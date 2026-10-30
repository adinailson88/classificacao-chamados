#!/usr/bin/env python3
"""Pipeline da Trilha B (novo corte cientifico) sobre o snapshot imutavel.

Le a aba ``CORTE_B_<data>`` criada por ``corte_b.py``, confere que ela
reproduz as impressoes digitais do manifesto ``docs/dados/trilha_b/corte_b.json``
(fail-closed) e executa as etapas, todas sobre o MESMO corpus em memoria:

- ``particoes``: grupos textuais e ``StratifiedGroupKFold`` (k=5, semente 42);
- ``retreino``: sete modelos com predicoes *out-of-fold*, mais desempenho por
  campus;
- ``temporal``: treino no passado e teste no futuro (periodo prospectivo e
  origem rolante por ano).

Reaproveita as funcoes puras dos scripts da rodada anterior sem alterar nenhum
artefato do ARTIGO_CONGELADO: todas as saidas ficam em ``docs/dados/trilha_b/``
e carregam o ``hash_corte``. Nenhuma saida publica titulo, descricao ou ID; as
chaves sao SHA-256 do ID.
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import calibrar_confianca as cc  # noqa: E402
import comparacao_kfold_groupkfold as ckg  # noqa: E402
import comparar_regras_modelos as crm  # noqa: E402
import conferencia_derivada as cd  # noqa: E402
import construir_grupos_textuais as cgt  # noqa: E402
import corte_b as cb  # noqa: E402
import gerar_particoes_canonicas as gpc  # noqa: E402
import planilha as pl  # noqa: E402
import retreinar_modelos_canonicos as rmc  # noqa: E402
from tempo import agora_bahia  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
DADOS_B = cb.DADOS_B
MANIFESTO_B = cb.SAIDA_JSON_PADRAO
SAIDAS = {
    "grupos_json": DADOS_B / "grupos_textuais.json",
    "grupos_mapa": DADOS_B / "grupos_textuais_mapa.csv",
    "particoes_json": DADOS_B / "particoes.json",
    "particoes_mapa": DADOS_B / "particoes_mapa.csv",
    "atributos": DADOS_B / "atributos_mapa.csv",
    "retreino_json": DADOS_B / "retreino.json",
    "retreino_pred": DADOS_B / "retreino_predicoes.csv",
    "temporal_json": DADOS_B / "avaliacao_temporal.json",
    "calibracao_json": DADOS_B / "calibracao.json",
    "regras_json": DADOS_B / "regras_versus_modelos.json",
    "kfold_json": DADOS_B / "kfold_vs_groupkfold.json",
}
K_PADRAO = 5
SEMENTE_PADRAO = 42
MINIMO_GRUPOS_PADRAO = 5
ANOS_TESTE_PADRAO = (2022, 2023, 2024, 2025, 2026)


# ---------------------------------------------------------------- snapshot --

def ler_snapshot(sh, aba: str) -> list[dict[str, str]]:
    """Le a aba de snapshot e devolve as linhas como dicts do cabecalho."""
    valores = sh.worksheet(aba).get_all_values()
    cab = valores[0]
    if cab != cb.CABECALHO_SNAPSHOT:
        raise RuntimeError(f"Cabecalho inesperado em {aba}: {cab}")
    linhas = []
    for v in valores[1:]:
        if not any(str(c).strip() for c in v):
            continue
        v = list(v) + [""] * (len(cab) - len(v))
        d = {c: str(x) for c, x in zip(cab, v)}
        d["id_chamado"] = cd.normalizar_id(d["id_chamado"])
        linhas.append(d)
    linhas.sort(key=lambda x: x["id_chamado"])
    return linhas


def verificar_snapshot(linhas: list[dict[str, str]],
                       manifesto: dict[str, Any]) -> dict[str, str]:
    """Fail-closed: o snapshot precisa reproduzir as digitais do manifesto."""
    obtidas = cb.impressoes_digitais(linhas)
    esperadas = manifesto["impressoes_digitais"]
    divergencias = [f"{k}: obtido={obtidas[k]} esperado={esperadas.get(k)}"
                    for k in obtidas if obtidas[k] != esperadas.get(k)]
    if divergencias or len(linhas) != manifesto["corpus"]["linhas"]:
        raise RuntimeError(
            "Snapshot divergente do corte B; etapa interrompida.\n"
            + "\n".join(divergencias)
            + f"\nlinhas obtidas={len(linhas)} esperadas={manifesto['corpus']['linhas']}")
    return obtidas


def registros_do_snapshot(linhas: list[dict[str, str]]) -> list[dict[str, str]]:
    """Converte o snapshot nos registros que as funcoes puras esperam."""
    return [{
        "id": r["id_chamado"], "titulo": r["titulo"],
        "descricao_glpi": r["descricao_glpi"], "titulo_osm": r["titulo_osm"],
        "descricao_osm": r["descricao_osm"],
        "categoria_historica": r["categoria_historica"],
        "conferencia_glpi": r["conferencia_glpi"],
        "categoria_manual": r["categoria_manual"],
        "data_abertura": r["data_abertura"], "campus": r["campus"],
        "periodo": r["periodo"],
    } for r in linhas]


def _digest(id_chamado: str) -> str:
    return hashlib.sha256(id_chamado.encode("utf-8")).hexdigest()


# --------------------------------------------------------------- particoes --

def etapa_particoes(registros: list[dict[str, str]], k: int = K_PADRAO,
                    semente: int = SEMENTE_PADRAO,
                    minimo: int = MINIMO_GRUPOS_PADRAO) -> dict[str, Any]:
    grupos = cgt.agrupar(registros)
    part = gpc.montar_relatorio(registros, k=k, semente=semente,
                                minimo_grupos=minimo)
    atributos = [{
        "id_sha256": _digest(r["id"]), "periodo": r["periodo"],
        "ano": r["data_abertura"][:4], "campus": r["campus"],
    } for r in registros if r["id"]]
    atributos.sort(key=lambda x: x["id_sha256"])
    return {"grupos": grupos, "particoes": part, "atributos": atributos}


def _escrever_csv(caminho: Path, campos: list[str], linhas: list[dict[str, Any]]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, lineterminator="\n")
        w.writeheader()
        w.writerows(linhas)


def _publicavel(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if not k.startswith("_")}


def gravar_particoes(resultado: dict[str, Any], digitais: dict[str, str],
                     quando: str, saidas: dict[str, Path] = SAIDAS) -> None:
    for chave in ("grupos_json", "particoes_json"):
        cb.garantir_fora_do_congelado(saidas[chave])
    g, p = resultado["grupos"], resultado["particoes"]
    carimbo = {"trilha": "B", "hash_corte": digitais["hash_corte"],
               "gerado_em": quando, "script_origem": "src/trilha_b.py"}
    saidas["grupos_json"].parent.mkdir(parents=True, exist_ok=True)
    saidas["grupos_json"].write_text(json.dumps(
        {**_publicavel(g), **carimbo}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    saidas["particoes_json"].write_text(json.dumps(
        {**_publicavel(p), **carimbo}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    _escrever_csv(saidas["grupos_mapa"], ["id_sha256", "grupo_sha256"], g["_mapa"])
    _escrever_csv(saidas["particoes_mapa"],
                  ["id_sha256", "grupo_sha256", "dobra"], p["_mapa"])
    _escrever_csv(saidas["atributos"],
                  ["id_sha256", "periodo", "ano", "campus"], resultado["atributos"])


# ----------------------------------------------------------------- corpus --

def preparar_corpus(registros: list[dict[str, str]],
                    particoes: dict[str, int]) -> dict[str, Any]:
    """Corpus da Trilha B: o de `rmc.preparar_corpus` mais ano, campus, periodo."""
    corpus = rmc.preparar_corpus(registros, particoes)
    por_digest = {_digest(r["id"]): r for r in registros if r["id"]}
    corpus["anos"] = [por_digest[c]["data_abertura"][:4] for c in corpus["chaves"]]
    corpus["campus"] = [por_digest[c]["campus"] for c in corpus["chaves"]]
    corpus["periodos"] = [por_digest[c]["periodo"] for c in corpus["chaves"]]
    return corpus


def carregar_particoes_b(caminho: Path = SAIDAS["particoes_mapa"]) -> dict[str, int]:
    return rmc.carregar_particoes(caminho)


# ---------------------------------------------------------------- retreino --

@contextlib.contextmanager
def lstm_deterministico(semente: int):
    """Fixa as sementes do TensorFlow antes de cada ajuste da LSTM.

    A rodada anterior nao fixou a semente global, o que impedia reproduzir os
    pesos. Os demais modelos ja recebem `random_state`.
    """
    original = rmc.zoo.criar_modelo

    def criar(nome: str):
        if (nome or "").strip().lower() == "lstm":
            from modelo_lstm import fixar_determinismo_lstm
            fixar_determinismo_lstm(semente)
        return original(nome)

    rmc.zoo.criar_modelo = criar
    try:
        yield
    finally:
        rmc.zoo.criar_modelo = original


def desempenho_por_campus(corpus: dict[str, Any], previsto: list[str]) -> list[dict[str, Any]]:
    from sklearn.metrics import f1_score
    saida = []
    for campus in sorted(set(corpus["campus"])):
        idx = [i for i, c in enumerate(corpus["campus"]) if c == campus]
        verdade = [corpus["rotulos"][i] for i in idx]
        pred = [previsto[i] for i in idx]
        saida.append({
            "campus": campus, "n": len(idx),
            "acuracia": round(rmc._acuracia(verdade, pred), 4),
            "macro_f1": round(float(f1_score(
                verdade, pred, labels=sorted(set(verdade)), average="macro",
                zero_division=0)), 4),
        })
    return saida


def etapa_retreino(corpus: dict[str, Any], modelos: list[str],
                   semente: int = SEMENTE_PADRAO, registrar=rmc._log) -> dict[str, Any]:
    with lstm_deterministico(semente):
        relatorio = rmc.montar_relatorio(corpus, modelos, semente, registrar)
    for r, bruto in zip(relatorio["modelos"], relatorio["_resultados"]):
        r["por_campus"] = desempenho_por_campus(corpus, bruto["_predicoes"])
    relatorio["trilha"] = "B"
    return relatorio


def gravar_retreino(relatorio: dict[str, Any], corpus: dict[str, Any],
                    digitais: dict[str, str], quando: str,
                    saidas: dict[str, Path] = SAIDAS) -> None:
    cb.garantir_fora_do_congelado(saidas["retreino_json"])
    carimbo = {"hash_corte": digitais["hash_corte"], "gerado_em": quando,
               "script_origem": "src/trilha_b.py"}
    saidas["retreino_json"].parent.mkdir(parents=True, exist_ok=True)
    saidas["retreino_json"].write_text(json.dumps(
        {**_publicavel(relatorio), **carimbo}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    rmc.escrever_predicoes(saidas["retreino_pred"], corpus, relatorio["_resultados"])


# ---------------------------------------------------------------- temporal --

def _metricas(verdade: list[str], previsto: list[str]) -> dict[str, float]:
    from sklearn.metrics import f1_score
    return {
        "acuracia": round(rmc._acuracia(verdade, previsto), 4),
        "macro_f1": round(float(f1_score(
            verdade, previsto, labels=sorted(set(verdade)), average="macro",
            zero_division=0)), 4),
    }


def avaliar_divisao(nome: str, corpus: dict[str, Any], treino: list[int],
                    teste: list[int], semente: int) -> dict[str, Any]:
    """Um ajuste no passado e uma predicao no futuro, com a mesma API dos modelos."""
    textos, rotulos, grupos = corpus["textos"], corpus["rotulos"], corpus["grupos"]
    vistos = {grupos[i] for i in treino}
    novos = [i for i in teste if grupos[i] not in vistos]
    modelo = rmc.zoo.criar_modelo(nome)
    modelo.fit([textos[i] for i in treino], [rotulos[i] for i in treino])
    previsto, _ = modelo.predict_score([textos[i] for i in teste])
    previsto = [str(p) for p in previsto]
    verdade = [rotulos[i] for i in teste]
    saida = {"modelo": nome, "treino": len(treino), "teste": len(teste),
             "teste_com_grupo_ja_visto": len(teste) - len(novos),
             **_metricas(verdade, previsto)}
    if novos:
        pos = {i: j for j, i in enumerate(teste)}
        saida["grupos_novos"] = {
            "n": len(novos),
            **_metricas([rotulos[i] for i in novos],
                        [previsto[pos[i]] for i in novos])}
    return saida


def etapa_temporal(corpus: dict[str, Any], modelos: list[str],
                   anos_teste: tuple[int, ...] = ANOS_TESTE_PADRAO,
                   semente: int = SEMENTE_PADRAO,
                   registrar=rmc._log) -> dict[str, Any]:
    n = len(corpus["textos"])
    historico = [i for i in range(n) if corpus["periodos"][i] == cb.PERIODO_HISTORICO]
    prospectivo = [i for i in range(n) if corpus["periodos"][i] == cb.PERIODO_PROSPECTIVO]
    cenarios: list[dict[str, Any]] = []
    if historico and prospectivo:
        cenarios.append({"nome": "prospectivo", "treino": historico, "teste": prospectivo,
                         "descricao": "treino em tudo o que foi aberto ate o corte, "
                                      "teste nos chamados abertos depois"})
    for ano in anos_teste:
        treino = [i for i in range(n) if corpus["anos"][i] and int(corpus["anos"][i]) < ano]
        teste = [i for i in range(n) if corpus["anos"][i] == str(ano)]
        if treino and teste:
            cenarios.append({"nome": f"origem_rolante_{ano}", "treino": treino,
                             "teste": teste,
                             "descricao": f"treino antes de {ano}, teste em {ano}"})
    resultados = []
    with lstm_deterministico(semente):
        for cen in cenarios:
            por_modelo = []
            for nome in modelos:
                registrar(f"[temporal] {cen['nome']}: {nome}")
                por_modelo.append(avaliar_divisao(nome, corpus, cen["treino"],
                                                  cen["teste"], semente))
            resultados.append({"cenario": cen["nome"], "descricao": cen["descricao"],
                               "treino": len(cen["treino"]), "teste": len(cen["teste"]),
                               "modelos": por_modelo})
    return {"schema_version": 1, "trilha": "B", "semente": semente,
            "modelos": modelos, "cenarios": resultados}


def gravar_temporal(relatorio: dict[str, Any], digitais: dict[str, str],
                    quando: str, saidas: dict[str, Path] = SAIDAS) -> None:
    cb.garantir_fora_do_congelado(saidas["temporal_json"])
    saidas["temporal_json"].parent.mkdir(parents=True, exist_ok=True)
    saidas["temporal_json"].write_text(json.dumps(
        {**relatorio, "hash_corte": digitais["hash_corte"], "gerado_em": quando,
         "script_origem": "src/trilha_b.py"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")


# -------------------------------------------------------------- calibracao --

def etapa_calibracao(corpus: dict[str, Any], modelos: list[str],
                     predicoes: Path = SAIDAS["retreino_pred"],
                     registrar=rmc._log) -> dict[str, Any]:
    """ECE, Brier e automacao seletiva por limiar, com dobra interna de calibracao.

    Usa as predicoes *out-of-fold* da etapa `retreino` como dobra externa e
    reajusta o modelo nas dobras restantes apenas para obter os escores da dobra
    interna, de modo que nenhum registro da externa toca calibrador ou limiar.
    """
    externas = cc.carregar_predicoes(predicoes)["por_modelo"]
    ausentes = [m for m in modelos if m not in externas]
    if ausentes:
        raise RuntimeError(f"Modelos sem predicoes no retreino: {ausentes}")
    with lstm_deterministico(SEMENTE_PADRAO):
        relatorio = cc.montar_relatorio(corpus, externas, modelos, registrar=registrar)
    relatorio["trilha"] = "B"
    return relatorio


def gravar_calibracao(relatorio: dict[str, Any], digitais: dict[str, str],
                      quando: str, saidas: dict[str, Path] = SAIDAS) -> None:
    cb.garantir_fora_do_congelado(saidas["calibracao_json"])
    saidas["calibracao_json"].parent.mkdir(parents=True, exist_ok=True)
    saidas["calibracao_json"].write_text(json.dumps(
        {**relatorio, "hash_corte": digitais["hash_corte"], "gerado_em": quando,
         "script_origem": "src/trilha_b.py"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")


# ------------------------------------------------------------------- kfold --

def etapa_kfold(corpus: dict[str, Any], modelos: list[str], k: int = K_PADRAO,
                registrar=rmc._log) -> dict[str, Any]:
    """KFold por linha contra GroupKFold por grupo textual, no MESMO corte.

    Mostra quanto a duplicacao textual infla o KFold. O alvo e a referencia
    humana (a rodada anterior usou a categoria historica, em outra data).
    """
    textos, cats, grupos = corpus["textos"], corpus["rotulos"], corpus["grupos"]
    resultados = []
    with lstm_deterministico(SEMENTE_PADRAO):
        for nome in modelos:
            registrar(f"[kfold] {nome}")
            r_kf = ckg.avaliar(nome, textos, cats, None, k)
            r_gk = ckg.avaliar(nome, textos, cats, grupos, k)
            resultados.append({
                "modelo": nome, "kfold": r_kf, "groupkfold": r_gk,
                "delta_acuracia_kfold_menos_groupkfold": round(
                    r_kf["acuracia"] - r_gk["acuracia"], 4)})
    ordem_kf = [r["modelo"] for r in sorted(resultados, key=lambda r: -r["kfold"]["acuracia"])]
    ordem_gk = [r["modelo"] for r in sorted(resultados, key=lambda r: -r["groupkfold"]["acuracia"])]
    return {
        "schema_version": 1, "trilha": "B", "k_folds": k,
        "natureza": "acuracia contra a referencia humana revisada",
        "duplicatas_textuais": {
            "n_linhas": len(textos), "n_grupos_textuais": len(set(grupos)),
            "proporcao_com_duplicata": round(1 - len(set(grupos)) / len(textos), 4)
            if textos else 0.0},
        "resultados": resultados, "ranking_kfold": ordem_kf,
        "ranking_groupkfold": ordem_gk, "ranking_preservado": ordem_kf == ordem_gk,
    }


def gravar_kfold(relatorio: dict[str, Any], digitais: dict[str, str],
                 quando: str, saidas: dict[str, Path] = SAIDAS) -> None:
    cb.garantir_fora_do_congelado(saidas["kfold_json"])
    saidas["kfold_json"].parent.mkdir(parents=True, exist_ok=True)
    saidas["kfold_json"].write_text(json.dumps(
        {**relatorio, "hash_corte": digitais["hash_corte"], "gerado_em": quando,
         "script_origem": "src/trilha_b.py"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")


# ------------------------------------------------------------------ regras --

def etapa_regras(corpus: dict[str, Any],
                 predicoes: Path = SAIDAS["retreino_pred"]) -> dict[str, Any]:
    """Camada de regras de periodicidade contra os modelos puros.

    Aplica a regra sobre as predicoes *out-of-fold* da etapa `retreino`, nos
    mesmos registros e particoes. A referencia humana nao e alterada.
    """
    dados = crm.carregar_predicoes(predicoes)
    textos = dict(zip(corpus["chaves"], corpus["textos"]))
    chaves = sorted(dados["referencia"])
    faltam = [c for c in chaves if c not in textos]
    if faltam:
        raise RuntimeError(f"{len(faltam)} registros das predicoes sem texto no corpus")
    relatorio = crm.montar_relatorio(chaves, dados["referencia"], textos,
                                     dados["por_modelo"])
    relatorio["trilha"] = "B"
    return relatorio


def gravar_regras(relatorio: dict[str, Any], digitais: dict[str, str],
                  quando: str, saidas: dict[str, Path] = SAIDAS) -> None:
    cb.garantir_fora_do_congelado(saidas["regras_json"])
    saidas["regras_json"].parent.mkdir(parents=True, exist_ok=True)
    saidas["regras_json"].write_text(json.dumps(
        {**relatorio, "hash_corte": digitais["hash_corte"], "gerado_em": quando,
         "script_origem": "src/trilha_b.py"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")


# --------------------------------------------------------------------- cli --

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("etapa", choices=["particoes", "retreino", "temporal", "calibracao",
                                     "regras", "kfold"])
    p.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    p.add_argument("--credenciais", default=None)
    p.add_argument("--aba", default="", help="aba de snapshot (padrao: a do manifesto)")
    p.add_argument("--modelos", default=",".join(rmc.MODELOS_PADRAO))
    p.add_argument("--semente", type=int, default=SEMENTE_PADRAO)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    manifesto = json.loads(MANIFESTO_B.read_text(encoding="utf-8"))
    aba = args.aba or manifesto["aba_snapshot"]
    config = json.loads(args.config.read_text(encoding="utf-8"))
    sh = pl.abrir_planilha(pl.id_planilha(config), args.credenciais)
    linhas = ler_snapshot(sh, aba)
    digitais = verificar_snapshot(linhas, manifesto)
    registros = registros_do_snapshot(linhas)
    quando = agora_bahia()
    modelos = [m.strip() for m in args.modelos.split(",") if m.strip()]

    if args.etapa == "particoes":
        r = etapa_particoes(registros, semente=args.semente)
        gravar_particoes(r, digitais, quando)
        p = r["particoes"]
        print(json.dumps({k: p[k] for k in (
            "status", "linhas_particionadas", "grupos_particionados",
            "categorias_na_referencia", "categorias_particionadas",
            "linhas_excluidas_total", "grupos_divididos_entre_dobras")},
            ensure_ascii=False, indent=2))
        return 0 if p["status"] == "apto_para_treinar" else 2

    corpus = preparar_corpus(registros, carregar_particoes_b())
    if args.etapa == "retreino":
        rel = etapa_retreino(corpus, modelos, args.semente)
        gravar_retreino(rel, corpus, digitais, quando)
        print(json.dumps([{k: m[k] for k in ("modelo", "acuracia", "macro_f1")}
                          for m in rel["modelos"]], ensure_ascii=False, indent=2))
        return 0 if rel["status"] == "apto_para_regras" else 2
    if args.etapa == "kfold":
        rel = etapa_kfold(corpus, modelos)
        gravar_kfold(rel, digitais, quando)
        for r in rel["resultados"]:
            print(r["modelo"], r["kfold"]["acuracia"], r["groupkfold"]["acuracia"])
        return 0
    if args.etapa == "regras":
        rel = etapa_regras(corpus)
        gravar_regras(rel, digitais, quando)
        print(json.dumps(rel["modelos_com_ganho_de_macro_f1"], ensure_ascii=False))
        return 0
    if args.etapa == "calibracao":
        rel = etapa_calibracao(corpus, modelos)
        gravar_calibracao(rel, digitais, quando)
        for m in rel["modelos"]:
            print(m["modelo"], "ECE", m["bruta"]["ece"], "->", m["calibrada"]["ece"])
        return 0
    rel = etapa_temporal(corpus, modelos, semente=args.semente)
    gravar_temporal(rel, digitais, quando)
    for c in rel["cenarios"]:
        print(c["cenario"], c["treino"], c["teste"],
              {m["modelo"]: m["acuracia"] for m in c["modelos"]})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
