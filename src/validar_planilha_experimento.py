#!/usr/bin/env python3
"""Valida a estrutura da planilha experimental de classificacao de chamados."""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen


CONFIG_PADRAO = Path(__file__).resolve().parents[1] / "config_experimento.json"


@dataclass(frozen=True)
class ResultadoValidacao:
    total_linhas_lidas: int
    total_linhas_dados: int
    total_linhas_nao_vazias: int
    cabecalho_ok: bool
    colunas_ausentes: list[str]
    colunas_extras: list[str]


def normalizar_cabecalho(valor: Any) -> str:
    texto = str(valor or "").strip()
    texto = unicodedata.normalize("NFKC", texto)
    return " ".join(texto.split()).casefold()


def linha_vazia(linha: list[Any]) -> bool:
    return all(str(celula or "").strip() == "" for celula in linha)


def carregar_config(caminho: Path) -> dict[str, Any]:
    with caminho.open("r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def validar_matriz(valores: list[list[Any]], colunas_esperadas: list[str]) -> ResultadoValidacao:
    if not valores:
        return ResultadoValidacao(
            total_linhas_lidas=0,
            total_linhas_dados=0,
            total_linhas_nao_vazias=0,
            cabecalho_ok=False,
            colunas_ausentes=colunas_esperadas,
            colunas_extras=[],
        )

    cabecalho = valores[0]
    dados = valores[1:]

    esperadas_norm = [normalizar_cabecalho(coluna) for coluna in colunas_esperadas]
    cabecalho_norm = [normalizar_cabecalho(coluna) for coluna in cabecalho]

    ausentes = [
        original
        for original, normalizada in zip(colunas_esperadas, esperadas_norm)
        if normalizada not in cabecalho_norm
    ]
    extras = [
        str(original or "").strip()
        for original, normalizada in zip(cabecalho, cabecalho_norm)
        if normalizada and normalizada not in esperadas_norm
    ]

    nao_vazias = [linha for linha in dados if not linha_vazia(linha)]

    return ResultadoValidacao(
        total_linhas_lidas=len(valores),
        total_linhas_dados=len(dados),
        total_linhas_nao_vazias=len(nao_vazias),
        cabecalho_ok=not ausentes,
        colunas_ausentes=ausentes,
        colunas_extras=extras,
    )


def ler_google_sheets(config: dict[str, Any], credenciais: Path) -> list[list[Any]]:
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError as exc:
        raise RuntimeError(
            "Dependencias ausentes. Instale com: pip install -r requirements.txt"
        ) from exc

    escopos = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(str(credenciais), scopes=escopos)
    cliente = gspread.authorize(creds)
    planilha = cliente.open_by_key(config["spreadsheet_id"])
    aba = planilha.worksheet(config["aba_principal"])
    return aba.get(config.get("range_leitura", "A:M"))


def validar_apps_script(config: dict[str, Any], url_base: str, token: str) -> ResultadoValidacao:
    params = {
        "action": "validar",
        "sheet": config["aba_principal"],
        "range": config.get("range_leitura", "A:M"),
        "token": token,
    }
    url = url_base.rstrip() + "?" + urlencode(params)

    with urlopen(url, timeout=120) as resposta:
        payload = json.loads(resposta.read().decode("utf-8"))

    if not payload.get("ok"):
        raise RuntimeError("Falha Apps Script: " + json.dumps(payload, ensure_ascii=False))

    header = payload.get("header") or []
    matriz_minima = [header]
    resultado = validar_matriz(matriz_minima, config["colunas_esperadas"])

    return ResultadoValidacao(
        total_linhas_lidas=int(payload.get("totalRowsRead", 0)),
        total_linhas_dados=int(payload.get("totalDataRows", 0)),
        total_linhas_nao_vazias=int(payload.get("totalNonEmptyRows", 0)),
        cabecalho_ok=resultado.cabecalho_ok,
        colunas_ausentes=resultado.colunas_ausentes,
        colunas_extras=resultado.colunas_extras,
    )


def imprimir_resultado(resultado: ResultadoValidacao) -> None:
    print(f"total_linhas_lidas={resultado.total_linhas_lidas}")
    print(f"total_linhas_dados={resultado.total_linhas_dados}")
    print(f"total_linhas_nao_vazias={resultado.total_linhas_nao_vazias}")
    print(f"cabecalho_ok={str(resultado.cabecalho_ok).lower()}")
    print("colunas_ausentes=" + json.dumps(resultado.colunas_ausentes, ensure_ascii=False))
    print("colunas_extras=" + json.dumps(resultado.colunas_extras, ensure_ascii=False))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Valida cabecalho e linhas nao vazias da planilha experimental."
    )
    parser.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    parser.add_argument("--credenciais", type=Path, help="Arquivo JSON de credenciais Google.")
    parser.add_argument("--apps-script-url", help="URL /exec do Web App do Apps Script.")
    parser.add_argument("--token", help="Token simples configurado no Apps Script.")
    parser.add_argument(
        "--arquivo-valores",
        type=Path,
        help="Arquivo JSON local com matriz de valores para teste offline.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = carregar_config(args.config)

    if args.arquivo_valores:
        with args.arquivo_valores.open("r", encoding="utf-8") as arquivo:
            valores = json.load(arquivo)
        resultado = validar_matriz(valores, config["colunas_esperadas"])
    elif args.apps_script_url:
        if not args.token:
            print("Informe --token ao usar --apps-script-url.", file=sys.stderr)
            return 2
        resultado = validar_apps_script(config, args.apps_script_url, args.token)
    elif args.credenciais:
        valores = ler_google_sheets(config, args.credenciais)
        resultado = validar_matriz(valores, config["colunas_esperadas"])
    else:
        print("Informe --apps-script-url, --credenciais ou --arquivo-valores.", file=sys.stderr)
        return 2

    imprimir_resultado(resultado)
    return 0 if resultado.cabecalho_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
