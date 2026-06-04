#!/usr/bin/env python3
"""Gera dados/snapshot_etapa_1.json lendo a planilha 1x (conta de serviço).

Arquitetura GitHub-first: lê a aba principal UMA vez via Google Sheets API
(conta de serviço) e congela o estado em dados/snapshot_etapa_1.json no repo.
Esse arquivo é o INPUT das etapas seguintes; não escreve nada na planilha.
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planilha as pl  # noqa: E402


RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
SNAPSHOT_PADRAO = RAIZ / "dados" / "snapshot_etapa_1.json"
FUSO_BAHIA = timezone(timedelta(hours=-3))


def agora_bahia() -> str:
    return datetime.now(FUSO_BAHIA).strftime("%Y-%m-%dT%H:%M:%S-03:00")


def normalizar_cabecalho(valor: Any) -> str:
    texto = unicodedata.normalize("NFKC", str(valor or "").strip())
    return " ".join(texto.split()).casefold()


def linha_vazia(linha: list[Any]) -> bool:
    return all(str(celula or "").strip() == "" for celula in linha)


def obter(linha: list[Any], idx: int | None) -> str:
    if idx is None or idx >= len(linha):
        return ""
    return str(linha[idx] or "").strip()


def carregar_config(caminho: Path) -> dict[str, Any]:
    with caminho.open("r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def montar_texto(linha: list[Any], idx: dict[str, int]) -> str:
    campos = [
        obter(linha, idx.get(normalizar_cabecalho("TÍTULO"))),
        obter(linha, idx.get(normalizar_cabecalho("DESCRIÇÃO GLPI"))),
        obter(linha, idx.get(normalizar_cabecalho("TÍTULO O.S.M."))),
        obter(linha, idx.get(normalizar_cabecalho("DESCRIÇÃO O.S.M."))),
    ]
    return "\n".join(campo for campo in campos if campo)


def construir_snapshot(config: dict[str, Any], valores: list[list[Any]]) -> dict[str, Any]:
    cabecalho = valores[0] if valores else []
    idx = {normalizar_cabecalho(nome): pos for pos, nome in enumerate(cabecalho)}
    idx_id = idx.get(normalizar_cabecalho("ID Chamado"))
    idx_categoria = idx.get(normalizar_cabecalho("CATEGORIA COMPLETA"))
    idx_classificacao = idx.get(normalizar_cabecalho("Classificação IA"))
    idx_avaliacao = idx.get(normalizar_cabecalho("Avaliação (%)"))
    idx_conferencia = idx.get(normalizar_cabecalho("CONFERÊNCIA"))

    linhas: list[dict[str, Any]] = []
    for posicao, linha in enumerate(valores[1:], start=2):
        if linha_vazia(linha):
            continue
        linhas.append(
            {
                "linha_planilha": posicao,
                "valores": [str(c or "") for c in linha],
                "id_chamado": obter(linha, idx_id),
                "categoria_original": obter(linha, idx_categoria),
                "classificacao_ia": obter(linha, idx_classificacao),
                "avaliacao_atual": obter(linha, idx_avaliacao),
                "conferencia": obter(linha, idx_conferencia),
                "texto_classificacao": montar_texto(linha, idx),
            }
        )

    return {
        "run_id": config.get("run_id", ""),
        "gerado_em": agora_bahia(),
        "aba_origem": config["aba_principal"],
        "range_leitura": config["range_leitura"],
        "colunas": [str(c or "") for c in cabecalho],
        "total_linhas_lidas": len(valores),
        "total_nao_vazias": len(linhas),
        "linhas": linhas,
    }


def gravar_json(caminho: Path, dados: dict[str, Any]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=2)
        arquivo.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera dados/snapshot_etapa_1.json lendo a planilha 1x (conta de serviço)."
    )
    parser.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    parser.add_argument("--credenciais", default=None, help="Caminho da chave JSON da conta de serviço.")
    parser.add_argument("--snapshot-json", type=Path, default=SNAPSHOT_PADRAO)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = carregar_config(args.config)

    try:
        ws = pl.abrir_worksheet(config["spreadsheet_id"], config["aba_principal"], args.credenciais)
        valores = pl.ler_valores(ws, config["range_leitura"])
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001
        print(f"Falha ao acessar a planilha: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    snapshot = construir_snapshot(config, valores)
    gravar_json(args.snapshot_json, snapshot)

    print(f"origem={config['aba_principal']}")
    print(f"run_id={snapshot['run_id']}")
    print(f"linhas_lidas_observado={snapshot['total_linhas_lidas']}")
    print(f"linhas_nao_vazias_observado={snapshot['total_nao_vazias']}")
    print(f"snapshot_json={args.snapshot_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
