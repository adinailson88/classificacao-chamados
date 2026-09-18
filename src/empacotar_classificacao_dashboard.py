#!/usr/bin/env python3
"""Empacota os JSONs sanitizados de classificacao usados pelo dashboard.

Fase 1 da migracao para reduzir a dependencia das abas CLASSIF__<modelo>.
O pacote e derivado exclusivamente de ``docs/dados`` depois da exportacao normal,
nao acessa nem escreve Google Sheets e nao inclui ID ou texto de chamado.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any


RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
ORIGEM_PADRAO = RAIZ / "docs" / "dados"
DESTINO_PADRAO = RAIZ / "artefatos" / "dashboard" / "classificacao"
PADRAO_MODELO = re.compile(r"^[a-z0-9_]+$")


def _sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def _contagem(payload: Any) -> int | None:
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        modelos = payload.get("modelos")
        if isinstance(modelos, list):
            return len(modelos)
    return None


def arquivos_classificacao(config: dict[str, Any]) -> list[str]:
    mm = config.get("multimodelo", {}) or {}
    modelos = list(mm.get("modelos_leves", [])) + list(mm.get("modelos_pesados", []))
    nomes = []
    for modelo in modelos:
        modelo = str(modelo)
        if not PADRAO_MODELO.fullmatch(modelo):
            raise ValueError(f"modelo invalido em config_experimento.json: {modelo!r}")
        nomes.append(f"registros_{modelo}.json")
    return nomes


def empacotar(config_path: Path, origem: Path, destino: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    esperados = arquivos_classificacao(config)
    destino.mkdir(parents=True, exist_ok=True)

    entradas = []
    ausentes = []
    for nome in esperados:
        fonte = origem / nome
        if not fonte.is_file():
            ausentes.append(nome)
            continue
        payload = json.loads(fonte.read_text(encoding="utf-8"))
        alvo = destino / nome
        shutil.copyfile(fonte, alvo)
        if _sha256(fonte) != _sha256(alvo):
            raise RuntimeError(f"copia divergente: {nome}")
        entradas.append({
            "arquivo": nome,
            "sha256": _sha256(alvo),
            "bytes": alvo.stat().st_size,
            "registros": _contagem(payload),
        })

    manifesto = {
        "schema": 1,
        "escopo": "classificacao_dashboard_sanitizada",
        "origem": "docs/dados/registros_<modelo>.json",
        "contem_id_chamado": False,
        "contem_texto_chamado": False,
        "arquivos": entradas,
        "ausentes": ausentes,
    }
    (destino / "manifesto.json").write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifesto


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Empacota a classificacao sanitizada do dashboard.")
    p.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    p.add_argument("--origem", type=Path, default=ORIGEM_PADRAO)
    p.add_argument("--destino", type=Path, default=DESTINO_PADRAO)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    manifesto = empacotar(args.config, args.origem, args.destino)
    print(
        f"pacote_classificacao: arquivos={len(manifesto['arquivos'])} "
        f"ausentes={len(manifesto['ausentes'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
