#!/usr/bin/env python3
"""Renova apenas os JSONs sanitizados de modelos usados pelo dashboard."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planilha as pl  # noqa: E402
from exportar_dashboard import exportar_registros_modelos_da_planilha  # noqa: E402


RAIZ = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Exporta somente a classificacao do dashboard.")
    p.add_argument("--config", type=Path, default=RAIZ / "config_experimento.json")
    p.add_argument("--saida", type=Path, default=RAIZ / "docs" / "dados")
    p.add_argument("--credenciais", default=None)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    try:
        sh = pl.abrir_planilha(pl.id_planilha(config), args.credenciais)
        contagens, auditoria = exportar_registros_modelos_da_planilha(sh, config, args.saida)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001
        print(f"Falha ao exportar classificacao: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    completos = sum(1 for a in auditoria.values() if a.get("status") == "valido_completo")
    print(f"classificacao_dashboard: modelos={len(contagens)} completos={completos}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
