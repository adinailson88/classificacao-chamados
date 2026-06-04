#!/usr/bin/env python3
"""Exporta o resultado de uma etapa para a planilha em UMA gravacao em lote.

Le dados/classificacao_etapa_1.json e envia as colunas G:J (Classificacao IA,
Avaliacao %, Executor, Criticidade) em um unico doPost (action=exportar_lote).
O Apps Script faz read-modify-write em bloco: 1 leitura + 1 escrita, pula linhas
com CONFERENCIA (coluna M) = TRUE e nao sobrescreve celula com valor vazio.

Sem --aplicar, faz dry-run (monta e valida o payload, nao chama a planilha).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
DADOS = RAIZ / "dados"
CLASSIFICACAO_PADRAO = DADOS / "classificacao_etapa_1.json"
MANIFEST = DADOS / "manifest_exportacao.json"

# Colunas de saida no layout reduzido (1-based): G=7 ... J=10.
COL_INICIO = 7
COL_FIM = 10
COL_CONFERENCIA = 13  # M
FUSO_BAHIA = timezone(timedelta(hours=-3))


def agora_bahia() -> str:
    return datetime.now(FUSO_BAHIA).strftime("%Y-%m-%dT%H:%M:%S-03:00")


def carregar_json(caminho: Path) -> Any:
    with caminho.open("r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def gravar_json(caminho: Path, dados: Any) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=2)
        arquivo.write("\n")


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


def montar_linhas(resultado: dict[str, Any]) -> list[dict[str, Any]]:
    """Converte o resultado da classificacao em linhas G:J para o lote."""
    linhas = []
    for item in resultado.get("linhas", []):
        linha_planilha = item.get("linha_planilha")
        if not linha_planilha:
            continue
        valores = [
            str(item.get("classificacao_ia", "") or ""),
            item.get("avaliacao_pct", ""),
            str(item.get("executor", "") or ""),
            str(item.get("criticidade", "") or ""),
        ]
        linhas.append({"linha": int(linha_planilha), "valores": valores})
    return linhas


def atualizar_manifest(registro: dict[str, Any]) -> None:
    if MANIFEST.exists():
        manifest = carregar_json(MANIFEST)
    else:
        manifest = {"exportacoes": []}
    manifest.setdefault("exportacoes", []).append(registro)
    gravar_json(MANIFEST, manifest)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Exporta uma etapa para a planilha em 1 gravacao em lote (G:J)."
    )
    parser.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    parser.add_argument("--classificacao", type=Path, default=CLASSIFICACAO_PADRAO)
    parser.add_argument("--etapa", default="classificacao_etapa_1")
    parser.add_argument("--apps-script-url", default=os.getenv("APPS_SCRIPT_URL"))
    parser.add_argument("--token", default=os.getenv("APPS_SCRIPT_TOKEN"))
    parser.add_argument(
        "--aplicar",
        action="store_true",
        help="Efetua a gravacao em lote na planilha. Sem isso, faz dry-run.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = carregar_json(args.config)
    aba = config["aba_principal"]
    resultado = carregar_json(args.classificacao)
    linhas = montar_linhas(resultado)

    print(f"etapa={args.etapa}")
    print(f"aba={aba}")
    print(f"colunas=G:J")
    print(f"linhas_para_exportar={len(linhas)}")

    if not linhas:
        print("Informação insuficiente para verificar.")
        return 1

    if not args.aplicar:
        print("modo=dry-run (nenhuma escrita na planilha)")
        print(json.dumps(linhas[:3], ensure_ascii=False, indent=2))
        return 0

    if not args.apps_script_url or not args.token:
        print(
            "Informe --apps-script-url e --token, ou defina APPS_SCRIPT_URL/APPS_SCRIPT_TOKEN.",
            file=sys.stderr,
        )
        return 2

    payload = {
        "action": "exportar_lote",
        "sheet": aba,
        "run_id": resultado.get("run_id", ""),
        "etapa": args.etapa,
        "col_inicio": COL_INICIO,
        "col_fim": COL_FIM,
        "col_conferencia": COL_CONFERENCIA,
        "respeitar_conferencia": True,
        "ignorar_vazios": True,
        "linhas": linhas,
    }
    resposta = chamar_post(args.apps_script_url, args.token, payload)
    print(json.dumps(resposta, ensure_ascii=False, indent=2))

    if not resposta.get("ok"):
        return 1

    atualizar_manifest(
        {
            "etapa": args.etapa,
            "aba": aba,
            "colunas": "G:J",
            "linhas_enviadas": len(linhas),
            "linhas_gravadas": resposta.get("linhas_gravadas"),
            "linhas_puladas_conferencia": resposta.get("linhas_puladas_conferencia"),
            "gerado_em": agora_bahia(),
            "run_id": resultado.get("run_id", ""),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
