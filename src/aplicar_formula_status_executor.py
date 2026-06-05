#!/usr/bin/env python3
"""Aplica a formula descritiva da coluna L (Classificado_Confianca_IA)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planilha as pl  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"


def formula_linha(linha: int) -> str:
    i = f"I{linha}"
    return (
        f'=SE({i}="";"";IFS('
        f'{i}="Supervisionado";"Classificado pelo modelo supervisionado local (TF-IDF + Random Forest, confiança ≥70%)";'
        f'{i}="LSTM";"Classificado pela IA LSTM com alta confiança (≥95%)";'
        f'{i}="RF_Fallback";"Classificado pela IA Random Forest fallback com alta confiança (≥95%)";'
        f'{i}="Baseline_TFIDF_LogReg";"Classificado pelo baseline TF-IDF + Regressão Logística";'
        f'{i}="Reclass_LSTM";"Reclassificado pela IA LSTM após rotina de revisão";'
        f'{i}="Reclass_RF";"Reclassificado pela IA Random Forest após rotina de revisão";'
        f'{i}="Reclass_Robusto";"Reclassificado pelo modelo robusto local após rotina de revisão";'
        f'{i}="NaoProcessado";"Falha geral – nenhum classificador funcionou, categoria humana mantida";'
        f'{i}="Desconhecido";"Origem indefinida (situação anômala)";'
        f'{i}="LLM_BAIXA_CONF";"Sugestão de LLM rejeitada (provedor não identificado)";'
        f'REGEXMATCH({i};"^Reclass_");"Reclassificado pela rotina de IA: "&REGEXREPLACE({i};"^Reclass_";"");'
        f'REGEXMATCH({i};"_BAIXA_CONF$");"Sugestão da IA "&REGEXREPLACE({i};"_BAIXA_CONF$";"")&" exige revisão (confiança <95%)";'
        f'REGEXMATCH({i};"^[A-Za-z0-9_]+$");"Classificado pela IA "&{i}&" com alta confiança (≥95%)";'
        f'VERDADEIRO;"Status não reconhecido: "&{i}))'
    )


def parse_args():
    p = argparse.ArgumentParser(description="Aplica formula da coluna L na aba principal.")
    p.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    p.add_argument("--credenciais", default=None)
    p.add_argument("--aplicar", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    with args.config.open(encoding="utf-8") as f:
        config = json.load(f)
    try:
        sh = pl.abrir_planilha(pl.id_planilha(config), args.credenciais)
        ws = sh.worksheet(config["aba_principal"])
    except Exception as e:  # noqa: BLE001
        print(f"Falha ao acessar a planilha: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    fim = ws.row_count
    formulas = [[formula_linha(r)] for r in range(2, fim + 1)]
    print(f"{config['aba_principal']}!L2:L{fim} formulas={len(formulas)}")
    if not args.aplicar:
        print("modo=dry-run")
        return 0
    ws.update(range_name=f"L2:L{fim}", values=formulas, value_input_option="USER_ENTERED")
    print("OK: formula da coluna L aplicada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
