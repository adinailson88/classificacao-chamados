#!/usr/bin/env python3
"""Registra o snapshot inicial da base nao vazia (arquitetura GitHub-first).

Le a aba principal UMA vez via Apps Script (action=ler) e grava o estado em
dados/snapshot_etapa_1.json no repositorio. Esse arquivo e o INPUT congelado das
etapas seguintes (classificacao), evitando reler a planilha a cada passo.

Opcionalmente, com --aplicar, tambem grava a aba SNAPSHOT_ETAPA_1 na planilha
(comportamento legado, 1 doPost).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
SNAPSHOT_PADRAO = RAIZ / "dados" / "snapshot_etapa_1.json"
FUSO_BAHIA = timezone(timedelta(hours=-3))


def agora_bahia() -> str:
    return datetime.now(FUSO_BAHIA).strftime("%Y-%m-%dT%H:%M:%S-03:00")


def normalizar_cabecalho(valor: Any) -> str:
    texto = str(valor or "").strip()
    texto = unicodedata.normalize("NFKC", texto)
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


def chamar_get(url_base: str, token: str, params: dict[str, str]) -> dict[str, Any]:
    query = dict(params)
    query["token"] = token
    url = url_base.rstrip() + "?" + urlencode(query)
    with urlopen(url, timeout=180) as resposta:
        return json.loads(resposta.read().decode("utf-8"))


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
        description="Gera dados/snapshot_etapa_1.json lendo a planilha uma vez. "
        "Com --aplicar tambem grava a aba SNAPSHOT_ETAPA_1 (legado)."
    )
    parser.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    parser.add_argument("--apps-script-url", default=os.getenv("APPS_SCRIPT_URL"))
    parser.add_argument("--token", default=os.getenv("APPS_SCRIPT_TOKEN"))
    parser.add_argument("--snapshot-json", type=Path, default=SNAPSHOT_PADRAO)
    parser.add_argument(
        "--aplicar",
        action="store_true",
        help="Alem do JSON no repo, grava a aba SNAPSHOT_ETAPA_1 na planilha.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.apps_script_url or not args.token:
        print(
            "Informe --apps-script-url e --token, ou defina APPS_SCRIPT_URL/APPS_SCRIPT_TOKEN.",
            file=sys.stderr,
        )
        return 2

    config = carregar_config(args.config)

    validacao = chamar_get(
        args.apps_script_url,
        args.token,
        {
            "action": "validar",
            "sheet": config["aba_principal"],
            "range": config["range_leitura"],
        },
    )
    if not validacao.get("ok"):
        print(json.dumps(validacao, ensure_ascii=False), file=sys.stderr)
        return 1

    leitura = chamar_get(
        args.apps_script_url,
        args.token,
        {
            "action": "ler",
            "sheet": config["aba_principal"],
            "range": config["range_leitura"],
        },
    )
    if not leitura.get("ok"):
        print(json.dumps(leitura, ensure_ascii=False), file=sys.stderr)
        return 1

    valores = leitura.get("values") or []
    snapshot = construir_snapshot(config, valores)
    gravar_json(args.snapshot_json, snapshot)

    print(f"origem={config['aba_principal']}")
    print(f"run_id={snapshot['run_id']}")
    print(f"linhas_lidas_observado={snapshot['total_linhas_lidas']}")
    print(f"linhas_nao_vazias_observado={snapshot['total_nao_vazias']}")
    print(f"snapshot_json={args.snapshot_json}")

    if not args.aplicar:
        print("modo=github-first (sem escrita na planilha)")
        return 0

    destino = config["abas_experimento"]["snapshot_etapa_1"]
    resultado = chamar_post(
        args.apps_script_url,
        args.token,
        {
            "action": "registrar_snapshot_inicial",
            "origem": config["aba_principal"],
            "destino": destino,
            "run_id": config["run_id"],
        },
    )
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0 if resultado.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
