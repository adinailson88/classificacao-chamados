#!/usr/bin/env python3
"""Cria as abas vazias do fluxo multimodelo com cabecalhos."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planilha as pl  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"

CAB_CLASSIF = ["run_id", "linha_planilha", "id_chamado", "categoria_original", "categoria_ia",
               "confianca", "faixa", "executor", "acerto_historico", "etapa", "data"]
CAB_RECLASS = ["run_id", "modelo", "linha_planilha", "id_chamado", "categoria_original",
               "categoria_antes", "confianca_antes", "acerto_antes", "categoria_depois",
               "confianca_depois", "acerto_depois", "mudou", "delta_confianca", "resultado", "data"]
CAB_TURNOS = ["modelo", "run_id", "turno", "linha_inicial", "linha_final", "qtd", "qtd_acerto",
              "taxa_concordancia", "concordancia_acumulada", "confianca_media", "confianca_min",
              "confianca_max", "qtd_abaixo_70", "qtd_70_95", "qtd_acima_95", "data"]
CAB_METRICAS = ["modelo", "feitos_total", "pendentes_restantes", "concordancia_acumulada",
                "concordancia_ultimo_lote", "metodo_ultimo", "processados_ultimo", "atualizado_em"]
CAB_RECLASS_TURNOS = ["modelo", "run_id", "turno", "qtd", "corretos_antes", "corretos_depois",
                      "concordancia_antes", "concordancia_depois", "corrigidos", "prejudicados",
                      "ganho_liquido", "variacao_media_confianca", "data"]


def nome_aba(template: str, modelo: str) -> str:
    return template.replace("{modelo}", modelo)


def parse_args():
    p = argparse.ArgumentParser(description="Prepara abas multimodelo. Sem --aplicar, dry-run.")
    p.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    p.add_argument("--credenciais", default=None)
    p.add_argument("--aplicar", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    with args.config.open(encoding="utf-8") as f:
        config = json.load(f)
    mm = config.get("multimodelo", {})
    modelos = list(mm.get("modelos_leves", [])) + list(mm.get("modelos_pesados", []))
    if not modelos:
        print("multimodelo sem modelos configurados.")
        return 0

    abas = []
    for modelo in modelos:
        abas.append((nome_aba(mm["aba_classificacao"], modelo), CAB_CLASSIF, [6]))
        abas.append((nome_aba(mm["aba_reclassificacao"], modelo), CAB_RECLASS, [7, 10]))
    abas.extend([
        (mm["aba_turnos"], CAB_TURNOS, [8, 9, 10, 11, 12]),
        (mm["aba_metricas"], CAB_METRICAS, [4, 5]),
        (mm["aba_turnos"].replace("TURNOS", "RECLASS_TURNOS"), CAB_RECLASS_TURNOS, [7, 8]),
    ])

    sh = pl.abrir_planilha(pl.id_planilha(config), args.credenciais)
    existentes = {ws.title for ws in sh.worksheets()}
    faltando = [a for a in abas if a[0] not in existentes]
    for nome, cab, _ in faltando:
        print(f"criar: {nome} colunas={len(cab)}")
    if not faltando:
        print("OK: abas multimodelo ja existem.")
        return 0
    if not args.aplicar:
        print(f"modo=dry-run | faltando={len(faltando)}")
        return 0
    for nome, cab, perc in faltando:
        pl.escrever_aba(sh, nome, cab, [], colunas_percentuais=perc)
    print(f"OK: abas criadas={len(faltando)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
