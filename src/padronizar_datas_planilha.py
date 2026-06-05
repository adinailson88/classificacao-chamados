#!/usr/bin/env python3
"""Converte timestamps ISO antigos da planilha para dd/mm/aaaa hh:mm.

O script procura apenas strings antigas no formato ISO com separador "T" e
converte para o padrao 05/06/2026 00:57. Sem --aplicar, roda em dry-run.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planilha as pl  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
ISO_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::\d{2})?(?:[+-]\d{2}:?\d{2}|Z)?$")


def converter(valor) -> str | None:
    m = ISO_RE.match(str(valor or "").strip())
    if not m:
        return None
    ano, mes, dia, hora, minuto = m.groups()
    return f"{dia}/{mes}/{ano} {hora}:{minuto}"


def col_letra(indice_1based: int) -> str:
    letras = ""
    n = indice_1based
    while n > 0:
        n, resto = divmod(n - 1, 26)
        letras = chr(65 + resto) + letras
    return letras


def parse_args():
    p = argparse.ArgumentParser(description="Padroniza timestamps ISO antigos nas abas da planilha.")
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
    except Exception as e:  # noqa: BLE001
        print(f"Falha ao acessar a planilha: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    total = 0
    for ws in sh.worksheets():
        vals = ws.get_values("A:Z", value_render_option="FORMATTED_VALUE")
        updates = []
        for i, row in enumerate(vals, start=1):
            for j, val in enumerate(row, start=1):
                novo = converter(val)
                if novo is None:
                    continue
                updates.append({"range": f"{col_letra(j)}{i}", "values": [[novo]]})
        if not updates:
            continue
        total += len(updates)
        print(f"{ws.title}: {len(updates)} celulas")
        if args.aplicar:
            ws.batch_update(updates, value_input_option="RAW")

    modo = "aplicado" if args.aplicar else "dry-run"
    print(f"OK: {total} celulas identificadas | modo={modo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
