#!/usr/bin/env python3
"""Seleciona o proximo lote elegivel para classificacao inicial, sem escrever."""

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


CONFIG_PADRAO = Path(__file__).resolve().parents[1] / "config_experimento.json"


@dataclass(frozen=True)
class Candidato:
    linha_planilha: int
    id_chamado: str
    titulo: str
    categoria_original: str
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


def selecionar_candidatos(valores: list[list[Any]], tamanho_lote: int) -> list[Candidato]:
    if not valores:
        return []

    cabecalho = valores[0]
    idx = indice_colunas(cabecalho)
    idx_id = idx.get(normalizar_cabecalho("ID Chamado"))
    idx_titulo = idx.get(normalizar_cabecalho("TÍTULO"))
    idx_categoria = idx.get(normalizar_cabecalho("CATEGORIA COMPLETA"))
    idx_classificacao = idx.get(normalizar_cabecalho("Classificação IA"))

    candidatos: list[Candidato] = []
    for posicao, linha in enumerate(valores[1:], start=2):
        if linha_vazia(linha):
            continue
        if obter(linha, idx_classificacao):
            continue

        texto = montar_texto(linha, idx)
        if not texto:
            continue

        candidatos.append(
            Candidato(
                linha_planilha=posicao,
                id_chamado=obter(linha, idx_id),
                titulo=obter(linha, idx_titulo),
                categoria_original=obter(linha, idx_categoria),
                texto_classificacao=texto,
            )
        )
        if len(candidatos) >= tamanho_lote:
            break

    return candidatos


def imprimir_candidatos(candidatos: list[Candidato]) -> None:
    print(f"candidatos_lote={len(candidatos)}")
    for candidato in candidatos:
        print(
            json.dumps(
                {
                    "linha_planilha": candidato.linha_planilha,
                    "id_chamado": candidato.id_chamado,
                    "titulo": candidato.titulo[:120],
                    "categoria_original": candidato.categoria_original,
                    "tamanho_texto": len(candidato.texto_classificacao),
                },
                ensure_ascii=False,
            )
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seleciona o proximo lote de classificacao inicial. Nao escreve na planilha."
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
    candidatos = selecionar_candidatos(valores, tamanho_lote)

    print(f"modo=dry-run")
    print(f"run_id={config['run_id']}")
    print(f"aba={config['aba_principal']}")
    print(f"linhas_lidas_observado={len(valores)}")
    imprimir_candidatos(candidatos)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
