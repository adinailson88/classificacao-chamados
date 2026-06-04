#!/usr/bin/env python3
"""Etapa 2 do roteiro — RECLASSIFICAÇÃO dos casos de baixa confiança (17-23).

Reavalia os chamados classificados na Etapa 1 com confiança < limiar de alta (95%),
de forma PROGRESSIVA (turnos), comparando o estado ANTES (Etapa 1, lido do
SNAPSHOT_ETAPA_1) com o DEPOIS (reclassificação) e medindo o GANHO LÍQUIDO
(corrigidos − prejudicados).

- candidatos = SNAPSHOT com confiança < 0,95, não conferidos (M≠TRUE) e ainda não
  reclassificados (executor atual não começa com "Reclass");
- treina o modelo (producao=LSTM | baseline | robusto=transformer) na base rotulada
  e reprediz só os candidatos;
- grava G:J com a nova categoria/confiança e executor "Reclass_<tag>";
- APPEND em LOG_TURNOS_RECLASSIFICACAO (antes/depois, corrigidos, prejudicados,
  mantidos, ganho líquido, variação média de confiança) e LOG_LINHA_A_LINHA (etapa 2).

Sem --aplicar = dry-run. Acesso via conta de serviço (gspread).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planilha as pl  # noqa: E402
import classificador_producao as cp  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
DADOS = RAIZ / "dados"
FUSO_BAHIA = timezone(timedelta(hours=-3))
COL_G, COL_J = 7, 10


def agora_bahia() -> str:
    return datetime.now(FUSO_BAHIA).strftime("%Y-%m-%dT%H:%M:%S-03:00")


def cel(linha, idx) -> str:
    return str(linha[idx] or "").strip() if (idx is not None and idx < len(linha)) else ""


def parse_conf(v) -> float:
    try:
        f = float(str(v).replace("%", "").replace(",", ".").strip())
        return f / 100.0 if f > 1 else f
    except (ValueError, TypeError):
        return 0.0


def treinar_reclass(modelo, textos, cats):
    """Retorna (predict_fn, tag). predict_fn(textos) -> (preds, confs)."""
    if modelo == "robusto":
        import classificador_robusto as cr
        clf, tag = cr.treinar(textos, cats)
        return (lambda x: clf.predict_com_conf(x)), tag
    if modelo == "baseline":
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline
        clf = Pipeline([
            ("tfidf", TfidfVectorizer(strip_accents="unicode", lowercase=True,
                                      ngram_range=(1, 2), min_df=1, max_features=30000)),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ])
        clf.fit(textos, cats)

        def f(x):
            p = clf.predict_proba(x)
            i = p.argmax(axis=1)
            return clf.classes_[i], p[np.arange(len(i)), i]
        return f, "Baseline"
    clf, eh_lstm = cp.treinar_classificador(textos, cats)
    return (lambda x: cp.predizer(clf, eh_lstm, x)), ("LSTM" if eh_lstm else "RF")


def carregar_snapshot(sh, nome):
    """linha -> (categoria_ia_1, confianca_1)."""
    try:
        vals = sh.worksheet(nome).get_values("A:J", value_render_option="UNFORMATTED_VALUE")
    except Exception:  # noqa: BLE001
        return {}
    m = {}
    for r in vals[1:]:
        if len(r) < 6:
            continue
        try:
            ln = int(r[1])
        except (ValueError, TypeError):
            continue
        m[ln] = (str(r[4]).strip(), parse_conf(r[5]))
    return m


def cumulativo_reclass_turnos(sh, nome) -> int:
    try:
        vals = sh.worksheet(nome).get_all_values()
        return max(0, len(vals) - 1)
    except Exception:  # noqa: BLE001
        return 0


def parse_args():
    p = argparse.ArgumentParser(description="Etapa 2 — reclassificação progressiva.")
    p.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    p.add_argument("--credenciais", default=None)
    p.add_argument("--modelo", choices=["producao", "baseline", "robusto"], default="producao")
    p.add_argument("--tamanho-turno", type=int, default=15)
    p.add_argument("--max-turnos", type=int, default=40, help="Turnos por execução (0=todos).")
    p.add_argument("--aplicar", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    with args.config.open(encoding="utf-8") as f:
        config = json.load(f)
    aba = config["aba_principal"]
    abas = config["abas_experimento"]
    lim_alta = float(config.get("classificacao", {}).get("limiar_alta_confianca", 0.95))
    run_id = config.get("run_id", "")
    gerado = agora_bahia()
    tam = args.tamanho_turno

    try:
        sh = pl.abrir_planilha(pl.id_planilha(config), args.credenciais)
        ws = sh.worksheet(aba)
        valores = pl.ler_valores(ws, config["range_leitura"])
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr); return 2
    except Exception as e:  # noqa: BLE001
        print(f"Falha ao acessar a planilha: {type(e).__name__}: {e}", file=sys.stderr); return 1

    cab = valores[0] if valores else []
    norm = lambda s: " ".join(str(s or "").split()).casefold()  # noqa: E731
    idx = {norm(n): i for i, n in enumerate(cab)}
    i_id, i_tit, i_cat = idx.get(norm("ID Chamado")), idx.get(norm("TÍTULO")), idx.get(norm("CATEGORIA COMPLETA"))
    i_dg, i_to, i_do = idx.get(norm("DESCRIÇÃO GLPI")), idx.get(norm("TÍTULO O.S.M.")), idx.get(norm("DESCRIÇÃO O.S.M."))
    i_exec, i_conf = idx.get(norm("Executor")), idx.get(norm("CONFERÊNCIA"))

    # Base rotulada (treino) e índice por linha.
    elegiveis = []
    info = {}
    for pos, linha in enumerate(valores[1:], start=2):
        cat = cel(linha, i_cat)
        texto = "\n".join(c for c in [cel(linha, i_tit), cel(linha, i_dg),
                                      cel(linha, i_to), cel(linha, i_do)] if c)
        if cat and texto:
            elegiveis.append((texto, cat))
            info[pos] = {
                "id": cel(linha, i_id), "categoria_original": cat, "texto": texto,
                "exec_atual": cel(linha, i_exec),
                "conferido": cel(linha, i_conf).upper() in {"TRUE", "VERDADEIRO", "SIM"},
            }

    snap = carregar_snapshot(sh, abas["snapshot_etapa_1"])

    candidatos = []
    for ln, (cat_ia_1, conf_1) in snap.items():
        d = info.get(ln)
        if not d or d["conferido"]:
            continue
        if d["exec_atual"].startswith("Reclass"):
            continue  # já reclassificado
        if conf_1 < lim_alta:
            candidatos.append((ln, cat_ia_1, conf_1, d))

    candidatos.sort(key=lambda c: c[0])
    total_cand = len(candidatos)
    print(f"run_id={run_id} | elegiveis={len(elegiveis)} | candidatos_reclass={total_cand} | modelo={args.modelo}")

    if total_cand == 0:
        print("Etapa 2 concluída (0 candidatos a reclassificar).")
        return 0

    n_lote = total_cand if args.max_turnos <= 0 else min(total_cand, args.max_turnos * tam)
    lote = candidatos[:n_lote]

    print("treinando modelo de reclassificação...")
    predict_fn, tag = treinar_reclass(args.modelo, [t for t, _ in elegiveis], [c for _, c in elegiveis])
    executor_reclass = f"Reclass_{tag}"
    preds, confs = predict_fn([d["texto"] for (_, _, _, d) in lote])

    registros = []
    for (ln, cat_ia_1, conf_1, d), pred, conf2 in zip(lote, preds, confs):
        orig = d["categoria_original"]
        cat_2, conf_2 = str(pred), round(float(conf2), 4)
        correto_antes = (cat_ia_1 == orig)
        correto_depois = (cat_2 == orig)
        if not correto_antes and correto_depois:
            resultado = "corrigido"
        elif correto_antes and not correto_depois:
            resultado = "prejudicado"
        elif correto_antes and correto_depois:
            resultado = "mantido_correto"
        else:
            resultado = "mantido_errado"
        registros.append({
            "linha": ln, "id": d["id"], "original": orig,
            "cat_1": cat_ia_1, "conf_1": conf_1, "correto_antes": correto_antes,
            "cat_2": cat_2, "conf_2": conf_2, "correto_depois": correto_depois,
            "mudou": cat_2 != cat_ia_1, "delta_conf": round(conf_2 - conf_1, 4),
            "resultado": resultado, "criticidade": cp.estimar_criticidade(d["texto"]),
        })

    corrigidos = sum(1 for r in registros if r["resultado"] == "corrigido")
    prejudicados = sum(1 for r in registros if r["resultado"] == "prejudicado")
    ganho = corrigidos - prejudicados
    corretos_antes = sum(1 for r in registros if r["correto_antes"])
    corretos_depois = sum(1 for r in registros if r["correto_depois"])
    print(f"lote={len(registros)} | corrigidos={corrigidos} | prejudicados={prejudicados} | "
          f"GANHO_LIQUIDO={ganho} | concordancia antes={corretos_antes}/{len(registros)} "
          f"depois={corretos_depois}/{len(registros)}")

    DADOS.mkdir(parents=True, exist_ok=True)
    (DADOS / "etapa2_ultimo_lote.json").write_text(
        json.dumps({"run_id": run_id, "gerado_em": gerado, "executor": executor_reclass,
                    "lote": len(registros), "ganho_liquido": ganho}, ensure_ascii=False, indent=2),
        encoding="utf-8")

    if not args.aplicar:
        print("modo=dry-run (nada gravado na planilha)")
        return 0

    # Grava G:J reclassificado (executor Reclass_<tag>)
    linhas_gj = [{"linha": r["linha"], "valores": [r["cat_2"], r["conf_2"], executor_reclass, r["criticidade"]]}
                 for r in registros]
    pl.exportar_lote_gj(ws, linhas_gj, col_inicio=COL_G, col_fim=COL_J)

    # APPEND LOG_TURNOS_RECLASSIFICACAO (turnos de 15)
    prev = cumulativo_reclass_turnos(sh, abas["log_turnos_reclassificacao"])
    turnos = []
    for k, ini in enumerate(range(0, len(registros), tam)):
        b = registros[ini:ini + tam]
        n = len(b)
        ca = sum(1 for r in b if r["correto_antes"]); cd = sum(1 for r in b if r["correto_depois"])
        corr = sum(1 for r in b if r["resultado"] == "corrigido")
        prej = sum(1 for r in b if r["resultado"] == "prejudicado")
        mc = sum(1 for r in b if r["resultado"] == "mantido_correto")
        me = sum(1 for r in b if r["resultado"] == "mantido_errado")
        turnos.append([
            run_id, prev + k + 1, n, ca, n - ca, round(ca / n, 4),
            cd, n - cd, round(cd / n, 4), corr, prej, mc, me, corr - prej,
            round(float(np.mean([r["delta_conf"] for r in b])), 4), executor_reclass, gerado,
        ])
    cab_rt = ["run_id", "turno", "qtd_reclassificados", "qtd_corretos_antes", "qtd_incorretos_antes",
              "taxa_concordancia_antes", "qtd_corretos_depois", "qtd_incorretos_depois",
              "taxa_concordancia_depois", "qtd_corrigidos", "qtd_prejudicados",
              "qtd_mantidos_corretos", "qtd_mantidos_errados", "ganho_liquido",
              "variacao_media_confianca", "executor", "data_hora"]
    pl.append_aba(sh, abas["log_turnos_reclassificacao"], cab_rt, turnos,
                  colunas_percentuais=[6, 9])

    # APPEND LOG_LINHA_A_LINHA (etapa 2)
    cab_l = ["run_id", "etapa", "turno", "linha_planilha", "id_chamado", "titulo", "data_abertura",
             "categoria_original", "categoria_ia", "conferencia", "confianca", "executor",
             "criticidade", "data_hora"]
    linhas_l = []
    for k, ini in enumerate(range(0, len(registros), tam)):
        for r in registros[ini:ini + tam]:
            linhas_l.append([run_id, 2, prev + k + 1, r["linha"], r["id"], "", "",
                             r["original"], r["cat_2"], str(r["correto_depois"]),
                             r["conf_2"], executor_reclass, r["criticidade"], gerado])
    pl.append_aba(sh, abas["log_linha_a_linha"], cab_l, linhas_l, colunas_percentuais=[11])

    print(f"OK: {len(registros)} reclassificados ({executor_reclass}) | ganho liquido={ganho} | "
          f"restam {total_cand - len(lote)} candidatos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
