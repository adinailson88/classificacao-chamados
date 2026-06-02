#!/usr/bin/env python3
"""Registra a ficha tecnica do experimento na aba EXPERIMENTO_CONFIG."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


CONFIG_PADRAO = Path(__file__).resolve().parents[1] / "config_experimento.json"


def carregar_config(caminho: Path) -> dict[str, Any]:
    with caminho.open("r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


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


def git_valor(args: list[str]) -> str:
    try:
        return subprocess.check_output(["git", *args], text=True, stderr=subprocess.DEVNULL).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def montar_linhas(config: dict[str, Any], validacao: dict[str, Any]) -> list[list[Any]]:
    classificacao = config["classificacao"]
    reclassificacao = config["reclassificacao"]
    commit = git_valor(["rev-parse", "--short", "HEAD"])
    branch = git_valor(["branch", "--show-current"])

    linhas = [
        ["chave", "valor", "observacao"],
        ["run_id", config["run_id"], "Identificador unico da execucao experimental"],
        ["data_registro_utc", datetime.now(timezone.utc).isoformat(), "Gerado pelo script registrar_config_experimento.py"],
        ["spreadsheet_id", config["spreadsheet_id"], "ID da planilha experimental"],
        ["aba_principal", config["aba_principal"], "Aba analisada"],
        ["range_leitura", config["range_leitura"], "Intervalo util da aba principal"],
        ["total_linhas_lidas", validacao.get("totalRowsRead", ""), "Total retornado pelo Apps Script"],
        ["total_linhas_dados", validacao.get("totalDataRows", ""), "Linhas abaixo do cabecalho"],
        ["total_linhas_nao_vazias", validacao.get("totalNonEmptyRows", ""), "Base efetiva do experimento"],
        ["last_row", validacao.get("lastRow", ""), "Ultima linha informada pela planilha"],
        ["last_column", validacao.get("lastColumn", ""), "Ultima coluna informada pela planilha"],
        ["cabecalho", " | ".join(str(x) for x in validacao.get("header", [])), "Cabecalho real validado"],
        ["tamanho_lote_classificacao", classificacao["tamanho_lote"], "Turno logico da etapa 1"],
        ["limiar_confianca_baixa", classificacao["limiar_confianca_baixa"], "Faixa inferior de confianca"],
        ["limiar_alta_confianca", classificacao["limiar_alta_confianca"], "Corte para alta confianca"],
        ["reclassificacao_habilitada", reclassificacao["habilitada"], "Estado inicial do experimento"],
        ["tamanho_lote_reclassificacao", reclassificacao["tamanho_lote"], "Lote planejado da etapa 2"],
        ["reclassificar_confianca_menor_que", reclassificacao["selecionar_confianca_menor_que"], "Criterio planejado"],
        ["repositorio", "https://github.com/adinailson88/classifica-o-chamados", "Repositorio do experimento"],
        ["branch", branch, "Branch local no momento do registro"],
        ["commit", commit, "Commit local no momento do registro"],
    ]
    return linhas


def imprimir_linhas(linhas: list[list[Any]]) -> None:
    for linha in linhas:
        print("\t".join(str(celula) for celula in linha))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Registra EXPERIMENTO_CONFIG. Sem --aplicar, faz apenas dry-run."
    )
    parser.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    parser.add_argument("--apps-script-url", default=os.getenv("APPS_SCRIPT_URL"))
    parser.add_argument("--token", default=os.getenv("APPS_SCRIPT_TOKEN"))
    parser.add_argument("--aplicar", action="store_true", help="Grava EXPERIMENTO_CONFIG na planilha.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.apps_script_url or not args.token:
        print("Informe --apps-script-url e --token, ou defina APPS_SCRIPT_URL/APPS_SCRIPT_TOKEN.", file=sys.stderr)
        return 2

    config = carregar_config(args.config)
    validacao = chamar_get(
        args.apps_script_url,
        args.token,
        {
            "action": "validar",
            "sheet": config["aba_principal"],
            "range": config["range_leitura"],
        },
    )

    if not validacao.get("ok"):
        print(json.dumps(validacao, ensure_ascii=False), file=sys.stderr)
        return 1

    linhas = montar_linhas(config, validacao)
    imprimir_linhas(linhas)

    if not args.aplicar:
        print("modo=dry-run")
        return 0

    resultado = chamar_post(
        args.apps_script_url,
        args.token,
        {
            "action": "registrar_config_experimento",
            "sheet": config["abas_experimento"]["config"],
            "linhas": linhas,
        },
    )
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0 if resultado.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
