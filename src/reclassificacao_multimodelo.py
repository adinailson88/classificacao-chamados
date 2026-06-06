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
import time
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


def _append_resiliente(sh, nome, cab, linhas, colunas_percentuais=None, tentativas=5, espera=10):
    """append_aba com retry para erros transitorios (rede/quota da API do Sheets).

    Evita perder gravacao de estatistica por ConnectionError/RemoteDisconnected/429,
    que deixava a linha de turno (ou ate as linhas por chamado) sem registrar.
    """
    for t in range(1, tentativas + 1):
        try:
            return pl.append_aba(sh, nome, cab, linhas, colunas_percentuais=colunas_percentuais)
        except Exception as e:  # noqa: BLE001
            msg = str(e).lower()
            transitorio = any(k in msg for k in (
                "connection", "remotedisconnected", "aborted", "reset by peer",
                "429", "quota", "rate limit", "timed out", "timeout", "temporarily"))
            if t >= tentativas or not transitorio:
                raise
            print(f"[append {nome}] falha transitoria ({type(e).__name__}); "
                  f"retry {t}/{tentativas} em {espera * t}s", file=sys.stderr)
            time.sleep(espera * t)


def parse_conf(v) -> float:
    try:
        f = float(str(v).replace("%", "").replace(",", ".").strip())
        return f / 100.0 if f > 1 else f
    except (ValueError, TypeError):
        return 0.0


def _carregar_calibrador(modelo: str) -> dict:
    """Mapa do calibrador do modelo (y_grid em [0,1]) de calibracao_ajustada_modelos.json.
    Retorna {} se ausente — nesse caso a confianca calibrada cai para a bruta."""
    arq = RAIZ / "docs" / "dados" / "calibracao_ajustada_modelos.json"
    try:
        d = json.loads(arq.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    for m in d.get("modelos", []):
        if m.get("modelo") == modelo:
            return m.get("calibrador", {}) or {}
    return {}


def aplicar_calibrado(calibrador: dict, conf) -> float:
    """Aplica o mapa do calibrador (grade y_grid) a uma confianca bruta por interpolacao
    linear. Sem mapa, retorna a confianca original. (Espelha calibracao_confianca.)"""
    g = (calibrador or {}).get("y_grid")
    try:
        c = max(0.0, min(1.0, float(conf)))
    except (TypeError, ValueError):
        return 0.0
    if not g:
        return c
    pos = c * (len(g) - 1)
    i = int(pos)
    if i >= len(g) - 1:
        return float(g[-1])
    frac = pos - i
    return float(g[i] * (1 - frac) + g[i + 1] * frac)


def carregar_classif_baixa(sh, aba: str, limiar: float, calibrador: dict | None = None) -> dict[int, dict]:
    """linha -> {cat_1, conf_1, conf_sel} dos casos com confianca < limiar.

    conf_1 e sempre a confianca BRUTA (auditoria). Quando `calibrador` e fornecido,
    a SELECAO usa a confianca CALIBRADA (conf_sel = P(acerto|conf_bruta)); senao
    conf_sel = conf_1. Assim, modelos cuja saida bruta e enganosa (ex.: linear_svc)
    deixam de marcar como "baixa confianca" casos que, calibrados, sao confiaveis.
    """
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
        conf_sel = aplicar_calibrado(calibrador, conf) if calibrador else conf
        if conf_sel < limiar:
            baixa[ln] = {"cat_1": str(r[4]).strip(), "conf_1": conf, "conf_sel": conf_sel}
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

    calibrador = _carregar_calibrador(modelo) if getattr(args, "usar_calibrado", False) else None
    baixa = carregar_classif_baixa(sh, aba_classif, lim_alta, calibrador)
    feitas = linhas_ja_reclass(sh, aba_reclass)
    cand_linhas = [ln for ln in baixa if ln not in feitas and ln in por_linha]
    cand_linhas.sort(key=lambda ln: (baixa[ln].get("conf_sel", baixa[ln]["conf_1"]), ln))
    if calibrador:
        print(f"[{modelo}] selecao por confianca CALIBRADA ({calibrador.get('metodo','?')}).")
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
    _append_resiliente(sh, aba_reclass, cab, linhas, colunas_percentuais=[7, 10])

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
    _append_resiliente(sh, mm["aba_turnos"].replace("TURNOS", "RECLASS_TURNOS"), cab_t, turnos,
                       colunas_percentuais=[7, 8])

    # Grava a reclassificacao na coluna "Classificacao IA - 2" (O) da aba principal,
    # SEM tocar em G (classificacao original), M/N (conferencias). Assim a conferencia
    # da IA continua valida para G, e a reclassificacao fica num campo proprio.
    if getattr(args, "col2_ativa", False):
        try:
            ws_main = sh.worksheet(config["aba_principal"])
            col_o = pl.indice_coluna_por_cabecalho(ws_main, "Classificacao IA - 2", 15)
            mapa = {int(r["linha"]): r["cat_2"] for r in registros}
            for tentativa in range(1, 4):
                try:
                    pl.escrever_coluna_por_linha(ws_main, col_o, mapa)
                    break
                except Exception as e:  # noqa: BLE001
                    if tentativa >= 3:
                        raise
                    print(f"[{modelo}] coluna 2: falha transitoria ({type(e).__name__}); retry {tentativa}/3 em {10*tentativa}s",
                          file=sys.stderr)
                    time.sleep(10 * tentativa)
            print(f"[{modelo}] gravou {len(mapa)} reclassificacoes na coluna {col_o} (Classificacao IA - 2).")
        except Exception as e:  # noqa: BLE001
            print(f"[{modelo}] FALHA ao gravar coluna 2: {type(e).__name__}: {e}", file=sys.stderr)

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
    p.add_argument("--usar-calibrado", action="store_true",
                   help="Seleciona candidatos pela confianca CALIBRADA (calibracao_ajustada_modelos.json) "
                        "em vez da bruta. Reduz candidatos espurios em modelos mal calibrados.")
    p.add_argument("--gravar-coluna-2", action="store_true",
                   help="Grava a reclassificacao na coluna 'Classificacao IA - 2' (O) da aba principal, "
                        "sem tocar em G/M/N. Use com UM unico modelo no escopo (ex.: pesados=lstm). "
                        "So tem efeito junto com --aplicar.")
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

    # Gravacao na coluna "Classificacao IA - 2" (O) so faz sentido com 1 modelo no
    # escopo (a coluna e unica). Com varios, desativa para nao misturar modelos.
    args.col2_ativa = bool(args.gravar_coluna_2 and args.aplicar and len(modelos) == 1)
    if args.gravar_coluna_2 and not args.col2_ativa:
        print("[aviso] --gravar-coluna-2 ignorado: requer --aplicar e exatamente 1 modelo no escopo.",
              file=sys.stderr)

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
