#!/usr/bin/env python3
"""Acesso à planilha experimental via conta de serviço (gspread).

Substitui a ponte por Apps Script Web App: em vez de URL + token (que exigia
reimplantar a cada rotação), a planilha é compartilhada com o e-mail da conta
de serviço e os scripts a abrem direto pela Google Sheets API.

A chave JSON da conta de serviço NUNCA é versionada (ver .gitignore). O caminho
padrão é credenciais_sa.json na raiz do repositório; pode ser sobrescrito por
--credenciais ou pela variável de ambiente GOOGLE_APPLICATION_CREDENTIALS.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import gspread


RAIZ = Path(__file__).resolve().parents[1]
CREDENCIAIS_PADRAO = RAIZ / "credenciais_sa.json"


def resolver_credenciais(caminho: str | Path | None = None) -> Path:
    if caminho:
        return Path(caminho)
    env = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("GCP_SA_KEY_FILE")
    if env:
        return Path(env)
    return CREDENCIAIS_PADRAO


def abrir_worksheet(spreadsheet_id: str, aba: str, credenciais: str | Path | None = None):
    """Abre a aba da planilha usando a conta de serviço."""
    cred = resolver_credenciais(credenciais)
    if not cred.exists():
        raise FileNotFoundError(
            f"Credenciais da conta de serviço não encontradas em {cred}. "
            "Salve a chave JSON como credenciais_sa.json na raiz do repo, ou "
            "defina GOOGLE_APPLICATION_CREDENTIALS."
        )
    # utf-8-sig tolera BOM (que pode ser inserido ao gravar a chave a partir de secret).
    with cred.open("r", encoding="utf-8-sig") as arquivo:
        info = json.load(arquivo)
    gc = gspread.service_account_from_dict(info)
    planilha = gc.open_by_key(spreadsheet_id)
    return planilha.worksheet(aba)


def ler_valores(ws, range_a1: str = "A:M") -> list[list[Any]]:
    """Lê os valores do intervalo (1 chamada de API)."""
    return ws.get_values(range_a1)


def _coluna_letra(indice_1based: int) -> str:
    """Converte índice de coluna (1=A) para letra(s) A1."""
    letras = ""
    n = indice_1based
    while n > 0:
        n, resto = divmod(n - 1, 26)
        letras = chr(65 + resto) + letras
    return letras


def _normalizar(bloco: list[list[Any]], n_linhas: int, n_cols: int) -> list[list[Any]]:
    """Garante matriz n_linhas x n_cols preenchendo com '' (get_values corta vazios)."""
    saida = []
    for i in range(n_linhas):
        linha = list(bloco[i]) if i < len(bloco) else []
        linha = linha[:n_cols] + [""] * (n_cols - len(linha))
        saida.append(linha)
    return saida


def exportar_lote_gj(
    ws,
    linhas: list[dict[str, Any]],
    col_inicio: int = 7,   # G
    col_fim: int = 10,     # J
    col_conferencia: int = 13,  # M
    respeitar_conferencia: bool = True,
    ignorar_vazios: bool = True,
) -> dict[str, Any]:
    """Grava G:J em UMA escrita em lote (read-modify-write em bloco).

    - Pula linhas com CONFERÊNCIA (col M) verdadeira.
    - Não sobrescreve célula com valor vazio (preserva o que já está na planilha).
    Faz 2 leituras (bloco G:J + coluna M, em 1 batch_get) e 1 escrita.
    """
    alvos = {
        int(item["linha"]): (item.get("valores") or [])
        for item in linhas
        if int(item.get("linha", 0)) >= 2
    }
    if not alvos:
        return {"ok": False, "erro": "linhas_sem_numero_valido"}

    min_l, max_l = min(alvos), max(alvos)
    n_linhas = max_l - min_l + 1
    n_cols = col_fim - col_inicio + 1

    rng_bloco = f"{_coluna_letra(col_inicio)}{min_l}:{_coluna_letra(col_fim)}{max_l}"
    rng_conf = f"{_coluna_letra(col_conferencia)}{min_l}:{_coluna_letra(col_conferencia)}{max_l}"

    bloco_raw, conf_raw = ws.batch_get([rng_bloco, rng_conf])
    bloco = _normalizar(bloco_raw, n_linhas, n_cols)
    conf = _normalizar(conf_raw, n_linhas, 1)

    def eh_verdadeiro(valor: Any) -> bool:
        return str(valor or "").strip().upper() in {"TRUE", "VERDADEIRO", "SIM"}

    gravadas = 0
    puladas_conf = 0
    for linha_num, valores in alvos.items():
        off = linha_num - min_l
        if respeitar_conferencia and eh_verdadeiro(conf[off][0]):
            puladas_conf += 1
            continue
        for c in range(n_cols):
            novo = valores[c] if c < len(valores) else ""
            if ignorar_vazios and (novo == "" or novo is None):
                continue
            bloco[off][c] = novo
        gravadas += 1

    ws.update(range_name=rng_bloco, values=bloco, value_input_option="RAW")

    # Coluna H (Avaliação) = 2ª coluna do bloco (G+1): formatar como porcentagem.
    col_pct = col_inicio + 1
    rng_pct = f"{_coluna_letra(col_pct)}{min_l}:{_coluna_letra(col_pct)}{max_l}"
    try:
        ws.format(rng_pct, {"numberFormat": {"type": "PERCENT", "pattern": "0.00%"}})
    except Exception:  # noqa: BLE001
        pass  # formatação é cosmética; não falhar a exportação por causa dela

    return {
        "ok": True,
        "intervalo_linhas": [min_l, max_l],
        "range": rng_bloco,
        "range_percentual": rng_pct,
        "linhas_recebidas": len(alvos),
        "linhas_gravadas": gravadas,
        "linhas_puladas_conferencia": puladas_conf,
    }
