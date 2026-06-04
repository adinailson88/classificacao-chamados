#!/usr/bin/env python3
"""Reseta o experimento: apaga tudo que a IA gravou e volta ao ZERO.

Limpa na planilha principal as colunas G:K (Classificação IA, Avaliação,
Executor, Criticidade e a fórmula de conferência) e LIMPA o conteúdo das abas do
experimento (EXPERIMENTO_CONFIG, LOG_TURNOS_CLASSIFICACAO, LOG_LINHA_A_LINHA,
SNAPSHOT_ETAPA_1, LOG_TURNOS_RECLASSIFICACAO, VALIDACAO_HUMANA,
METRICAS_EXPERIMENTO, METRICAS_POR_CATEGORIA).

NÃO mexe na coluna C (categoria original/histórica), em L (fórmula do usuário) nem
em M (CONFERÊNCIA manual). Acesso via conta de serviço (gspread).

SEGURANÇA: só executa com --aplicar E --confirmar RESETAR. Sem isso, é dry-run.
Use sempre que quiser recomeçar a classificação/reclassificação do zero.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planilha as pl  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
PALAVRA_CONFIRMACAO = "RESETAR"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Reseta o experimento ao zero (G:K + abas).")
    p.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    p.add_argument("--credenciais", default=None)
    p.add_argument("--aplicar", action="store_true", help="Executa o reset. Sem isso, dry-run.")
    p.add_argument("--confirmar", default="", help=f"Digite {PALAVRA_CONFIRMACAO} para confirmar.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    with args.config.open(encoding="utf-8") as f:
        config = json.load(f)
    aba = config["aba_principal"]
    abas = list(config["abas_experimento"].values())

    print("planilha=<via SPREADSHEET_ID/local>")
    print(f"principal={aba} -> limpar G:K (preserva C, L, M)")
    print(f"abas a limpar: {', '.join(abas)}")

    if not args.aplicar:
        print("modo=dry-run (nada apagado). Para resetar: --aplicar --confirmar RESETAR")
        return 0

    if args.confirmar != PALAVRA_CONFIRMACAO:
        print(f"ABORTADO: confirmação inválida. Passe --confirmar {PALAVRA_CONFIRMACAO}.", file=sys.stderr)
        return 2

    try:
        sh = pl.abrir_planilha(pl.id_planilha(config), args.credenciais)
        ws = sh.worksheet(aba)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001
        print(f"Falha ao acessar a planilha: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    ws.batch_clear([f"G2:K{ws.row_count}"])
    print(f"limpo: {aba}!G2:K{ws.row_count}")

    for nome in abas:
        try:
            sh.worksheet(nome).clear()
            print(f"limpo: {nome}")
        except Exception as e:  # noqa: BLE001
            print(f"(pulado) {nome}: {type(e).__name__}")

    print("RESET concluído — experimento zerado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
