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
import modelos_alternativos as ma  # noqa: E402
import comparacao_kfold_groupkfold as ckg  # noqa: E402
import comparacao_historica as ch  # noqa: E402
import comparar_regras_modelos as crm  # noqa: E402
import conferencia_derivada as cd  # noqa: E402
import construir_grupos_textuais as cgt  # noqa: E402
import corte_b as cb  # noqa: E402
import gerar_particoes_canonicas as gpc  # noqa: E402
import planilha as pl  # noqa: E402
import retreinar_modelos_canonicos as rmc  # noqa: E402
import validacao_ufrn as vu  # noqa: E402
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
    "historica_json": DADOS_B / "comparacao_historica.json",
    "kfold_json": DADOS_B / "kfold_vs_groupkfold.json",
    "campi_json": DADOS_B / "avaliacao_campi.json",
    "calibracao_candidatos_json": DADOS_B / "calibracao_candidatos.json",
    "ufrn_resumo_json": DADOS_B / "ufrn_resumo.json",
    "ufrn_reverso_json": DADOS_B / "ufrn_reverso.json",
    "ufrn_reverso_pred": DADOS_B / "ufrn_reverso_predicoes_nossa_base.csv",
    # Texto de chamados de OUTRA instituicao: fica fora da arvore versionada.
    "ufrn_avaliacao_csv": RAIZ / "saidas_privadas" / "ufrn_amostra_avaliacao.csv",
    "alternativas_json": DADOS_B / "alternativas.json",
    "alternativas_pred": DADOS_B / "alternativas_predicoes.csv",
    "predicoes_todas": DADOS_B / "predicoes_com_alternativas.csv",
}
K_PADRAO = 5
SEMENTE_PADRAO = 42
MINIMO_GRUPOS_PADRAO = 5
ANOS_TESTE_PADRAO = (2022, 2023, 2024, 2025, 2026)


# ---------------------------------------------------------------- snapshot --

def ler_snapshot(sh, aba: str) -> list[dict[str, str]]:
    """Le a aba de snapshot e devolve as linhas como dicts do cabecalho."""
    return linhas_do_snapshot(sh.worksheet(aba).get_all_values(), aba)


def ler_snapshot_json(caminho: Path) -> list[dict[str, str]]:
    """Le uma copia local do snapshot (JSON `{"values": [[...]]}` do conector de planilhas).

    A verificacao contra o manifesto continua valendo: copia divergente e recusada.
    """
    valores = json.loads(Path(caminho).read_text(encoding="utf-8"))["values"]
    return linhas_do_snapshot(valores, str(caminho))


def linhas_do_snapshot(valores: list[list[str]], aba: str) -> list[dict[str, str]]:
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


def ic_acuracia_por_grupo(acertos: list[bool], grupos: list[str], reamostras: int = 1000,
                          semente: int = SEMENTE_PADRAO) -> list[float]:
    """IC95% percentil da acuracia, reamostrando grupos textuais (nao linhas)."""
    import numpy as np
    rng = np.random.default_rng(semente)
    ids = {g: k for k, g in enumerate(dict.fromkeys(grupos))}
    cod = np.array([ids[g] for g in grupos])
    ok = np.array(acertos, dtype=float)
    soma = np.bincount(cod, weights=ok, minlength=len(ids))
    tam = np.bincount(cod, minlength=len(ids)).astype(float)
    sorteios = rng.integers(0, len(ids), size=(reamostras, len(ids)))
    acc = soma[sorteios].sum(axis=1) / tam[sorteios].sum(axis=1)
    return [round(float(np.percentile(acc, 2.5)), 4), round(float(np.percentile(acc, 97.5)), 4)]


def avaliar_divisao(nome: str, corpus: dict[str, Any], treino: list[int],
                    teste: list[int], semente: int, detalhar: bool = False) -> dict[str, Any]:
    """Um ajuste no passado e uma predicao no futuro, com a mesma API dos modelos.

    Com ``detalhar``, acrescenta o IC95% por grupo e o desempenho restrito aos
    chamados cuja categoria de referencia aparece no treino (o teto de uma
    transferencia entre origens e a cobertura de categorias do treino).
    """
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
    if detalhar:
        saida["ic95_acuracia"] = ic_acuracia_por_grupo(
            [v == p for v, p in zip(verdade, previsto)], [grupos[i] for i in teste],
            semente=semente)
        categorias_treino = {rotulos[i] for i in treino}
        cobertas = [j for j, v in enumerate(verdade) if v in categorias_treino]
        saida["categorias_cobertas"] = {
            "n": len(cobertas), "proporcao": round(len(cobertas) / len(teste), 4),
            **(_metricas([verdade[j] for j in cobertas], [previsto[j] for j in cobertas])
               if cobertas else {})}
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


# -------------------------------------------------------------------- ufrn --

MODELOS_UFRN_PADRAO = ("tfidf_embedding", "linear_svc", "naive_bayes", "regressao_logistica",
                       "sgd", "extra_trees", "random_forest", "lstm", "tfidf_caracteres")
COLUNAS_PLANILHA_UFRN = 2  # a planilha de avaliacao traz so os dois primeiros modelos


def etapa_ufrn(corpus: dict[str, Any], amostra: list[dict[str, str]],
               nomes: tuple[str, ...] = MODELOS_UFRN_PADRAO,
               gerar_embeddings=ma.calcular_embeddings, semente: int = SEMENTE_PADRAO,
               registrar=rmc._log) -> dict[str, Any]:
    """Treina no corpus inteiro da Trilha B e preve a amostra da UFRN.

    Sem dobras: nao ha rotulo da Trilha B nos chamados da UFRN, o treino usa todo o
    corpus avaliado e a amostra e so de teste. A confianca e o escore bruto do
    modelo, sem calibracao.
    """
    textos = [rmc.montar_texto({"descricao_glpi": a["descricao"]}) for a in amostra]
    tabela: dict[str, Any] = {}
    if any("embedding" in n for n in nomes):
        registrar("[ufrn] calculando embeddings")
        tabela = gerar_embeddings(sorted(set(corpus["textos"]) | set(textos)),
                                  registrar=registrar)
    previsoes: dict[str, list[str]] = {}
    confiancas: dict[str, list[float]] = {}
    with lstm_deterministico(semente), modelos_alternativos_ativos(tabela):
        for nome in nomes:
            registrar(f"[ufrn] ajustando {nome} em {len(corpus['textos'])} chamados")
            modelo = rmc.zoo.criar_modelo(nome)
            modelo.fit(corpus["textos"], corpus["rotulos"])
            prev, conf = modelo.predict_score(textos)
            previsoes[nome] = [str(p) for p in prev]
            confiancas[nome] = [round(float(c), 4) for c in conf]
    return {"amostra": amostra, "previsoes": previsoes, "confiancas": confiancas,
            "resumo": vu.resumir(amostra, previsoes)}


def gravar_ufrn(resultado: dict[str, Any], digitais: dict[str, str], quando: str,
                saidas: dict[str, Path] = SAIDAS) -> None:
    """Resumo agregado (versionavel) e planilha de avaliacao (privada, com texto)."""
    cb.garantir_fora_do_congelado(saidas["ufrn_resumo_json"])
    saidas["ufrn_resumo_json"].parent.mkdir(parents=True, exist_ok=True)
    saidas["ufrn_resumo_json"].write_text(json.dumps(
        {**resultado["resumo"], "hash_corte": digitais["hash_corte"], "gerado_em": quando,
         "fonte": vu.URL_PADRAO, "fonte_sha256": digitais.get("fonte_ufrn_sha256", ""),
         "script_origem": "src/trilha_b.py"},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    nomes = list(resultado["previsoes"])[:COLUNAS_PLANILHA_UFRN]
    principal = nomes[0]
    campos = ["id_ufrn", "ano", "divisao_ufrn", "descricao", "local"]
    for n in nomes:
        campos += [f"previsao_{n}", f"confianca_{n}"]
    campos += [f"concorda_{principal}_com_divisao", "avaliacao_do_modelo",
               "categoria_correta_manual", "observacao"]
    saidas["ufrn_avaliacao_csv"].parent.mkdir(parents=True, exist_ok=True)
    with saidas["ufrn_avaliacao_csv"].open("w", encoding="utf-8-sig", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=campos)
        escritor.writeheader()
        for i, a in enumerate(resultado["amostra"]):
            linha = {"id_ufrn": a["id_ufrn"], "ano": a["ano"], "divisao_ufrn": a["divisao"],
                     "descricao": a["descricao"], "local": a["local"]}
            for n in nomes:
                linha[f"previsao_{n}"] = resultado["previsoes"][n][i]
                linha[f"confianca_{n}"] = resultado["confiancas"][n][i]
            linha[f"concorda_{principal}_com_divisao"] = vu.concorda(
                resultado["previsoes"][principal][i], a["divisao"])
            escritor.writerow(linha)


MODELOS_REVERSO_PADRAO = ("naive_bayes", "regressao_logistica", "linear_svc", "sgd",
                          "extra_trees", "random_forest", "lstm", "tfidf_caracteres")


def _recall_por_classe(verdade: list[str], previsto: list[str]) -> dict[str, dict[str, Any]]:
    total: dict[str, int] = {}
    acerto: dict[str, int] = {}
    for v, p in zip(verdade, previsto):
        total[v] = total.get(v, 0) + 1
        acerto[v] = acerto.get(v, 0) + (v == p)
    return {c: {"n": total[c], "recall": round(acerto[c] / total[c], 4)} for c in sorted(total)}


def _matriz(verdade: list[str], previsto: list[str]) -> dict[str, dict[str, int]]:
    m: dict[str, dict[str, int]] = {}
    for v, p in zip(verdade, previsto):
        m.setdefault(v, {})
        m[v][p] = m[v].get(p, 0) + 1
    return {v: dict(sorted(d.items(), key=lambda kv: -kv[1])) for v, d in sorted(m.items())}


def _acuracia_por(verdade: list[str], previsto: list[str], grupo: list[str]) -> list[dict[str, Any]]:
    n: dict[str, int] = {}
    ok: dict[str, int] = {}
    for v, p, g in zip(verdade, previsto, grupo):
        n[g] = n.get(g, 0) + 1
        ok[g] = ok.get(g, 0) + (v == p)
    return [{"grupo": g, "n": n[g], "acuracia": round(ok[g] / n[g], 4)} for g in sorted(n)]


def etapa_ufrn_reverso(corpus: dict[str, Any], linhas_ufrn: list[dict[str, str]],
                       nomes: tuple[str, ...] = MODELOS_REVERSO_PADRAO,
                       por_divisao: int = 5000, ano_minimo: int = 2018, ano_teste: int = 2025,
                       gerar_embeddings=ma.calcular_embeddings,
                       semente: int = SEMENTE_PADRAO, registrar=rmc._log) -> dict[str, Any]:
    """Treina na base da UFRN e classifica o corpus da Trilha B com a taxonomia dela.

    O treino usa as requisicoes da UFRN de ``ano_minimo`` ate o ano anterior a
    ``ano_teste`` (no maximo ``por_divisao`` por divisao); as de ``ano_teste`` em
    diante sao o teste dentro da propria UFRN. O mesmo modelo ajustado classifica
    todos os chamados do corpus. A concordancia com a nossa referencia so vale nos
    chamados cujo primeiro nivel tem correspondencia proposta com uma `divisao`.
    """
    import random
    from sklearn.metrics import cohen_kappa_score

    pool = vu.elegiveis(linhas_ufrn, ano_minimo)
    treino_pool = [l for l in pool if int(l["ano"]) < ano_teste]
    teste_u = [l for l in pool if int(l["ano"]) >= ano_teste]
    rng = random.Random(semente)
    por_classe: dict[str, list[dict[str, str]]] = {}
    for l in treino_pool:
        por_classe.setdefault(l["divisao"], []).append(l)
    treino: list[dict[str, str]] = []
    for classe in sorted(por_classe):
        itens = por_classe[classe]
        treino.extend(rng.sample(itens, min(por_divisao, len(itens))))
    if not treino or not teste_u:
        raise RuntimeError("base da UFRN sem treino ou teste para os anos informados")
    montar = lambda ls: [rmc.montar_texto({"descricao_glpi": l["descricao"]}) for l in ls]  # noqa: E731
    x_tr, y_tr = montar(treino), [l["divisao"] for l in treino]
    x_te, y_te = montar(teste_u), [vu.chave(l["divisao"]) for l in teste_u]
    nivel1 = [str(r).split(">")[0].strip() for r in corpus["rotulos"]]
    mapeada = [vu.CORRESPONDENCIA_PROPOSTA.get(vu.chave(n)) for n in nivel1]
    idx = [i for i, m in enumerate(mapeada) if m]
    verdade_n = [mapeada[i] for i in idx]
    resultados: dict[str, Any] = {}
    previsoes_n: dict[str, list[str]] = {}
    confiancas_n: dict[str, list[float]] = {}
    tabela: dict[str, Any] = {}
    if any("embedding" in n for n in nomes):
        registrar("[reverso] calculando embeddings")
        tabela = gerar_embeddings(sorted(set(x_tr) | set(x_te) | set(corpus["textos"])),
                                  registrar=registrar)
    with lstm_deterministico(semente), modelos_alternativos_ativos(tabela):
        for nome in nomes:
            registrar(f"[reverso] {nome}: treino {len(x_tr)} (UFRN), teste UFRN {len(x_te)}, "
                      f"nossa base {len(corpus['textos'])}")
            modelo = rmc.zoo.criar_modelo(nome)
            modelo.fit(x_tr, y_tr)
            prev_u, _ = modelo.predict_score(x_te)
            prev_u = [vu.chave(p) for p in prev_u]
            prev_n, conf_n = modelo.predict_score(corpus["textos"])
            prev_n = [vu.chave(p) for p in prev_n]
            previsoes_n[nome] = prev_n
            confiancas_n[nome] = [round(float(c), 4) for c in conf_n]
            pn = [prev_n[i] for i in idx]
            resultados[nome] = {
                "ufrn_teste": {"n": len(y_te), **_metricas(y_te, prev_u),
                               "recall_por_divisao": _recall_por_classe(y_te, prev_u)},
                "nossa_base": {"n_com_correspondencia": len(idx),
                               "n_sem_correspondencia": len(prev_n) - len(idx),
                               **_metricas(verdade_n, pn),
                               "recall_por_divisao": _recall_por_classe(verdade_n, pn),
                               "matriz_referencia_por_previsao": _matriz(verdade_n, pn),
                               "por_primeiro_nivel": _acuracia_por(
                                   verdade_n, pn, [nivel1[i] for i in idx]),
                               "por_campus": _acuracia_por(
                                   verdade_n, pn, [corpus["campus"][i] for i in idx])},
                "distribuicao_prevista_na_nossa_base": dict(sorted(
                    {c: prev_n.count(c) for c in set(prev_n)}.items(), key=lambda kv: -kv[1])),
            }
    concordancia = []
    for i, a in enumerate(nomes):
        for b in nomes[i + 1:]:
            pa, pb = previsoes_n[a], previsoes_n[b]
            concordancia.append({
                "modelos": [a, b],
                "concordancia": round(sum(x == y for x, y in zip(pa, pb)) / len(pa), 4),
                "kappa": round(float(cohen_kappa_score(pa, pb)), 4)})
    return {"schema_version": 1, "trilha": "B", "semente": semente, "modelos": list(nomes),
            "treino_ufrn": {"n": len(x_tr), "ano_minimo": ano_minimo,
                            "ano_ate": ano_teste - 1, "por_divisao_maximo": por_divisao,
                            "por_divisao": dict(sorted(
                                {c: y_tr.count(c) for c in set(y_tr)}.items()))},
            "teste_ufrn": {"n": len(x_te), "ano_de": ano_teste},
            "correspondencia_proposta": vu.CORRESPONDENCIA_PROPOSTA,
            "concordancia_entre_modelos_na_nossa_base": concordancia,
            "resultados": resultados,
            "_previsoes": previsoes_n, "_confiancas": confiancas_n}


def gravar_ufrn_reverso(res: dict[str, Any], corpus: dict[str, Any], digitais: dict[str, str],
                        quando: str, saidas: dict[str, Path] = SAIDAS) -> None:
    """JSON agregado e previsoes por id (SHA-256), sem texto de nenhum chamado."""
    for chave in ("ufrn_reverso_json", "ufrn_reverso_pred"):
        cb.garantir_fora_do_congelado(saidas[chave])
    saidas["ufrn_reverso_json"].parent.mkdir(parents=True, exist_ok=True)
    publico = {k: v for k, v in res.items() if not k.startswith("_")}
    saidas["ufrn_reverso_json"].write_text(json.dumps(
        {**publico, "hash_corte": digitais["hash_corte"], "gerado_em": quando,
         "fonte": vu.URL_PADRAO, "fonte_sha256": digitais.get("fonte_ufrn_sha256", ""),
         "script_origem": "src/trilha_b.py"},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    nomes = res["modelos"]
    campos = ["id_sha256", "campus", "referencia_primeiro_nivel", "divisao_equivalente"]
    for n in nomes:
        campos += [f"previsao_{n}", f"confianca_{n}"]
    with saidas["ufrn_reverso_pred"].open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        for i, h in enumerate(corpus["chaves"]):
            n1 = str(corpus["rotulos"][i]).split(">")[0].strip()
            linha = {"id_sha256": h, "campus": corpus["campus"][i],
                     "referencia_primeiro_nivel": n1,
                     "divisao_equivalente": vu.CORRESPONDENCIA_PROPOSTA.get(vu.chave(n1), "")}
            for n in nomes:
                linha[f"previsao_{n}"] = res["_previsoes"][n][i]
                linha[f"confianca_{n}"] = res["_confiancas"][n][i]
            w.writerow(linha)


# ------------------------------------------------------------------- campi --

CAMPUS_ORIGEM_PADRAO = "Reitoria"
MINIMO_TESTE_CAMPUS = 30


def etapa_campi(corpus: dict[str, Any], modelos: list[str],
                origem: str = CAMPUS_ORIGEM_PADRAO,
                minimo_teste: int = MINIMO_TESTE_CAMPUS,
                semente: int = SEMENTE_PADRAO,
                registrar=rmc._log) -> dict[str, Any]:
    """Transferencia entre campi: o campus de origem treina, os demais testam.

    Dois desenhos sobre o mesmo corpus: ``origem_para_<campus>`` (treino so no campus
    de origem) e ``deixa_um_campus_fora_<campus>`` (treino em todos os outros). O
    campus e um recorte de analise, nao uma instituicao diferente: taxonomia,
    sistema de chamados e autoria da referencia sao os mesmos.
    """
    n = len(corpus["textos"])
    por_campus: dict[str, list[int]] = {}
    for i in range(n):
        por_campus.setdefault(corpus["campus"][i], []).append(i)
    if origem not in por_campus:
        raise RuntimeError(f"campus de origem ausente do corpus: {origem}")
    alvos = sorted(c for c, idx in por_campus.items()
                   if c != origem and len(idx) >= minimo_teste)
    excluidos = sorted((c, len(idx)) for c, idx in por_campus.items()
                       if c != origem and len(idx) < minimo_teste)
    cenarios: list[dict[str, Any]] = []
    for c in alvos:
        cenarios.append({"nome": f"origem_para_{c}", "tipo": "origem_unica",
                         "treino": por_campus[origem], "teste": por_campus[c]})
    for c in [origem, *alvos]:
        cenarios.append({"nome": f"deixa_um_campus_fora_{c}", "tipo": "deixa_um_fora",
                         "treino": [i for i in range(n) if corpus["campus"][i] != c],
                         "teste": por_campus[c]})
    resultados = []
    with lstm_deterministico(semente):
        for cen in cenarios:
            por_modelo = []
            for nome in modelos:
                registrar(f"[campi] {cen['nome']}: {nome}")
                por_modelo.append(avaliar_divisao(nome, corpus, cen["treino"], cen["teste"],
                                                  semente, detalhar=True))
            resultados.append({"cenario": cen["nome"], "tipo": cen["tipo"],
                               "treino": len(cen["treino"]), "teste": len(cen["teste"]),
                               "categorias_no_treino": len({corpus["rotulos"][i]
                                                            for i in cen["treino"]}),
                               "modelos": por_modelo})
    return {"schema_version": 1, "trilha": "B", "semente": semente, "origem": origem,
            "minimo_teste": minimo_teste, "modelos": modelos,
            "campi_excluidos_por_tamanho": [{"campus": c, "n": k} for c, k in excluidos],
            "cenarios": resultados}


def gravar_campi(relatorio: dict[str, Any], digitais: dict[str, str],
                 quando: str, saidas: dict[str, Path] = SAIDAS) -> None:
    cb.garantir_fora_do_congelado(saidas["campi_json"])
    saidas["campi_json"].parent.mkdir(parents=True, exist_ok=True)
    saidas["campi_json"].write_text(json.dumps(
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


def etapa_calibracao_candidatos(corpus: dict[str, Any], nomes: tuple[str, ...] = ma.NOMES,
                                predicoes: Path = SAIDAS["predicoes_todas"],
                                gerar_embeddings=ma.calcular_embeddings,
                                registrar=rmc._log) -> dict[str, Any]:
    """Calibracao e automacao seletiva dos modelos candidatos, como nos sete base.

    Usa as predicoes fora de dobra de `alternativas` como dobra externa e o mesmo
    reajuste na dobra interna da etapa `calibracao`.
    """
    nomes = list(nomes)
    externas = cc.carregar_predicoes(predicoes)["por_modelo"]
    ausentes = [m for m in nomes if m not in externas]
    if ausentes:
        raise RuntimeError(f"Modelos sem predicoes das alternativas: {ausentes}")
    tabela: dict[str, Any] = {}
    if any("embedding" in n for n in nomes):
        registrar("[candidatos] calculando embeddings")
        tabela = gerar_embeddings(sorted(set(corpus["textos"])), registrar=registrar)
    with modelos_alternativos_ativos(tabela):
        relatorio = cc.montar_relatorio(corpus, externas, nomes, registrar=registrar)
    relatorio["trilha"] = "B"
    relatorio["encoder"] = ma.MODELO_EMBEDDING_PADRAO
    return relatorio


def gravar_calibracao_candidatos(relatorio: dict[str, Any], digitais: dict[str, str],
                                 quando: str, saidas: dict[str, Path] = SAIDAS) -> None:
    cb.garantir_fora_do_congelado(saidas["calibracao_candidatos_json"])
    saidas["calibracao_candidatos_json"].parent.mkdir(parents=True, exist_ok=True)
    saidas["calibracao_candidatos_json"].write_text(json.dumps(
        {**relatorio, "hash_corte": digitais["hash_corte"], "gerado_em": quando,
         "script_origem": "src/trilha_b.py"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")


# ------------------------------------------------------------- alternativas --

@contextlib.contextmanager
def modelos_alternativos_ativos(tabela: dict[str, Any]):
    """Faz o zoo reconhecer os modelos candidatos, que dividem as mesmas dobras."""
    original = rmc.zoo.criar_modelo

    def criar(nome: str):
        if (nome or "").strip().lower() in ma.NOMES:
            return ma.criar_modelo(nome.strip().lower(), tabela)
        return original(nome)

    rmc.zoo.criar_modelo = criar
    try:
        yield
    finally:
        rmc.zoo.criar_modelo = original


def etapa_alternativas(corpus: dict[str, Any], nomes: tuple[str, ...] = ma.NOMES,
                       gerar_embeddings=ma.calcular_embeddings,
                       semente: int = SEMENTE_PADRAO, registrar=rmc._log) -> dict[str, Any]:
    """Modelos candidatos nas mesmas dobras (OOF) e nos mesmos cenarios temporais."""
    nomes = list(nomes)
    tabela: dict[str, Any] = {}
    if any("embedding" in n for n in nomes):
        registrar("[alternativas] calculando embeddings")
        tabela = gerar_embeddings(sorted(set(corpus["textos"])), registrar=registrar)
    with modelos_alternativos_ativos(tabela):
        retreino = etapa_retreino(corpus, nomes, semente, registrar)
        temporal = etapa_temporal(corpus, nomes, semente=semente, registrar=registrar)
    return {"retreino": retreino, "temporal": temporal,
            "encoder": ma.MODELO_EMBEDDING_PADRAO}


def gravar_alternativas(resultado: dict[str, Any], corpus: dict[str, Any],
                        digitais: dict[str, str], quando: str,
                        saidas: dict[str, Path] = SAIDAS) -> None:
    """Grava o relatorio e as predicoes; junta as predicoes aos sete modelos base."""
    for chave in ("alternativas_json", "alternativas_pred", "predicoes_todas"):
        cb.garantir_fora_do_congelado(saidas[chave])
    carimbo = {"hash_corte": digitais["hash_corte"], "gerado_em": quando,
               "script_origem": "src/trilha_b.py"}
    saidas["alternativas_json"].parent.mkdir(parents=True, exist_ok=True)
    saidas["alternativas_json"].write_text(json.dumps({
        "trilha": "B", "encoder": resultado["encoder"],
        "retreino": _publicavel(resultado["retreino"]),
        "temporal": resultado["temporal"], **carimbo},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rmc.escrever_predicoes(saidas["alternativas_pred"], corpus,
                           resultado["retreino"]["_resultados"])
    base = saidas["retreino_pred"]
    if base.exists():
        linhas = base.read_text(encoding="utf-8").splitlines()
        novas = saidas["alternativas_pred"].read_text(encoding="utf-8").splitlines()[1:]
        saidas["predicoes_todas"].write_text("\n".join(linhas + novas) + "\n",
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
                 predicoes: Path = SAIDAS["predicoes_todas"]) -> dict[str, Any]:
    """Camada de regras de periodicidade contra os modelos puros.

    Aplica a regra sobre as predicoes *out-of-fold* de todos os modelos
    (`predicoes_com_alternativas.csv`), nos mesmos registros e particoes. A referencia humana nao e alterada.
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


# --------------------------------------------------------------- historica --

def etapa_historica(corpus: dict[str, Any],
                    predicoes: Path = SAIDAS["predicoes_todas"]) -> dict[str, Any]:
    """Concordancia, ganho liquido e dispersao contra a categoria historica (coluna C).

    Usa as predicoes *out-of-fold* de todos os modelos; a referencia humana arbitra
    quem acerta em cada divergencia. Nao treina nada.
    """
    dados = crm.carregar_predicoes(predicoes)
    chaves = corpus["chaves"]
    faltam = [c for c in chaves if c not in dados["referencia"]]
    if faltam:
        raise RuntimeError(f"{len(faltam)} registros do corpus sem predicao")
    referencias = [dados["referencia"][c] for c in chaves]
    por_modelo = {m: [p[c] for c in chaves] for m, p in dados["por_modelo"].items()}
    relatorio = ch.montar_relatorio(list(corpus["historicas"]), referencias, por_modelo)
    relatorio["trilha"] = "B"
    return relatorio


def gravar_historica(relatorio: dict[str, Any], digitais: dict[str, str],
                     quando: str, saidas: dict[str, Path] = SAIDAS) -> None:
    cb.garantir_fora_do_congelado(saidas["historica_json"])
    saidas["historica_json"].parent.mkdir(parents=True, exist_ok=True)
    saidas["historica_json"].write_text(json.dumps(
        {**relatorio, "hash_corte": digitais["hash_corte"], "gerado_em": quando,
         "script_origem": "src/trilha_b.py"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")


# --------------------------------------------------------------------- cli --

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("etapa", choices=["particoes", "retreino", "temporal", "calibracao",
                                     "regras", "historica", "kfold", "alternativas", "campi",
                                     "candidatos", "ufrn", "reverso", "completa"])
    p.add_argument("--ufrn-fonte", default=vu.URL_PADRAO,
                   help="URL ou arquivo CSV da base da UFRN (etapa ufrn)")
    p.add_argument("--por-divisao", type=int, default=300)
    p.add_argument("--por-divisao-treino", type=int, default=5000,
                   help="maximo de requisicoes da UFRN por divisao no treino (etapa reverso)")
    p.add_argument("--ano-minimo", type=int, default=2022)
    p.add_argument("--origem", default=CAMPUS_ORIGEM_PADRAO,
                   help="campus que treina na etapa campi")
    p.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    p.add_argument("--credenciais", default=None)
    p.add_argument("--aba", default="", help="aba de snapshot (padrao: a do manifesto)")
    p.add_argument("--snapshot-json", type=Path, default=None,
                   help="copia local do snapshot, em vez de ler a planilha")
    p.add_argument("--modelos", default=",".join(rmc.MODELOS_PADRAO))
    p.add_argument("--modelos-ufrn", default="",
                   help="modelos das etapas ufrn e reverso (padrao: os constantes do modulo)")
    p.add_argument("--semente", type=int, default=SEMENTE_PADRAO)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    manifesto = json.loads(MANIFESTO_B.read_text(encoding="utf-8"))
    aba = args.aba or manifesto["aba_snapshot"]
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if args.snapshot_json:
        linhas = ler_snapshot_json(args.snapshot_json)
    else:
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
    if args.etapa == "alternativas":
        res = etapa_alternativas(corpus, semente=args.semente)
        gravar_alternativas(res, corpus, digitais, quando)
        for m in res["retreino"]["modelos"]:
            print(m["modelo"], m["acuracia"], m["macro_f1"])
        for c in res["temporal"]["cenarios"]:
            print(c["cenario"], {m["modelo"]: m["acuracia"] for m in c["modelos"]})
        return 0
    if args.etapa in ("reverso", "ufrn") and Path(args.ufrn_fonte).is_file():
        digitais = {**digitais, "fonte_ufrn_sha256": hashlib.sha256(
            Path(args.ufrn_fonte).read_bytes()).hexdigest()}
    if args.etapa == "completa":
        todas = [dict(l, id_ufrn=f"{l['ano']}-{l['numero']}") for l in vu.ler_ufrn(args.ufrn_fonte)
                 if l["divisao"] and l["ano"].isdigit() and int(l["ano"]) >= args.ano_minimo]
        res = etapa_ufrn(corpus, todas,
                         nomes=tuple(m for m in args.modelos_ufrn.split(",") if m)
                         or MODELOS_UFRN_PADRAO, semente=args.semente)
        gravar_ufrn(res, digitais, quando, {
            **SAIDAS, "ufrn_resumo_json": DADOS_B / "ufrn_completo_resumo.json",
            "ufrn_avaliacao_csv": RAIZ / "saidas_privadas" / "ufrn_completa_classificada.csv"})
        for nome, m in res["resumo"]["modelos"].items():
            print(nome, len(todas), m["concordancia_com_correspondencia"])
        return 0
    if args.etapa == "reverso":
        res = etapa_ufrn_reverso(corpus, vu.ler_ufrn(args.ufrn_fonte),
                                 nomes=tuple(m for m in args.modelos_ufrn.split(",") if m)
                                 or MODELOS_REVERSO_PADRAO,
                                 por_divisao=args.por_divisao_treino, semente=args.semente)
        gravar_ufrn_reverso(res, corpus, digitais, quando)
        for nome, m in res["resultados"].items():
            print(nome, "UFRN", m["ufrn_teste"]["acuracia"], "nossa base",
                  m["nossa_base"]["acuracia"])
        return 0
    if args.etapa == "ufrn":
        amostra = vu.amostrar(vu.ler_ufrn(args.ufrn_fonte), por_divisao=args.por_divisao,
                              ano_minimo=args.ano_minimo, semente=args.semente)
        res = etapa_ufrn(corpus, amostra,
                         nomes=tuple(m for m in args.modelos_ufrn.split(",") if m)
                         or MODELOS_UFRN_PADRAO, semente=args.semente)
        gravar_ufrn(res, digitais, quando)
        for nome, m in res["resumo"]["modelos"].items():
            print(nome, "concordancia com a correspondencia proposta:",
                  m["concordancia_com_correspondencia"])
        return 0
    if args.etapa == "candidatos":
        rel = etapa_calibracao_candidatos(corpus)
        gravar_calibracao_candidatos(rel, digitais, quando)
        for m in rel["modelos"]:
            print(m["modelo"], "ECE", m["bruta"]["ece"], "->", m["calibrada"]["ece"])
        return 0
    if args.etapa == "campi":
        rel = etapa_campi(corpus, modelos, origem=args.origem, semente=args.semente)
        gravar_campi(rel, digitais, quando)
        for c in rel["cenarios"]:
            print(c["cenario"], c["treino"], c["teste"],
                  {m["modelo"]: m["acuracia"] for m in c["modelos"]})
        return 0
    if args.etapa == "kfold":
        rel = etapa_kfold(corpus, modelos)
        gravar_kfold(rel, digitais, quando)
        for r in rel["resultados"]:
            print(r["modelo"], r["kfold"]["acuracia"], r["groupkfold"]["acuracia"])
        return 0
    if args.etapa == "historica":
        rel = etapa_historica(corpus)
        gravar_historica(rel, digitais, quando)
        for m in rel["modelos"]:
            print(m["modelo"], m["concordancia"]["acordo_bruto"], m["reclassificacao"]["ganho_liquido"])
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
