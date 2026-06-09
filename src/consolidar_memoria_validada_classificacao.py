#!/usr/bin/env python3
"""Consolida memória validada, métricas e calibração da Classificação IA - 2.

Lê a aba principal, usando:
- C = categoria histórica;
- G/H = Classificação IA original e confiança;
- M = CONFERÊNCIA GLPI;
- N = CONFERÊNCIA IA;
- O = Classificação IA - 2;
- P = CONFERÊNCIA IA - 2.

Produz abas privadas:
- MEMORIA_VALIDADA_CLASSIFICACAO
- METRICAS_CLASSIFICACAO_2
- CALIBRACAO_VALIDADA

Sem --aplicar = dry-run.
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planilha as pl  # noqa: E402
from tempo import agora_bahia  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"

ABA_MEMORIA = "MEMORIA_VALIDADA_CLASSIFICACAO"
ABA_METRICAS = "METRICAS_CLASSIFICACAO_2"
ABA_CALIBRACAO = "CALIBRACAO_VALIDADA"
ABA_CONTROLE = "CONTROLE_CLASSIFICACAO_2"


def norm(s: Any) -> str:
    t = unicodedata.normalize("NFKD", str(s or ""))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return " ".join(t.split()).casefold()


def cel(linha: list[Any], idx: int | None) -> str:
    return str(linha[idx] or "").strip() if idx is not None and idx < len(linha) else ""


def parse_float(v: Any, default: float = 0.0) -> float:
    try:
        f = float(str(v).replace("%", "").replace(",", ".").strip())
        return f / 100.0 if f > 1 else f
    except (ValueError, TypeError):
        return default


def carregar_config(caminho: Path) -> dict[str, Any]:
    with caminho.open("r", encoding="utf-8") as f:
        return json.load(f)


def veredito(v: str) -> str | None:
    s = str(v or "").strip()
    if not s:
        return None
    return "Correto" if s.casefold() == "correto" else "Errado"


def metricas_binarias(registros: list[dict[str, Any]], campo_pred: str) -> dict[str, Any]:
    aval = [r for r in registros if r.get("verdade") and r.get(campo_pred)]
    if not aval:
        return {"n": 0, "acuracia": None}
    acertos = sum(1 for r in aval if r[campo_pred] == r["verdade"])
    return {"n": len(aval), "acertos": acertos, "acuracia": round(acertos / len(aval), 4)}


def main() -> int:
    p = argparse.ArgumentParser(description="Consolida memória e métricas validadas da Classificação IA - 2.")
    p.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    p.add_argument("--credenciais", default=None)
    p.add_argument("--aplicar", action="store_true")
    args = p.parse_args()

    config = carregar_config(args.config)
    gerado = agora_bahia()

    try:
        sh = pl.abrir_planilha(pl.id_planilha(config), args.credenciais)
        ws = sh.worksheet(config["aba_principal"])
        valores = pl.ler_valores(ws, "A:P")
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001
        print(f"Falha ao acessar planilha: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    cab = valores[0] if valores else []
    idx = {norm(n): i for i, n in enumerate(cab)}
    campos_texto = ["TITULO", "DESCRICAO GLPI", "TITULO O.S.M.", "DESCRICAO O.S.M."]

    registros = []
    memoria = []
    for pos, linha in enumerate(valores[1:], start=2):
        cat_c = cel(linha, idx.get(norm("CATEGORIA COMPLETA")))
        cat_g = cel(linha, idx.get(norm("Classificacao IA")))
        conf_g = parse_float(cel(linha, idx.get(norm("Avaliacao (%)"))))
        cat_o = cel(linha, idx.get(norm("Classificacao IA - 2")))
        m = veredito(cel(linha, idx.get(norm("CONFERENCIA GLPI"))))
        n = veredito(cel(linha, idx.get(norm("CONFERENCIA IA"))))
        p2 = veredito(cel(linha, idx.get(norm("CONFERENCIA IA - 2"))))
        id_chamado = cel(linha, idx.get(norm("ID Chamado")))
        partes = [cel(linha, idx.get(norm(c))) for c in campos_texto]
        texto_curto = " | ".join(p for p in partes if p)[:500]

        verdade = ""
        origem = ""
        if p2 == "Correto" and cat_o:
            verdade = cat_o
            origem = "P:reclassificacao_correta"
        elif n == "Correto" and cat_g:
            verdade = cat_g
            origem = "N:ia_original_correta"
        elif m == "Correto" and cat_c:
            verdade = cat_c
            origem = "M:historico_correto"

        if verdade:
            peso = 10 if p2 == "Correto" else 8 if (m and n and m != n) else 5
            memoria.append([pos, id_chamado, texto_curto, verdade, origem, peso, "SIM", "", gerado])

        registros.append({
            "linha": pos,
            "id": id_chamado,
            "c": cat_c,
            "g": cat_g,
            "conf_g": conf_g,
            "o": cat_o,
            "m": m,
            "n": n,
            "p": p2,
            "verdade": verdade,
            "origem": origem,
        })

    m_g = metricas_binarias(registros, "g")
    m_o = metricas_binarias(registros, "o")
    linhas_metricas = [
        ["ia_original_G", m_g["n"], m_g.get("acertos", 0), m_g["acuracia"], gerado],
        ["classificacao_ia_2_O", m_o["n"], m_o.get("acertos", 0), m_o["acuracia"], gerado],
    ]

    faixas = {
        "<70": lambda x: x < 0.70,
        "70-95": lambda x: 0.70 <= x < 0.95,
        ">=95": lambda x: x >= 0.95,
    }
    linhas_cal = []
    for nome, pred in faixas.items():
        aval = [r for r in registros if r["verdade"] and r["g"] and pred(r["conf_g"])]
        ac = sum(1 for r in aval if r["g"] == r["verdade"])
        taxa = round(ac / len(aval), 4) if aval else ""
        linhas_cal.append([nome, len(aval), ac, taxa, "IA original G vs verdade derivada M/N/P", gerado])

    por_origem = Counter(r["origem"] for r in registros if r["origem"])
    print(json.dumps({
        "gerado_em": gerado,
        "memoria_validada": len(memoria),
        "metricas": {"G": m_g, "O": m_o},
        "origens": dict(por_origem),
        "modo": "aplicar" if args.aplicar else "dry-run",
    }, ensure_ascii=False, indent=2))

    if not args.aplicar:
        print("modo=dry-run (nada gravado na planilha).")
        return 0

    pl.escrever_aba(sh, ABA_MEMORIA, [
        "linha", "id_chamado", "texto_resumido_opcional", "categoria_validada",
        "origem_validacao", "peso_treino", "usar_para_treino", "observacao_tecnica", "data_execucao",
    ], memoria)
    pl.escrever_aba(sh, ABA_METRICAS, [
        "modelo", "qtd_validados", "qtd_acertos", "acuracia_validada", "data_execucao",
    ], linhas_metricas, colunas_percentuais=[4])
    pl.escrever_aba(sh, ABA_CALIBRACAO, [
        "faixa_confianca", "qtd_casos", "acertos", "taxa_acerto_real",
        "base_calibracao", "data_execucao",
    ], linhas_cal, colunas_percentuais=[4])
    pl.append_aba(
        sh,
        ABA_CONTROLE,
        ["data_execucao", "etapa", "status", "qtd_candidatos", "qtd_processados", "modelo_usado", "aplicou_na_coluna_O", "observacao_tecnica"],
        [[gerado, "5-memoria-metricas-calibracao", "OK", len(registros), len(memoria), "M/N/P", "NAO", json.dumps(dict(por_origem), ensure_ascii=False)]],
    )
    print("OK: memória, métricas e calibração gravadas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
