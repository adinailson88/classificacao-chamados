#!/usr/bin/env python3
"""Materializa um cache local da planilha para reduzir leituras repetidas.

O cache completo pode conter texto livre de chamados. Por isso ele e gravado em
`dados/` (gitignored) para uso efemero no workflow. Apenas o manifesto sanitizado
em `docs/dados/cache_planilha_manifest.json` pode ser commitado.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planilha as pl  # noqa: E402
from tempo import agora_bahia  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
SAIDA_PADRAO = RAIZ / "dados" / "cache_planilha.json"
MANIFEST_PADRAO = RAIZ / "docs" / "dados" / "cache_planilha_manifest.json"


def _max_cols(valores: list[list[Any]]) -> int:
    return max((len(r) for r in valores), default=0)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Atualiza cache local read-only da planilha.")
    p.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    p.add_argument("--credenciais", default=None)
    p.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    p.add_argument("--manifest", type=Path, default=MANIFEST_PADRAO)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    with args.config.open("r", encoding="utf-8") as f:
        config = json.load(f)

    # Garante que esta rotina sempre leia a origem real, mesmo quando chamada em
    # uma etapa que depois exportara PLANILHA_CACHE_JSON para os scripts.
    os.environ.pop(pl.CACHE_ENV, None)

    try:
        sh = pl.abrir_planilha(pl.id_planilha(config), args.credenciais)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001
        print(f"Falha ao acessar planilha: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    gerado = agora_bahia()
    worksheets: dict[str, dict[str, Any]] = {}
    manifest_abas: dict[str, dict[str, Any]] = {}

    for ws in sh.worksheets():
        nome = str(ws.title)
        valores = pl.ler_valores(ws, "A:Z")
        worksheets[nome] = {"values": valores}
        manifest_abas[nome] = {"linhas": len(valores), "colunas_max": _max_cols(valores)}
        print(f"cache {nome}: linhas={len(valores)} colunas_max={_max_cols(valores)}")

    payload = {
        "gerado_em": gerado,
        "origem": "google_sheets",
        "observacao": "Cache operacional efemero; pode conter texto livre; nao versionar.",
        "worksheets": worksheets,
    }
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    manifest = {
        "gerado_em": gerado,
        "cache_version": 1,
        "natureza": "manifesto_sanitizado_do_cache_operacional",
        "arquivo_cache_gitignored": str(args.saida.resolve().relative_to(RAIZ)),
        "abas": manifest_abas,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: cache={args.saida} | manifest={args.manifest} | abas={len(worksheets)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
