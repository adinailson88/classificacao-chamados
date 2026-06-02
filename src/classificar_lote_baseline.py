#!/usr/bin/env python3
"""Classifica o proximo lote em dry-run com baseline TF-IDF, sem escrever."""

from __future__ import annotations

import argparse
import json
import os
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


CONFIG_PADRAO = Path(__file__).resolve().parents[1] / "config_experimento.json"
EXECUTOR = "Baseline_TFIDF_LogReg_DRY_RUN"


@dataclass(frozen=True)
class Registro:
    linha_planilha: int
    id_chamado: str
    titulo: str
    categoria_original: str
    classificacao_ia: str
    texto_classificacao: str


def normalizar_cabecalho(valor: Any) -> str:
    texto = str(valor or "").strip()
    texto = unicodedata.normalize("NFKC", texto)
    return " ".join(texto.split()).casefold()


def linha_vazia(linha: list[Any]) -> bool:
    return all(str(celula or "").strip() == "" for celula in linha)


def carregar_config(caminho: Path) -> dict[str, Any]:
    with caminho.open("r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def chamar_get(url_base: str, token: str, params: dict[str, str]) -> dict[str, Any]:
    query = dict(params)
    query["token"] = token
    url = url_base.rstrip() + "?" + urlencode(query)

    with urlopen(url, timeout=180) as resposta:
        return json.loads(resposta.read().decode("utf-8"))


def indice_colunas(cabecalho: list[Any]) -> dict[str, int]:
    return {normalizar_cabecalho(nome): idx for idx, nome in enumerate(cabecalho)}


def obter(linha: list[Any], idx: int | None) -> str:
    if idx is None or idx >= len(linha):
        return ""
    return str(linha[idx] or "").strip()


def montar_texto(linha: list[Any], idx: dict[str, int]) -> str:
    campos = [
        obter(linha, idx.get(normalizar_cabecalho("TÍTULO"))),
        obter(linha, idx.get(normalizar_cabecalho("DESCRIÇÃO GLPI"))),
        obter(linha, idx.get(normalizar_cabecalho("TÍTULO O.S.M."))),
        obter(linha, idx.get(normalizar_cabecalho("DESCRIÇÃO O.S.M."))),
    ]
    return "\n".join(campo for campo in campos if campo)


def montar_registros(valores: list[list[Any]]) -> list[Registro]:
    if not valores:
        return []

    idx = indice_colunas(valores[0])
    idx_id = idx.get(normalizar_cabecalho("ID Chamado"))
    idx_titulo = idx.get(normalizar_cabecalho("TÍTULO"))
    idx_categoria = idx.get(normalizar_cabecalho("CATEGORIA COMPLETA"))
    idx_classificacao = idx.get(normalizar_cabecalho("Classificação IA"))

    registros: list[Registro] = []
    for posicao, linha in enumerate(valores[1:], start=2):
        if linha_vazia(linha):
            continue

        texto = montar_texto(linha, idx)
        if not texto:
            continue

        registros.append(
            Registro(
                linha_planilha=posicao,
                id_chamado=obter(linha, idx_id),
                titulo=obter(linha, idx_titulo),
                categoria_original=obter(linha, idx_categoria),
                classificacao_ia=obter(linha, idx_classificacao),
                texto_classificacao=texto,
            )
        )
    return registros


def selecionar_lote(registros: list[Registro], tamanho_lote: int) -> list[Registro]:
    candidatos = [
        registro
        for registro in registros
        if registro.categoria_original and not registro.classificacao_ia
    ]
    return candidatos[:tamanho_lote]


def treinar_baseline(registros_treino: list[Registro]) -> Pipeline:
    textos = [registro.texto_classificacao for registro in registros_treino]
    categorias = [registro.categoria_original for registro in registros_treino]

    modelo = Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    strip_accents="unicode",
                    lowercase=True,
                    ngram_range=(1, 2),
                    min_df=1,
                    max_features=30000,
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    solver="lbfgs",
                ),
            ),
        ]
    )
    modelo.fit(textos, categorias)
    return modelo


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classifica o proximo lote com baseline local em dry-run. Nao escreve na planilha."
    )
    parser.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    parser.add_argument("--apps-script-url", default=os.getenv("APPS_SCRIPT_URL"))
    parser.add_argument("--token", default=os.getenv("APPS_SCRIPT_TOKEN"))
    parser.add_argument("--limite", type=int, help="Sobrescreve o tamanho_lote da configuracao.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.apps_script_url or not args.token:
        print("Informe --apps-script-url e --token, ou defina APPS_SCRIPT_URL/APPS_SCRIPT_TOKEN.", file=sys.stderr)
        return 2

    config = carregar_config(args.config)
    tamanho_lote = args.limite or int(config["classificacao"]["tamanho_lote"])
    resposta = chamar_get(
        args.apps_script_url,
        args.token,
        {
            "action": "ler",
            "sheet": config["aba_principal"],
            "range": config["range_leitura"],
        },
    )
    if not resposta.get("ok"):
        print(json.dumps(resposta, ensure_ascii=False), file=sys.stderr)
        return 1

    valores = resposta.get("values") or []
    registros = montar_registros(valores)
    lote = selecionar_lote(registros, tamanho_lote)
    linhas_lote = {registro.linha_planilha for registro in lote}
    treino = [
        registro
        for registro in registros
        if registro.categoria_original and registro.linha_planilha not in linhas_lote
    ]

    if len(lote) == 0:
        print("candidatos_lote=0")
        return 0
    if len(treino) < 2:
        print("Informação insuficiente para verificar.", file=sys.stderr)
        return 1

    modelo = treinar_baseline(treino)
    textos_lote = [registro.texto_classificacao for registro in lote]
    predicoes = modelo.predict(textos_lote)
    probabilidades = modelo.predict_proba(textos_lote)

    print("modo=dry-run")
    print(f"executor={EXECUTOR}")
    print(f"run_id={config['run_id']}")
    print(f"linhas_lidas_observado={len(valores)}")
    print(f"registros_texto_observado={len(registros)}")
    print(f"registros_treino_observado={len(treino)}")
    print(f"candidatos_lote={len(lote)}")

    acertos_aparentes = 0
    for registro, predicao, probs in zip(lote, predicoes, probabilidades):
        confianca = float(max(probs))
        confere_historico = predicao == registro.categoria_original
        acertos_aparentes += int(confere_historico)
        print(
            json.dumps(
                {
                    "linha_planilha": registro.linha_planilha,
                    "id_chamado": registro.id_chamado,
                    "categoria_original": registro.categoria_original,
                    "categoria_prevista": str(predicao),
                    "confianca": round(confianca, 4),
                    "confere_historico": confere_historico,
                    "executor": EXECUTOR,
                },
                ensure_ascii=False,
            )
        )

    print(f"concordancia_aparente_lote={acertos_aparentes}/{len(lote)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
