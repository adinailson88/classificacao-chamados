#!/usr/bin/env python3
"""Registra snapshot inicial da base nao vazia antes da classificacao."""

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

    with urlopen(req, timeout=240) as resposta:
        return json.loads(resposta.read().decode("utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Registra snapshot inicial. Sem --aplicar, faz apenas dry-run."
    )
    parser.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    parser.add_argument("--apps-script-url", default=os.getenv("APPS_SCRIPT_URL"))
    parser.add_argument("--token", default=os.getenv("APPS_SCRIPT_TOKEN"))
    parser.add_argument("--aplicar", action="store_true", help="Grava SNAPSHOT_ETAPA_1 na planilha.")
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

    destino = config["abas_experimento"]["snapshot_etapa_1"]
    print(f"origem={config['aba_principal']}")
    print(f"destino={destino}")
    print(f"run_id={config['run_id']}")
    print(f"linhas_lidas_observado={validacao.get('totalRowsRead')}")
    print(f"linhas_nao_vazias_observado={validacao.get('totalNonEmptyRows')}")

    if not args.aplicar:
        print("modo=dry-run")
        return 0

    resultado = chamar_post(
        args.apps_script_url,
        args.token,
        {
            "action": "registrar_snapshot_inicial",
            "origem": config["aba_principal"],
            "destino": destino,
            "run_id": config["run_id"],
        },
    )
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0 if resultado.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
