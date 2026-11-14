#!/usr/bin/env python3
"""Simulacao cronologica de aprendizado continuo com confirmacoes humanas (Trilha B).

Pergunta: se a base for sendo confirmada ao longo do tempo e o modelo retreinado a
cada trimestre, quanto se ganha em acuracia e em cobertura sob controle de risco
(Learn-then-Test), e a escolha ativa de quem revisar rende mais do que a aleatoria?

Protocolo. O corte B e ordenado pela data de abertura. O modelo inicial treina com
tudo o que foi aberto ate 2021; cada trimestre seguinte e predito ANTES de seus
rotulos serem revelados. Em cada bloco ha uma amostra aleatoria de auditoria
(``--auditoria``), igual para todas as estrategias, usada para calibrar o limiar do
Learn-then-Test e, nas estrategias que aprendem, tambem para treino. As estrategias
diferem no que mais e confirmado depois de cada bloco:

- ``estatico``   nada alem da auditoria (que so calibra); o modelo nunca e retreinado;
- ``aleatorio``  auditoria + ``--revisoes`` chamados sorteados;
- ``ativo``      auditoria + os ``--revisoes`` de menor confianca fora da auditoria;
- ``completo``   todos os rotulos do bloco (teto, custo de rotular tudo).

A auditoria aleatoria preserva a validade do limiar: casos escolhidos pela incerteza
nao servem de calibracao. Saem apenas agregados e contagens (sem texto de chamado).
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

import controle_risco as cr  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "docs" / "dados" / "trilha_b" / "aprendizado_continuo.json"
ESTRATEGIAS = ("estatico", "aleatorio", "ativo", "completo")
ALFA = 0.10
DELTA = 0.05
MIN_CALIBRACAO = 200


def trimestre(data: str) -> str:
    ano, mes = int(data[:4]), int(data[5:7])
    return f"{ano}T{(mes - 1) // 3 + 1}"


def montar_blocos(datas: list[str], inicio_ano: int) -> tuple[list[int], list[tuple[str, list[int]]]]:
    """Indices do treino inicial (antes de ``inicio_ano``) e blocos trimestrais seguintes."""
    inicial = [i for i, d in enumerate(datas) if int(d[:4]) < inicio_ano]
    por_tri: dict[str, list[int]] = defaultdict(list)
    for i, d in enumerate(datas):
        if int(d[:4]) >= inicio_ano:
            por_tri[trimestre(d)].append(i)
    return inicial, sorted(por_tri.items())


def escolher_revisoes(estrategia: str, bloco: list[int], auditoria: set[int],
                      confianca: dict[int, float], n: int, rng: random.Random) -> list[int]:
    """Indices do bloco a confirmar alem da auditoria, conforme a estrategia."""
    resto = [i for i in bloco if i not in auditoria]
    if estrategia == "completo":
        return resto
    if estrategia == "aleatorio":
        return rng.sample(resto, min(n, len(resto)))
    if estrategia == "ativo":
        return sorted(resto, key=lambda i: (confianca[i], i))[:n]
    return []


def avaliar_bloco(previsto: list[str], verdade: list[str], escores: list[float],
                  calibracao: list[tuple[float, bool, str]]) -> dict[str, Any]:
    acertos = [p == v for p, v in zip(previsto, verdade)]
    saida: dict[str, Any] = {"n": len(verdade), "acuracia": round(sum(acertos) / len(acertos), 4),
                             "acertos": sum(acertos)}
    if len(calibracao) < MIN_CALIBRACAO:
        saida["controle"] = None
        return saida
    unicos = cr.um_por_grupo([g for _, _, g in calibracao])
    esc = [calibracao[i][0] for i in unicos]
    ac = [calibracao[i][1] for i in unicos]
    for nome, limiar in (("controlado", cr.escolher_limiar(esc, ac, alfa=ALFA, delta=DELTA)),
                         ("ingenuo", cr.limiar_ingenuo(esc, ac, alfa=ALFA))):
        saida[nome] = {"limiar": limiar, **cr.risco_e_cobertura(escores, acertos, limiar)}
    saida["controle"] = True
    return saida


def simular(textos: list[str], rotulos: list[str], grupos: list[str], datas: list[str],
            criar_modelo: Callable[[], Any], inicio_ano: int = 2022, auditoria: int = 100,
            revisoes: int = 100, janela: int = 4, semente: int = 42,
            estrategias: tuple[str, ...] = ESTRATEGIAS, log=print) -> dict[str, Any]:
    inicial, blocos = montar_blocos(datas, inicio_ano)
    rng_aud = random.Random(semente)
    auditorias = {rot: set(rng_aud.sample(idx, min(auditoria, len(idx)))) for rot, idx in blocos}
    resultado: dict[str, list[dict[str, Any]]] = {}
    for est in estrategias:
        rng = random.Random(semente + 1)
        treino = list(inicial)
        historico_cal: list[list[tuple[float, bool, str]]] = []
        linhas = []
        for rot, bloco in blocos:
            modelo = criar_modelo()
            modelo.fit([textos[i] for i in treino], [rotulos[i] for i in treino])
            prev, esc = modelo.predict_score([textos[i] for i in bloco])
            prev = [str(p) for p in prev]
            esc = [float(e) for e in esc]
            verdade = [rotulos[i] for i in bloco]
            calibracao = [x for lote in historico_cal[-janela:] for x in lote]
            linha = {"bloco": rot, "treino": len(treino),
                     **avaliar_bloco(prev, verdade, esc, calibracao)}
            linhas.append(linha)
            log(f"[{est}] {rot}: treino={len(treino)} acc={linha['acuracia']}")
            pos = {i: j for j, i in enumerate(bloco)}
            aud = auditorias[rot]
            historico_cal.append([(esc[pos[i]], prev[pos[i]] == rotulos[i], grupos[i])
                                  for i in sorted(aud)])
            if est == "estatico":
                continue
            conf = {i: esc[pos[i]] for i in bloco}
            novos = set(aud) | set(escolher_revisoes(est, bloco, aud, conf, revisoes, rng))
            treino.extend(sorted(novos))
        resultado[est] = linhas
    return {"estrategias": resultado, "blocos": [r for r, _ in blocos],
            "treino_inicial": len(inicial)}


def agregar(resultado: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for est, linhas in resultado["estrategias"].items():
        n = sum(l["n"] for l in linhas)
        a = sum(l["acertos"] for l in linhas)
        por_ano: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for l in linhas:
            por_ano[l["bloco"][:4]][0] += l["acertos"]
            por_ano[l["bloco"][:4]][1] += l["n"]
        resumo: dict[str, Any] = {
            "n": n, "acuracia": round(a / n, 4),
            "acuracia_por_ano": {y: round(v[0] / v[1], 4) for y, v in sorted(por_ano.items())}}
        for nome in ("controlado", "ingenuo"):
            com = [l[nome] for l in linhas if l.get("controle") and l[nome]["automatizados"]]
            auto = sum(c["automatizados"] for c in com)
            erros = sum(c["erros"] for c in com)
            total = sum(c["n"] for c in com)
            resumo[nome] = {
                "blocos": len(com), "cobertura": round(auto / total, 4) if total else None,
                "erro": round(erros / auto, 4) if auto else None,
                "blocos_acima_da_meta": sum(1 for c in com if c["erro"] is not None
                                            and c["erro"] > ALFA)}
        out[est] = resumo
    return out


def main() -> int:
    import trilha_b as tb  # noqa: E402  (importa so aqui: dependencias pesadas)
    import modelos_zoo as zoo  # noqa: E402

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--snapshot-json", type=Path, required=True)
    p.add_argument("--modelo", default="linear_svc")
    p.add_argument("--auditoria", type=int, default=100)
    p.add_argument("--revisoes", type=int, default=100)
    p.add_argument("--inicio-ano", type=int, default=2022)
    p.add_argument("--estrategias", default=",".join(ESTRATEGIAS),
                   help="lista separada por virgulas (padrao: todas)")
    p.add_argument("--saida", type=Path, default=SAIDA)
    args = p.parse_args()

    manifesto = json.loads(tb.MANIFESTO_B.read_text(encoding="utf-8"))
    linhas = tb.ler_snapshot_json(args.snapshot_json)
    tb.verificar_snapshot(linhas, manifesto)
    registros = tb.registros_do_snapshot(linhas)
    corpus = tb.preparar_corpus(registros, tb.carregar_particoes_b())
    data_de = {tb._digest(r["id"]): r["data_abertura"] for r in registros if r["id"]}
    datas = [data_de[c] for c in corpus["chaves"]]
    res = simular(corpus["textos"], corpus["rotulos"], corpus["grupos"], datas,
                  lambda: zoo.criar_modelo(args.modelo), args.inicio_ano, args.auditoria,
                  args.revisoes,
                  estrategias=tuple(e.strip() for e in args.estrategias.split(",")),
                  log=lambda s: print(s, flush=True))
    saida = {"protocolo": __doc__, "modelo": args.modelo, "meta_de_erro": ALFA,
             "auditoria_por_bloco": args.auditoria, "revisoes_por_bloco": args.revisoes,
             "hash_corte": manifesto.get("impressoes_digitais", {}).get("hash_corte"),
             "agregado": agregar(res), **res}
    args.saida.write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(saida["agregado"], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
