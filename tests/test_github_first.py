#!/usr/bin/env python3
"""Testes leves da arquitetura GitHub-first (sem rede, sem planilha)."""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import classificar_etapa as ce  # noqa: E402
import exportar_etapa as ee  # noqa: E402
import registrar_snapshot_inicial as rs  # noqa: E402


def test_label_confianca():
    assert ce.label_confianca(0.99, 0.7, 0.95) == "alta"
    assert ce.label_confianca(0.80, 0.7, 0.95) == "media"
    assert ce.label_confianca(0.50, 0.7, 0.95) == "baixa"


def test_selecionar_elegiveis_ignora_sem_rotulo_ou_texto():
    linhas = [
        {"categoria_original": "A", "texto_classificacao": "texto"},
        {"categoria_original": "", "texto_classificacao": "texto"},
        {"categoria_original": "B", "texto_classificacao": "   "},
    ]
    assert len(ce.selecionar_elegiveis(linhas)) == 1


def test_montar_linhas_gera_GJ_com_criticidade_vazia():
    resultado = {
        "linhas": [
            {
                "linha_planilha": 5,
                "classificacao_ia": "Eletrica",
                "avaliacao": 0.873,
                "executor": "Baseline_TFIDF_LogReg",
                "criticidade": "",
            }
        ]
    }
    linhas = ee.montar_linhas(resultado)
    assert linhas == [
        {"linha": 5, "valores": ["Eletrica", 0.873, "Baseline_TFIDF_LogReg", ""]}
    ]


def test_construir_snapshot_ignora_linha_vazia_e_localiza_por_cabecalho():
    config = {
        "run_id": "T",
        "aba_principal": "X",
        "range_leitura": "A:M",
    }
    cabecalho = [
        "ID Chamado", "TÍTULO", "CATEGORIA COMPLETA", "DESCRIÇÃO GLPI",
        "TÍTULO O.S.M.", "DESCRIÇÃO O.S.M.", "Classificação IA",
        "Avaliação (%)", "Executor", "Criticidade Atribuída por IA",
        "Comparação", "Classificado_Confiança_IA", "CONFERÊNCIA",
    ]
    valores = [
        cabecalho,
        ["1", "Lampada", "Eletrica", "desc", "osm", "descosm", "", "", "", "", "", "", ""],
        ["", "", "", "", "", "", "", "", "", "", "", "", ""],
    ]
    snap = rs.construir_snapshot(config, valores)
    assert snap["total_nao_vazias"] == 1
    linha = snap["linhas"][0]
    assert linha["linha_planilha"] == 2
    assert linha["id_chamado"] == "1"
    assert linha["categoria_original"] == "Eletrica"
    assert "Lampada" in linha["texto_classificacao"]


def _run():
    falhas = 0
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok {nome}")
            except AssertionError as exc:
                falhas += 1
                print(f"FALHOU {nome}: {exc}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(_run())
