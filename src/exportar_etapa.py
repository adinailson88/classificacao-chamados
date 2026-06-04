#!/usr/bin/env python3
"""Exporta o resultado de uma etapa para a planilha em UMA gravação em lote.

Lê dados/classificacao_etapa_1.json e grava as colunas G:J (Classificação IA,
Avaliação %, Executor, Criticidade) via conta de serviço (gspread), em um único
update em bloco: pula linhas com CONFERÊNCIA (col M) = TRUE e não sobrescreve
célula vazia (preserva J/Criticidade).

Sem --aplicar, faz dry-run (monta e valida o payload, não toca na planilha).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planilha as pl  # noqa: E402


RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
DADOS = RAIZ / "dados"
CLASSIFICACAO_PADRAO = DADOS / "classificacao_etapa_1.json"
MANIFEST = DADOS / "manifest_exportacao.json"

COL_INICIO = 7    # G
COL_FIM = 10      # J
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


def montar_linhas(resultado: dict[str, Any]) -> list[dict[str, Any]]:
    """Converte o resultado da classificação em linhas G:J para o lote."""
    linhas = []
    for item in resultado.get("linhas", []):
        linha_planilha = item.get("linha_planilha")
        if not linha_planilha:
            continue
        valores = [
            str(item.get("classificacao_ia", "") or ""),
            item.get("avaliacao", ""),  # fração 0-1 (coluna H formatada como %)
            str(item.get("executor", "") or ""),
            str(item.get("criticidade", "") or ""),
        ]
        linhas.append({"linha": int(linha_planilha), "valores": valores})
    return linhas


def atualizar_manifest(registro: dict[str, Any]) -> None:
    manifest = carregar_json(MANIFEST) if MANIFEST.exists() else {"exportacoes": []}
    manifest.setdefault("exportacoes", []).append(registro)
    gravar_json(MANIFEST, manifest)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Exporta uma etapa para a planilha em 1 gravação em lote (G:J)."
    )
    parser.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    parser.add_argument("--credenciais", default=None, help="Caminho da chave JSON da conta de serviço.")
    parser.add_argument("--classificacao", type=Path, default=CLASSIFICACAO_PADRAO)
    parser.add_argument("--etapa", default="classificacao_etapa_1")
    parser.add_argument(
        "--aplicar",
        action="store_true",
        help="Efetua a gravação em lote na planilha. Sem isso, faz dry-run.",
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
    print("colunas=G:J")
    print(f"linhas_para_exportar={len(linhas)}")

    if not linhas:
        print("Informação insuficiente para verificar.")
        return 1

    if not args.aplicar:
        print("modo=dry-run (nenhuma escrita na planilha)")
        print(json.dumps(linhas[:3], ensure_ascii=False, indent=2))
        return 0

    try:
        ws = pl.abrir_worksheet(config["spreadsheet_id"], aba, args.credenciais)
        resposta = pl.exportar_lote_gj(
            ws,
            linhas,
            col_inicio=COL_INICIO,
            col_fim=COL_FIM,
            col_conferencia=COL_CONFERENCIA,
            respeitar_conferencia=True,
            ignorar_vazios=True,
        )
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001
        print(f"Falha ao gravar na planilha: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

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
