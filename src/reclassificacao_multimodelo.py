#!/usr/bin/env python3
"""Reclassificacao COMPLETA por modelo — Etapa 2 generalizada para o zoo.

Para CADA modelo, reavalia os chamados de BAIXA confianca (conf < limiar de alta)
gravados em CLASSIF__<modelo>, de forma progressiva, comparando ANTES (etapa 1) com
DEPOIS (reclassificacao) e medindo o GANHO LIQUIDO (corrigidos - prejudicados).

A reclassificacao reusa o motor OUT-OF-FOLD (sem vazamento) e inclui a MEMORIA
VALIDADA no treino — por isso o ganho aparece a medida que a validacao humana
cresce (antes disso, o mesmo modelo tende a reproduzir a etapa 1: honesto, sem
"almoco gratis"). Registra em RECLASS__<modelo> (antes/depois/turnos). Nao muta a
aba CLASSIF (preserva o registro original da etapa 1).

Sem --aplicar = dry-run. Acesso via conta de servico (gspread).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planilha as pl  # noqa: E402
import memoria_validada as mv  # noqa: E402
import classificacao_multimodelo as clf  # noqa: E402
from tempo import agora_bahia  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
DADOS = RAIZ / "dados"


def parse_conf(v) -> float:
    try:
        f = float(str(v).replace("%", "").replace(",", ".").strip())
        return f / 100.0 if f > 1 else f
    except (ValueError, TypeError):
        return 0.0


def carregar_classif_baixa(sh, aba: str, limiar: float) -> dict[int, dict]:
    """linha -> {cat_1, conf_1} dos casos com confianca < limiar."""
    try:
        vals = sh.worksheet(aba).get_values("A:K", value_render_option="UNFORMATTED_VALUE")
    except Exception:  # noqa: BLE001
        return {}
    # CLASSIF cols: 1 linha,3 cat_original,4 cat_ia,5 confianca
    baixa = {}
    for r in vals[1:]:
        if len(r) < 6:
            continue
        try:
            ln = int(r[1])
        except (ValueError, TypeError):
            continue
        conf = parse_conf(r[5])
        if conf < limiar:
            baixa[ln] = {"cat_1": str(r[4]).strip(), "conf_1": conf}
    return baixa


def linhas_ja_reclass(sh, aba: str) -> set[int]:
    try:
        vals = sh.worksheet(aba).get_values("C:C", value_render_option="UNFORMATTED_VALUE")
    except Exception:  # noqa: BLE001
        return set()
    feitas = set()
    for r in vals[1:]:
        try:
            feitas.add(int(r[0]))
        except (IndexError, ValueError, TypeError):
            continue
    return feitas


def reclassificar_modelo(sh, config, modelo, elegiveis, por_linha, cap, base_extra, args) -> dict:
    mm = config["multimodelo"]
    run_id = config.get("run_id", "")
    gerado = agora_bahia()
    tam = int(mm.get("tamanho_turno", 15))
    lim_alta = float(config.get("classificacao", {}).get("limiar_alta_confianca", 0.95))
    aba_classif = clf.nome_aba(mm["aba_classificacao"], modelo)
    aba_reclass = clf.nome_aba(mm["aba_reclassificacao"], modelo)

    baixa = carregar_classif_baixa(sh, aba_classif, lim_alta)
    feitas = linhas_ja_reclass(sh, aba_reclass)
    cand_linhas = [ln for ln in baixa if ln not in feitas and ln in por_linha]
    cand_linhas.sort(key=lambda ln: (baixa[ln]["conf_1"], ln))
    if not cand_linhas:
        print(f"[{modelo}] 0 candidatos a reclassificar.")
        return {"modelo": modelo, "reclassificados": 0, "ganho_liquido": 0}

    n_lote = len(cand_linhas) if cap <= 0 else min(len(cand_linhas), cap)
    sel = cand_linhas[:n_lote]
    lote = [por_linha[ln] for ln in sel]

    # Base sempre-no-treino: TODAS as linhas elegiveis menos o lote + memoria.
    sel_set = set(sel)
    base_textos = [e["texto"] for e in elegiveis if e["linha"] not in sel_set] + list(base_extra[0])
    base_cats = [e["categoria_original"] for e in elegiveis if e["linha"] not in sel_set] + list(base_extra[1])

    print(f"[{modelo}] candidatos_baixa={len(cand_linhas)} | lote_agora={len(lote)} | base={len(base_textos)}")
    preds, scores, metodo = clf.prever_out_of_fold(
        modelo, lote, base_textos, base_cats,
        k_folds=int(mm.get("k_folds", 5)), min_base=int(mm.get("min_base_treino", 200)),
        fracao_topup=float(mm.get("fracao_topup", 0.25)))

    registros = []
    for e, p, s in zip(lote, preds, scores):
        if p is None:
            continue
        orig = e["categoria_original"]
        cat_1 = baixa[e["linha"]]["cat_1"]
        conf_1 = baixa[e["linha"]]["conf_1"]
        cat_2, conf_2 = str(p), round(float(s), 4)
        antes_ok = (cat_1 == orig)
        depois_ok = (cat_2 == orig)
        if not antes_ok and depois_ok:
            res = "corrigido"
        elif antes_ok and not depois_ok:
            res = "prejudicado"
        elif antes_ok and depois_ok:
            res = "mantido_correto"
        else:
            res = "mantido_errado"
        registros.append({"linha": e["linha"], "id": e["id"], "original": orig,
                          "cat_1": cat_1, "conf_1": conf_1, "antes_ok": antes_ok,
                          "cat_2": cat_2, "conf_2": conf_2, "depois_ok": depois_ok,
                          "mudou": cat_2 != cat_1, "delta": round(conf_2 - conf_1, 4), "res": res})

    if not registros:
        print(f"[{modelo}] nada reclassificado (base insuficiente).")
        return {"modelo": modelo, "reclassificados": 0, "ganho_liquido": 0}

    corr = sum(1 for r in registros if r["res"] == "corrigido")
    prej = sum(1 for r in registros if r["res"] == "prejudicado")
    ganho = corr - prej
    print(f"[{modelo}] reclass={len(registros)} | corrigidos={corr} | prejudicados={prej} | "
          f"GANHO={ganho} | metodo={metodo}")

    if not args.aplicar:
        return {"modelo": modelo, "reclassificados": len(registros), "ganho_liquido": ganho,
                "corrigidos": corr, "prejudicados": prej, "dry_run": True}

    cab = ["run_id", "modelo", "linha_planilha", "id_chamado", "categoria_original",
           "categoria_antes", "confianca_antes", "acerto_antes", "categoria_depois",
           "confianca_depois", "acerto_depois", "mudou", "delta_confianca", "resultado", "data"]
    linhas = [[run_id, modelo, r["linha"], r["id"], r["original"], r["cat_1"], r["conf_1"],
               str(r["antes_ok"]), r["cat_2"], r["conf_2"], str(r["depois_ok"]), str(r["mudou"]),
               r["delta"], r["res"], gerado] for r in registros]
    pl.append_aba(sh, aba_reclass, cab, linhas, colunas_percentuais=[7, 10])

    # Turnos de 15 no log consolidado.
    turnos = []
    for k, ini in enumerate(range(0, len(registros), tam)):
        b = registros[ini:ini + tam]
        n = len(b)
        ca = sum(1 for r in b if r["antes_ok"]); cd = sum(1 for r in b if r["depois_ok"])
        c2 = sum(1 for r in b if r["res"] == "corrigido"); p2 = sum(1 for r in b if r["res"] == "prejudicado")
        turnos.append([modelo, run_id, k + 1, n, ca, cd, round(ca / n, 4), round(cd / n, 4),
                       c2, p2, c2 - p2, round(float(np.mean([r["delta"] for r in b])), 4), gerado])
    cab_t = ["modelo", "run_id", "turno", "qtd", "corretos_antes", "corretos_depois",
             "concordancia_antes", "concordancia_depois", "corrigidos", "prejudicados",
             "ganho_liquido", "variacao_media_confianca", "data"]
    pl.append_aba(sh, mm["aba_turnos"].replace("TURNOS", "RECLASS_TURNOS"), cab_t, turnos,
                  colunas_percentuais=[7, 8])

    return {"modelo": modelo, "reclassificados": len(registros), "ganho_liquido": ganho,
            "corrigidos": corr, "prejudicados": prej, "metodo": metodo}


def parse_args():
    p = argparse.ArgumentParser(description="Reclassificacao completa por modelo (Etapa 2).")
    p.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    p.add_argument("--credenciais", default=None)
    p.add_argument("--modelos", default="leves",
                   help="'leves' (6), 'todos' (7), 'pesados' (lstm) ou lista.")
    p.add_argument("--max-turnos", type=int, default=0, help="Cap de turnos de 15 por execucao (0=todos).")
    p.add_argument("--aplicar", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    config = clf.carregar_config(args.config)
    if not config.get("multimodelo", {}).get("habilitado", False):
        print("multimodelo desabilitado no config."); return 0
    mm = config["multimodelo"]
    tam = int(mm.get("tamanho_turno", 15))
    cap = 0 if args.max_turnos <= 0 else args.max_turnos * tam
    modelos = clf.resolver_modelos(config, args.modelos)
    gerado = agora_bahia()

    try:
        sh = pl.abrir_planilha(pl.id_planilha(config), args.credenciais)
        ws = sh.worksheet(config["aba_principal"])
        elegiveis = clf.carregar_elegiveis(ws, config)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr); return 2
    except Exception as e:  # noqa: BLE001
        print(f"Falha ao acessar a planilha: {type(e).__name__}: {e}", file=sys.stderr); return 1

    por_linha = {e["linha"]: e for e in elegiveis}
    memoria_cfg = config.get("memoria_validada", {})
    memoria = mv.carregar_memoria_validada(sh, config["abas_experimento"]["validacao_humana"]) \
        if memoria_cfg.get("habilitada", True) else []
    mem_textos, mem_cats = mv.expandir_treino_com_memoria([], [], memoria, peso=int(memoria_cfg.get("peso_treino", 3)))
    print(f"modelos={modelos} | elegiveis={len(elegiveis)} | memoria_validada={len(memoria)}")

    resumos = []
    for modelo in modelos:
        try:
            r = reclassificar_modelo(sh, config, modelo, elegiveis, por_linha, cap, (mem_textos, mem_cats), args)
        except Exception as e:  # noqa: BLE001
            print(f"[{modelo}] FALHOU: {type(e).__name__}: {e}", file=sys.stderr)
            continue
        resumos.append(r)

    DADOS.mkdir(parents=True, exist_ok=True)
    (DADOS / "reclass_multimodelo_ultimo.json").write_text(
        json.dumps({"gerado_em": gerado, "modelos": resumos}, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(r.get("reclassificados", 0) for r in resumos)
    print(f"OK: reclassificados={total} | modelos={len(resumos)}{' (dry-run)' if not args.aplicar else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
