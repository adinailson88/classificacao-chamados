#!/usr/bin/env python3
"""Comparação de múltiplos modelos locais sobre o MESMO lote de registros.

Cada modelo é treinado na base rotulada (excluindo o lote de teste) e avaliado no
MESMO lote [inicio, inicio+limite), na MESMA ordem — comparação justa. Gera:
- COMPARACAO_MODELOS: métricas consolidadas por (modelo, lote);
- COMPARACAO_CATEGORIA: precision/recall/F1/suporte por categoria;
- COMPARACAO_PREVISOES: previsão por registro + campos p/ validação humana posterior.

NÃO altera o fluxo de classificação (etapa1/etapa2). Sem --aplicar = dry-run.
Controle por lote: --modelo, --inicio, --limite, --executar-todos.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, f1_score,
                             precision_recall_fscore_support)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planilha as pl  # noqa: E402
import modelos_zoo as zoo  # noqa: E402
from tempo import agora_bahia  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
QUEM_CORRETO = ["NAO_AVALIADO", "IA", "ORIGINAL", "NENHUM", "DUVIDOSO"]


def cel(linha, idx) -> str:
    return str(linha[idx] or "").strip() if (idx is not None and idx < len(linha)) else ""


def carregar_elegiveis(ws, config):
    valores = pl.ler_valores(ws, config["range_leitura"])
    cab = valores[0] if valores else []
    norm = lambda s: " ".join(str(s or "").split()).casefold()  # noqa: E731
    idx = {norm(n): i for i, n in enumerate(cab)}
    i_id, i_tit, i_cat = idx.get(norm("ID Chamado")), idx.get(norm("TÍTULO")), idx.get(norm("CATEGORIA COMPLETA"))
    i_dg, i_to, i_do = idx.get(norm("DESCRIÇÃO GLPI")), idx.get(norm("TÍTULO O.S.M.")), idx.get(norm("DESCRIÇÃO O.S.M."))
    elig = []
    for pos, linha in enumerate(valores[1:], start=2):
        cat = cel(linha, i_cat)
        texto = "\n".join(c for c in [cel(linha, i_tit), cel(linha, i_dg),
                                      cel(linha, i_to), cel(linha, i_do)] if c)
        if cat and texto:
            elig.append({"linha": pos, "id": cel(linha, i_id), "titulo": cel(linha, i_tit),
                         "categoria_original": cat, "texto": texto})
    return elig


def avaliar_modelo(nome, treino, teste, limiar):
    textos_tr = [e["texto"] for e in treino]
    cats_tr = [e["categoria_original"] for e in treino]
    textos_te = [e["texto"] for e in teste]
    y_true = [e["categoria_original"] for e in teste]

    m = zoo.criar_modelo(nome)
    t0 = time.perf_counter()
    m.fit(textos_tr, cats_tr)
    t_treino = time.perf_counter() - t0
    t1 = time.perf_counter()
    preds, scores = m.predict_score(textos_te)
    t_infer = time.perf_counter() - t1
    y_pred = [str(p) for p in preds]
    scores = [float(s) for s in scores]

    revisao = [s < limiar for s in scores]
    idx_rev = [i for i, r in enumerate(revisao) if r]
    acerto_baixa = (sum(int(y_pred[i] == y_true[i]) for i in idx_rev) / len(idx_rev)) if idx_rev else None

    metricas = {
        "modelo": nome, "n": len(teste),
        "acuracia": round(float(accuracy_score(y_true, y_pred)), 4),
        "f1_macro": round(float(f1_score(y_true, y_pred, average="macro", zero_division=0)), 4),
        "f1_weighted": round(float(f1_score(y_true, y_pred, average="weighted", zero_division=0)), 4),
        "balanced_accuracy": round(float(balanced_accuracy_score(y_true, y_pred)), 4),
        "n_revisao": len(idx_rev),
        "acerto_baixa_conf": round(acerto_baixa, 4) if acerto_baixa is not None else None,
        "tempo_treino_s": round(t_treino, 2), "tempo_inferencia_s": round(t_infer, 2),
    }

    labels = sorted(set(y_true) | set(y_pred))
    pr, rc, f1, sup = precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=0)
    por_cat = [{"categoria": labels[i], "precision": round(float(pr[i]), 4),
                "recall": round(float(rc[i]), 4), "f1": round(float(f1[i]), 4),
                "suporte": int(sup[i])} for i in range(len(labels)) if sup[i] > 0]

    previsoes = []
    for e, yp, sc, rev in zip(teste, y_pred, scores, revisao):
        previsoes.append({"linha": e["linha"], "id": e["id"], "titulo": e["titulo"][:200],
                          "original": e["categoria_original"], "prevista": yp,
                          "score": round(sc, 4), "divergencia": yp != e["categoria_original"],
                          "revisao": rev})
    return metricas, por_cat, previsoes


def parse_args():
    p = argparse.ArgumentParser(description="Compara modelos locais no mesmo lote.")
    p.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    p.add_argument("--credenciais", default=None)
    p.add_argument("--modelo", default="naive_bayes",
                   help="um do zoo, ou 'todos'.")
    p.add_argument("--inicio", type=int, default=0)
    p.add_argument("--limite", type=int, default=200)
    p.add_argument("--passo", type=int, default=0,
                   help="Se >0, ladrilha TODA a base em janelas desse tamanho e SUBSTITUI "
                        "COMPARACAO_MODELOS/_CATEGORIA (cobertura completa, nao so 0-1000).")
    p.add_argument("--executar-todos", action="store_true")
    p.add_argument("--aplicar", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    with args.config.open(encoding="utf-8") as f:
        config = json.load(f)
    abas = config["abas_experimento"]
    limiar = float(config.get("comparacao", {}).get("limiar_revisao", 0.95))
    gerado = agora_bahia()

    if args.modelo.strip().lower() == "todos" or args.executar_todos:
        modelos = zoo.MODELOS_LEVES
    else:
        modelos = [args.modelo.strip().lower()]

    try:
        sh = pl.abrir_planilha(pl.id_planilha(config), args.credenciais)
        ws = sh.worksheet(config["aba_principal"])
        elig = carregar_elegiveis(ws, config)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr); return 2
    except Exception as e:  # noqa: BLE001
        print(f"Falha ao acessar a planilha: {type(e).__name__}: {e}", file=sys.stderr); return 1

    # --- Modo TILING: cobre TODA a base em janelas de tamanho --passo e SUBSTITUI
    # a tabela de recortes (em vez de parar em 0-1000). Held-out por janela: cada
    # modelo treina em tudo menos a janela avaliada. Nao grava COMPARACAO_PREVISOES
    # (seriam ~13.825 x N modelos linhas) — so as metricas por (modelo, lote).
    if args.passo and args.passo > 0:
        passo = args.passo
        n_elig = len(elig)
        janelas = [(i, min(i + passo, n_elig)) for i in range(0, n_elig, passo)]
        print(f"TILING: elegiveis={n_elig} | passo={passo} | janelas={len(janelas)} | modelos={modelos}")
        linhas_m, linhas_c = [], []
        for ini, fim in janelas:
            teste = elig[ini:fim]
            linhas_teste = {e["linha"] for e in teste}
            treino = [e for e in elig if e["linha"] not in linhas_teste]
            if len(teste) < 2 or len(treino) < 2:
                continue
            for nome in modelos:
                try:
                    met, por_cat, _ = avaliar_modelo(nome, treino, teste, limiar)
                except Exception as e:  # noqa: BLE001
                    print(f"[{nome} {ini}-{fim}] falhou: {type(e).__name__}: {e}", file=sys.stderr)
                    continue
                linhas_m.append([met["modelo"], ini, fim, met["n"], met["acuracia"],
                                 met["f1_macro"], met["f1_weighted"], met["balanced_accuracy"],
                                 met["n_revisao"],
                                 met["acerto_baixa_conf"] if met["acerto_baixa_conf"] is not None else "",
                                 met["tempo_treino_s"], met["tempo_inferencia_s"], gerado])
                for c in por_cat:
                    linhas_c.append([met["modelo"], ini, fim, c["categoria"], c["precision"],
                                     c["recall"], c["f1"], c["suporte"], gerado])
            print(f"  janela {ini}-{fim}: {len(teste)} testados | acumulado={len(linhas_m)} linhas")
        if not args.aplicar:
            print(f"modo=dry-run (nada gravado). recortes={len(linhas_m)} | categorias={len(linhas_c)}")
            return 0
        cab_m = ["modelo", "inicio", "limite", "n_registros", "acuracia", "f1_macro",
                 "f1_weighted", "balanced_accuracy", "n_revisao", "acerto_baixa_conf",
                 "tempo_treino_s", "tempo_inferencia_s", "executado_em"]
        pl.escrever_aba(sh, abas["comparacao_modelos"], cab_m, linhas_m, colunas_percentuais=[5, 6, 7, 8, 10])
        cab_c = ["modelo", "inicio", "limite", "categoria", "precision", "recall", "f1", "suporte", "executado_em"]
        pl.escrever_aba(sh, abas["comparacao_categoria"], cab_c, linhas_c, colunas_percentuais=[5, 6, 7])
        print(f"OK (tiling): COMPARACAO_MODELOS={len(linhas_m)} | COMPARACAO_CATEGORIA={len(linhas_c)} "
              f"| janelas={len(janelas)} cobrindo 0-{n_elig}")
        return 0

    fim = args.inicio + args.limite if args.limite > 0 else len(elig)
    teste = elig[args.inicio:fim]
    linhas_teste = {e["linha"] for e in teste}
    treino = [e for e in elig if e["linha"] not in linhas_teste]

    print(f"elegiveis={len(elig)} | lote_teste=[{args.inicio}:{fim}] n={len(teste)} | "
          f"treino={len(treino)} | modelos={modelos}")
    if len(teste) < 2 or len(treino) < 2:
        print("Informação insuficiente para verificar."); return 1

    resultados = []
    for nome in modelos:
        try:
            met, por_cat, prev = avaliar_modelo(nome, treino, teste, limiar)
        except Exception as e:  # noqa: BLE001
            print(f"[{nome}] falhou: {type(e).__name__}: {e}", file=sys.stderr)
            continue
        resultados.append((met, por_cat, prev))
        print(f"[{nome}] acc={met['acuracia']} f1_macro={met['f1_macro']} "
              f"bal_acc={met['balanced_accuracy']} revisao={met['n_revisao']} "
              f"treino={met['tempo_treino_s']}s infer={met['tempo_inferencia_s']}s")

    if not args.aplicar:
        print("modo=dry-run (nada gravado).")
        return 0

    cab_m = ["modelo", "inicio", "limite", "n_registros", "acuracia", "f1_macro",
             "f1_weighted", "balanced_accuracy", "n_revisao", "acerto_baixa_conf",
             "tempo_treino_s", "tempo_inferencia_s", "executado_em"]
    linhas_m = [[m["modelo"], args.inicio, fim, m["n"], m["acuracia"], m["f1_macro"],
                 m["f1_weighted"], m["balanced_accuracy"], m["n_revisao"],
                 m["acerto_baixa_conf"] if m["acerto_baixa_conf"] is not None else "",
                 m["tempo_treino_s"], m["tempo_inferencia_s"], gerado] for m, _, _ in resultados]
    pl.append_aba(sh, abas["comparacao_modelos"], cab_m, linhas_m, colunas_percentuais=[5, 6, 7, 8, 10])

    cab_c = ["modelo", "inicio", "limite", "categoria", "precision", "recall", "f1", "suporte", "executado_em"]
    linhas_c = []
    for m, por_cat, _ in resultados:
        for c in por_cat:
            linhas_c.append([m["modelo"], args.inicio, fim, c["categoria"], c["precision"],
                             c["recall"], c["f1"], c["suporte"], gerado])
    pl.append_aba(sh, abas["comparacao_categoria"], cab_c, linhas_c, colunas_percentuais=[5, 6, 7])

    cab_p = ["modelo", "linha_planilha", "id_chamado", "titulo", "categoria_original",
             "categoria_prevista", "score", "divergencia", "enviado_revisao", "executado_em",
             "validacao_humana_final", "quem_estava_correto", "observacao_avaliador", "data_validacao"]
    linhas_p = []
    for m, _, prev in resultados:
        for p in prev:
            linhas_p.append([m["modelo"], p["linha"], p["id"], p["titulo"], p["original"],
                             p["prevista"], p["score"], str(p["divergencia"]), str(p["revisao"]),
                             gerado, "", "", "", ""])
    pl.append_aba(sh, abas["comparacao_previsoes"], cab_p, linhas_p, colunas_percentuais=[7])
    # dropdown em "quem_estava_correto" (col 12)
    try:
        wsp = sh.worksheet(abas["comparacao_previsoes"])
        ultima = wsp.row_count
        pl.dropdown(wsp, 12, 2, ultima, QUEM_CORRETO)
    except Exception:  # noqa: BLE001
        pass

    print(f"OK: {len(resultados)} modelo(s) gravados | previsoes={len(linhas_p)} | categorias={len(linhas_c)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
