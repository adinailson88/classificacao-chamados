#!/usr/bin/env python3
"""Prepara abas experimentais da planilha, com dry-run por padrao."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


CONFIG_PADRAO = Path(__file__).resolve().parents[1] / "config_experimento.json"


CABECALHOS_ABAS = {
    "EXPERIMENTO_CONFIG": [
        "chave",
        "valor",
        "observacao",
    ],
    "LOG_TURNOS_CLASSIFICACAO": [
        "run_id",
        "turno",
        "linha_inicial",
        "linha_final",
        "qtd_processados",
        "qtd_true",
        "qtd_false",
        "taxa_concordancia",
        "confianca_media",
        "confianca_min",
        "confianca_max",
        "qtd_conf_menor_70",
        "qtd_conf_70_95",
        "qtd_conf_maior_igual_95",
        "executor",
        "data_hora",
    ],
    "LOG_LINHA_A_LINHA": [
        "run_id",
        "etapa",
        "turno",
        "linha_planilha",
        "id_chamado",
        "titulo",
        "categoria_original",
        "categoria_ia",
        "conferencia",
        "confianca",
        "executor",
        "criticidade",
        "data_hora",
    ],
    "SNAPSHOT_ETAPA_1": [
        "run_id",
        "linha_planilha",
        "id_chamado",
        "categoria_original",
        "categoria_ia_etapa_1",
        "confianca_etapa_1",
        "executor_etapa_1",
        "criticidade_etapa_1",
        "conferencia_etapa_1",
        "data_snapshot",
    ],
    "LOG_TURNOS_RECLASSIFICACAO": [
        "run_id",
        "turno",
        "qtd_reclassificados",
        "corretos_antes",
        "incorretos_antes",
        "taxa_antes",
        "corretos_depois",
        "incorretos_depois",
        "taxa_depois",
        "corrigidos",
        "prejudicados",
        "mantidos_corretos",
        "mantidos_errados",
        "ganho_liquido",
        "variacao_media_confianca",
        "data_hora",
    ],
    "VALIDACAO_HUMANA": [
        "run_id",
        "id_chamado",
        "titulo",
        "descricao_glpi",
        "titulo_osm",
        "descricao_osm",
        "categoria_original",
        "categoria_ia_etapa_1",
        "categoria_ia_etapa_2",
        "categoria_validada",
        "decisao",
        "justificativa",
        "avaliador",
        "data_validacao",
        "usar_para_treino",
        "versao_taxonomia",
    ],
    "METRICAS_EXPERIMENTO": [
        "run_id",
        "metrica",
        "etapa",
        "valor",
        "numerador",
        "denominador",
        "observacao",
        "data_hora",
    ],
}


def carregar_config(caminho: Path) -> dict[str, Any]:
    with caminho.open("r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def montar_abas(config: dict[str, Any]) -> list[dict[str, Any]]:
    nomes = list(config["abas_experimento"].values())
    return [
        {
            "nome": nome,
            "cabecalho": CABECALHOS_ABAS.get(nome, []),
        }
        for nome in nomes
    ]


def chamar_get(url_base: str, token: str, params: dict[str, str]) -> dict[str, Any]:
    query = dict(params)
    query["token"] = token
    url = url_base.rstrip() + "?" + urlencode(query)

    with urlopen(url, timeout=120) as resposta:
        return json.loads(resposta.read().decode("utf-8"))


def chamar_post(url_base: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = dict(payload)
    body["token"] = token
    dados = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = Request(
        url_base.rstrip(),
        data=dados,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(req, timeout=180) as resposta:
        return json.loads(resposta.read().decode("utf-8"))


def imprimir_plano(abas: list[dict[str, Any]], existentes: set[str]) -> None:
    for item in abas:
        nome = item["nome"]
        status = "existe" if nome in existentes else "criar"
        print(f"{status}: {nome} colunas={len(item['cabecalho'])}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepara abas experimentais. Sem --aplicar, faz apenas dry-run."
    )
    parser.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    parser.add_argument("--apps-script-url", default=os.getenv("APPS_SCRIPT_URL"))
    parser.add_argument("--token", default=os.getenv("APPS_SCRIPT_TOKEN"))
    parser.add_argument("--aplicar", action="store_true", help="Cria/atualiza abas na planilha.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.apps_script_url or not args.token:
        print("Informe --apps-script-url e --token, ou defina APPS_SCRIPT_URL/APPS_SCRIPT_TOKEN.", file=sys.stderr)
        return 2

    config = carregar_config(args.config)
    abas = montar_abas(config)

    resposta = chamar_get(args.apps_script_url, args.token, {"action": "listar_abas"})
    if not resposta.get("ok"):
        print(json.dumps(resposta, ensure_ascii=False), file=sys.stderr)
        return 1

    existentes = {item["name"] for item in resposta.get("sheets", [])}
    imprimir_plano(abas, existentes)

    if not args.aplicar:
        print("modo=dry-run")
        return 0

    resultado = chamar_post(
        args.apps_script_url,
        args.token,
        {
            "action": "preparar_abas_experimento",
            "abas": abas,
        },
    )
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0 if resultado.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
