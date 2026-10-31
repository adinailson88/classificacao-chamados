#!/usr/bin/env python3
"""Segunda avaliacao independente e cega da referencia revisada (Trilha B).

Duas etapas.

``amostra``  sorteia 300 chamados de grupos textuais distintos, 100 por estrato, e
grava (i) a planilha de avaliacao, sem categoria historica, referencia nem previsao
do modelo, com identificador opaco, e (ii) a chave, que liga o identificador ao
chamado e aos tres rotulos. A chave nao deve ser aberta pelo avaliador.

  A  historico confirmado pela revisao e acertado pelo modelo principal;
  B  historico confirmado pela revisao e errado pelo modelo principal;
  C  historico substituido pela revisao.

``analisar``  le a planilha preenchida e a chave e calcula o kappa de Cohen entre o
segundo avaliador e a referencia, a concordancia por estrato e a proporcao em que o
segundo avaliador coincide com a categoria historica. Estima, assim, quanto a
referencia revisada e reprodutivel por outro especialista, a lacuna apontada na
avaliacao do artigo. Nao grava texto de chamado em arquivo versionado.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ESTRATOS = ("A", "B", "C")
POR_ESTRATO = 100
SEMENTE = 20261101


def estrato(historica: str, referencia: str, previsto: str) -> str | None:
    if historica != referencia:
        return "C"
    return "A" if previsto == referencia else "B"


def sortear(candidatos: dict[str, list[dict]], n: int, rng: random.Random) -> list[dict]:
    """Sorteia ``n`` itens por estrato, no maximo um por grupo textual."""
    saida: list[dict] = []
    for est in ESTRATOS:
        pool = candidatos[est][:]
        rng.shuffle(pool)
        vistos: set[str] = set()
        escolhidos = []
        for it in pool:
            if it["grupo"] in vistos:
                continue
            vistos.add(it["grupo"])
            escolhidos.append(it)
            if len(escolhidos) == n:
                break
        if len(escolhidos) < n:
            raise ValueError(f"Estrato {est} tem so {len(escolhidos)} grupos distintos.")
        saida += escolhidos
    rng.shuffle(saida)
    return saida


def kappa_cohen(a: list[str], b: list[str]) -> float:
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def resumir(avaliacao: list[dict], chave: dict[str, dict], pesos: dict[str, int] | None = None) -> dict:
    por_est = {e: [] for e in ESTRATOS}
    for r in avaliacao:
        k = chave[r["id"]]
        por_est[k["estrato"]].append((r["categoria"], k["referencia"], k["historica"], k["previsto"]))
    todos = [x for v in por_est.values() for x in v]
    out = {"n": len(todos),
           "kappa_avaliador_vs_referencia": round(kappa_cohen([x[0] for x in todos], [x[1] for x in todos]), 4),
           "concordancia_com_referencia": round(sum(x[0] == x[1] for x in todos) / len(todos), 4),
           "por_estrato": {}}
    for e, v in por_est.items():
        if not v:
            continue
        out["por_estrato"][e] = {
            "n": len(v),
            "coincide_com_referencia": round(sum(x[0] == x[1] for x in v) / len(v), 4),
            "coincide_com_historica": round(sum(x[0] == x[2] for x in v) / len(v), 4),
            "coincide_com_modelo": round(sum(x[0] == x[3] for x in v) / len(v), 4)}
    if pesos:
        tot = sum(pesos[e] for e in out["por_estrato"])
        out["concordancia_ponderada_populacao"] = round(sum(
            pesos[e] * out["por_estrato"][e]["coincide_com_referencia"] for e in out["por_estrato"]) / tot, 4)
        out["historico_coincide_ponderada_populacao"] = round(sum(
            pesos[e] * out["por_estrato"][e]["coincide_com_historica"] for e in out["por_estrato"]) / tot, 4)
    return out


def cmd_amostra(args) -> int:
    import trilha_b as tb

    manifesto = json.loads(tb.MANIFESTO_B.read_text(encoding="utf-8"))
    linhas = tb.ler_snapshot_json(args.snapshot_json)
    tb.verificar_snapshot(linhas, manifesto)
    registros = tb.registros_do_snapshot(linhas)
    prev = {}
    for r in csv.DictReader(open(args.predicoes, encoding="utf-8")):
        if r["modelo"] == "tfidf_embedding":
            prev[r["id_sha256"]] = r["previsto"]
    ref = {}
    for l in linhas:
        ref[tb._digest(l["id_chamado"])] = l["referencia_humana"]
    corpus = tb.preparar_corpus(registros, tb.carregar_particoes_b())
    por_digest = {tb._digest(r["id"]): r for r in registros}
    excluir: set[str] = set()
    if args.excluir:
        excluir = {tb._digest(r["id_chamado"]) for r in csv.DictReader(open(args.excluir, encoding="utf-8"))}
    cand = {e: [] for e in ESTRATOS}
    for ch, grupo in zip(corpus["chaves"], corpus["grupos"]):
        if ch in excluir:
            continue
        r = por_digest[ch]
        est = estrato(r["categoria_historica"], ref[ch], prev[ch])
        cand[est].append({"chave": ch, "grupo": grupo, "reg": r, "referencia": ref[ch], "previsto": prev[ch]})
    escolhidos = sortear(cand, args.por_estrato, random.Random(SEMENTE))
    args.saida.mkdir(parents=True, exist_ok=True)
    (args.saida / "estratos.json").write_text(json.dumps({e: len(v) for e, v in cand.items()}), encoding="utf-8")
    args.saida.mkdir(parents=True, exist_ok=True)
    with open(args.saida / "SEGUNDA_AVALIACAO_CEGA.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "titulo", "descricao_glpi", "titulo_osm", "descricao_osm", "categoria", "ambiguo (S/N)", "observacao"])
        for i, it in enumerate(escolhidos, 1):
            r = it["reg"]
            w.writerow([i, r["titulo"], r["descricao_glpi"], r["titulo_osm"], r["descricao_osm"], "", "", ""])
    with open(args.saida / "CHAVE_NAO_ABRIR.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "id_sha256", "estrato", "historica", "referencia", "previsto"])
        for i, it in enumerate(escolhidos, 1):
            w.writerow([i, it["chave"], estrato(it["reg"]["categoria_historica"], it["referencia"], it["previsto"]),
                        it["reg"]["categoria_historica"], it["referencia"], it["previsto"]])
    cats = sorted({l["referencia_humana"] for l in linhas})
    with open(args.saida / "CATEGORIAS.csv", "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows([["categoria"]] + [[c] for c in cats])
    print(f"ok: {len(escolhidos)} chamados, {len(cats)} categorias")
    return 0


def cmd_analisar(args) -> int:
    chave = {r["id"]: r for r in csv.DictReader(open(args.chave, encoding="utf-8"))}
    aval = [r for r in csv.DictReader(open(args.avaliacao, encoding="utf-8")) if r["categoria"].strip()]
    faltam = len(chave) - len(aval)
    if faltam:
        print(f"Aviso: {faltam} chamados sem categoria preenchida; analise parcial.", file=sys.stderr)
    for r in aval:
        r["categoria"] = r["categoria"].strip()
    pesos = json.loads(args.estratos.read_text(encoding="utf-8")) if args.estratos else None
    res = resumir(aval, chave, pesos)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    if args.saida:
        args.saida.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("amostra")
    a.add_argument("--snapshot-json", type=Path, required=True)
    a.add_argument("--predicoes", type=Path, default=Path(__file__).resolve().parents[1] / "docs" / "dados" / "trilha_b" / "predicoes_com_alternativas.csv")
    a.add_argument("--saida", type=Path, required=True)
    a.add_argument("--por-estrato", type=int, default=POR_ESTRATO)
    a.add_argument("--excluir", type=Path, default=None,
                   help="CSV com coluna id_chamado a excluir (ex.: os pre-triados, ancorados no modelo)")
    z = sub.add_parser("analisar")
    z.add_argument("--avaliacao", type=Path, required=True)
    z.add_argument("--chave", type=Path, required=True)
    z.add_argument("--saida", type=Path, default=None)
    z.add_argument("--estratos", type=Path, default=None, help="estratos.json da amostragem")
    args = p.parse_args()
    return cmd_amostra(args) if args.cmd == "amostra" else cmd_analisar(args)


if __name__ == "__main__":
    raise SystemExit(main())
