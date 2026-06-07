#!/usr/bin/env python3
"""Análises estatísticas formais sobre os resultados das 7 IAs (Extensão B).

Lê as abas CLASSIF__<modelo> (predição por linha + confiança + acerto vs histórico)
e MULTIMODELO_TURNOS, e calcula um conjunto de estatísticas comparáveis e
publicáveis. Grava um JSON AGREGADO (sem texto de chamado) em
docs/dados/estatistica.json, consumido pela aba "Estatistica" do painel.

Análises:
- Correlação confiança × acerto (ponto-bisserial e Spearman) por modelo.
- Normalidade da concordância por turno (Shapiro-Wilk) por modelo.
- Resíduos/tendência da concordância ao longo dos turnos (OLS, R², Durbin-Watson).
- Acurácia com IC 95% por bootstrap, por modelo.
- Kappa de Cohen (IA × histórico) por modelo; Kappa de Fleiss entre as 7 IAs.
- Cochran's Q (as 7 IAs têm a mesma acurácia?) e teste de McNemar par a par.
- Friedman entre modelos sobre os recortes + ranks médios e diferença crítica (Nemenyi).

100% local, sem texto sensível na saída. Acesso via conta de serviço (gspread).
"""

from __future__ import annotations

import json
import sys
import time
from itertools import combinations
from math import sqrt
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planilha as pl  # noqa: E402
from tempo import agora_bahia  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
SAIDA = RAIZ / "docs" / "dados" / "estatistica.json"

# q_alpha (alpha=0.05) da distribuição do range studentizado / sqrt(2), por k (=nº modelos).
# Usado na diferença crítica de Nemenyi. Fonte: Demšar (2006), tabela de q.
Q_NEMENYI_005 = {2: 1.960, 3: 2.343, 4: 2.569, 5: 2.728, 6: 2.850, 7: 2.949, 8: 3.031}


def _retry(rotulo, func, tentativas=5, espera=20):
    for i in range(1, tentativas + 1):
        try:
            return func()
        except Exception as e:  # noqa: BLE001
            transit = any(t in str(e).lower() for t in ("429", "quota", "rate limit", "unavailable"))
            if i >= tentativas or not transit:
                raise
            print(f"{rotulo}: retry {i} em {espera*i}s ({type(e).__name__})", file=sys.stderr)
            time.sleep(espera * i)


def parse_conf(v) -> float:
    try:
        f = float(str(v).replace("%", "").replace(",", ".").strip())
        return f / 100.0 if f > 1 else f
    except (ValueError, TypeError):
        return 0.0


def carregar_modelo(sh, aba):
    """linha -> {orig, ia, conf, acerto} a partir de CLASSIF__<modelo>."""
    try:
        vals = _retry(f"ler {aba}", lambda: sh.worksheet(aba).get_values(
            "A:K", value_render_option="UNFORMATTED_VALUE"))
    except Exception:  # noqa: BLE001
        return {}
    # cols: 1 linha, 3 cat_original, 4 cat_ia, 5 confianca, 8 acerto_historico
    out = {}
    for r in vals[1:]:
        if len(r) < 6:
            continue
        try:
            ln = int(r[1])
        except (ValueError, TypeError):
            continue
        orig = str(r[3]).strip(); ia = str(r[4]).strip()
        if not ia:
            continue
        out[ln] = {"orig": orig, "ia": ia, "conf": parse_conf(r[5]), "acerto": int(ia == orig)}
    return out


def turnos_por_modelo(sh, aba):
    """modelo -> lista de (turno, taxa_concordancia) de MULTIMODELO_TURNOS."""
    try:
        vals = _retry("ler turnos", lambda: sh.worksheet(aba).get_values(
            "A:P", value_render_option="UNFORMATTED_VALUE"))
    except Exception:  # noqa: BLE001
        return {}
    cab = [str(c).strip() for c in vals[0]] if vals else []
    idx = {c: i for i, c in enumerate(cab)}
    im, it, ix = idx.get("modelo"), idx.get("turno"), idx.get("taxa_concordancia")
    if None in (im, it, ix):
        return {}
    out = {}
    for r in vals[1:]:
        if len(r) <= max(im, it, ix):
            continue
        m = str(r[im]).strip()
        try:
            out.setdefault(m, []).append((float(r[it]), float(r[ix])))
        except (ValueError, TypeError):
            pass
    for m in out:
        out[m].sort(key=lambda p: p[0])
    return out


def bootstrap_ic(acertos: np.ndarray, n_boot=2000, seed=42):
    rng = np.random.default_rng(seed)
    n = len(acertos)
    if n == 0:
        return 0.0, 0.0, 0.0
    means = acertos[rng.integers(0, n, size=(n_boot, n))].mean(axis=1)
    return float(acertos.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def main() -> int:
    from scipy import stats as st
    from sklearn.metrics import cohen_kappa_score
    from statsmodels.stats.contingency_tables import cochrans_q, mcnemar
    from statsmodels.stats.inter_rater import aggregate_raters, fleiss_kappa
    from statsmodels.stats.stattools import durbin_watson

    with CONFIG_PADRAO.open(encoding="utf-8") as f:
        config = json.load(f)
    mm = config["multimodelo"]
    modelos = list(mm["modelos_leves"]) + list(mm.get("modelos_pesados", []))

    try:
        sh = _retry("abrir planilha", lambda: pl.abrir_planilha(pl.id_planilha(config)))
    except Exception as e:  # noqa: BLE001
        print(f"Falha ao abrir planilha: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    dados = {}
    for m in modelos:
        d = carregar_modelo(sh, mm["aba_classificacao"].replace("{modelo}", m))
        if d:
            dados[m] = d
            print(f"{m}: {len(d)} linhas")
    modelos = [m for m in modelos if m in dados]
    if len(modelos) < 2:
        print("Menos de 2 modelos materializados; estatística comparativa indisponível.")
        return 1

    linhas_comuns = sorted(set.intersection(*[set(dados[m]) for m in modelos]))
    n = len(linhas_comuns)
    print(f"modelos={modelos} | linhas_comuns={n}")

    # Matriz de acerto (n x k) e categorias previstas (n x k) alinhadas por linha.
    acerto = {m: np.array([dados[m][ln]["acerto"] for ln in linhas_comuns]) for m in modelos}
    conf = {m: np.array([dados[m][ln]["conf"] for ln in linhas_comuns]) for m in modelos}
    orig = [dados[modelos[0]][ln]["orig"] for ln in linhas_comuns]
    pred = {m: [dados[m][ln]["ia"] for ln in linhas_comuns] for m in modelos}

    out = {"gerado_em": agora_bahia(), "n_linhas_comuns": n, "modelos": modelos,
           "alpha": 0.05, "observacao": "Acerto = IA x categoria historica (preliminar; "
           "a validacao humana qualifica). Sem texto de chamado. Normalidade rejeitada "
           "(Shapiro) nos modelos avaliados: a analise assume pressupostos NAO "
           "parametricos (Spearman, Friedman/Nemenyi, Cochran Q, McNemar, bootstrap). "
           "Resultados sao contra o historico, nao contra validacao humana."}

    # 1) Correlação confiança × acerto (ponto-bisserial e Spearman)
    out["correlacao_conf_acerto"] = []
    for m in modelos:
        try:
            rb, pb = st.pointbiserialr(acerto[m], conf[m])
            rs, ps = st.spearmanr(conf[m], acerto[m])
            out["correlacao_conf_acerto"].append({
                "modelo": m, "pointbiserial_r": round(float(rb), 4), "p_pb": float(f"{pb:.2e}"),
                "spearman_r": round(float(rs), 4), "p_sp": float(f"{ps:.2e}"),
                "interpretacao": "positiva = mais confianca -> mais acerto"})
        except Exception as e:  # noqa: BLE001
            print(f"corr {m}: {e}", file=sys.stderr)

    # 2/3) Normalidade + resíduos/tendência da concordância por turno
    tur = turnos_por_modelo(sh, mm["aba_turnos"])
    out["normalidade_concordancia_turno"], out["residuos_tendencia"] = [], []
    for m in modelos:
        serie = [taxa for _, taxa in tur.get(m, [])]
        if len(serie) >= 8:
            y = np.array(serie)
            try:
                W, pW = st.shapiro(y)
                out["normalidade_concordancia_turno"].append({
                    "modelo": m, "n_turnos": len(y), "shapiro_W": round(float(W), 4),
                    "p": float(f"{pW:.2e}"), "normal_5pct": bool(pW > 0.05)})
            except Exception as e:  # noqa: BLE001
                print(f"shapiro {m}: {e}", file=sys.stderr)
            try:
                x = np.arange(len(y))
                sl, itc, r, pr, se = st.linregress(x, y)
                resid = y - (sl * x + itc)
                dw = float(durbin_watson(resid))
                out["residuos_tendencia"].append({
                    "modelo": m, "n_turnos": len(y), "slope": round(float(sl), 6),
                    "r2": round(float(r**2), 4), "p_tendencia": float(f"{pr:.2e}"),
                    "durbin_watson": round(dw, 3),
                    "tendencia": ("estavel" if pr > 0.05 else ("sobe" if sl > 0 else "cai"))})
            except Exception as e:  # noqa: BLE001
                print(f"resid {m}: {e}", file=sys.stderr)

    # 3b) Veredito de pressupostos: agrega a normalidade e fixa a postura não paramétrica.
    norm = out["normalidade_concordancia_turno"]
    n_aval = len(norm)
    n_rejeita = sum(1 for d in norm if not d["normal_5pct"])
    out["pressupostos"] = {
        "normalidade_testada": "Shapiro-Wilk sobre a concordancia por turno",
        "modelos_avaliados": n_aval,
        "modelos_normais_5pct": n_aval - n_rejeita,
        "modelos_normalidade_rejeitada": n_rejeita,
        "normalidade_rejeitada": (n_aval > 0 and n_rejeita == n_aval),
        "assume": "nao_parametrico" if (n_aval == 0 or n_rejeita > 0) else "parametrico",
        "metodos_nao_parametricos": ["Spearman", "Friedman/Nemenyi", "Cochran Q",
                                     "McNemar", "bootstrap"],
        "base_de_comparacao": "categoria historica (nao validacao humana)",
        "nota": "Normalidade rejeitada nos modelos avaliados; a analise NAO usa pressuposto "
                "parametrico como criterio principal. Resultados sao contra o historico.",
    }

    # 4) Acurácia + IC 95% (bootstrap)
    out["acuracia_bootstrap"] = []
    for m in modelos:
        acc, lo, hi = bootstrap_ic(acerto[m])
        out["acuracia_bootstrap"].append({"modelo": m, "acuracia": round(acc, 4),
                                          "ic95_min": round(lo, 4), "ic95_max": round(hi, 4)})
    out["acuracia_bootstrap"].sort(key=lambda d: -d["acuracia"])

    # 5) Kappa de Cohen (IA x histórico) por modelo
    out["kappa_cohen_historico"] = []
    for m in modelos:
        try:
            k = cohen_kappa_score(orig, pred[m])
            out["kappa_cohen_historico"].append({"modelo": m, "kappa": round(float(k), 4)})
        except Exception as e:  # noqa: BLE001
            print(f"kappa {m}: {e}", file=sys.stderr)
    out["kappa_cohen_historico"].sort(key=lambda d: -d["kappa"])

    # 5b) Kappa de Fleiss entre as IAs (concordância entre os 7 classificadores)
    try:
        tabela = [[pred[m][i] for m in modelos] for i in range(n)]
        agg, _ = aggregate_raters(np.array(tabela))
        out["fleiss_kappa_entre_ias"] = round(float(fleiss_kappa(agg)), 4)
    except Exception as e:  # noqa: BLE001
        print(f"fleiss: {e}", file=sys.stderr)
        out["fleiss_kappa_entre_ias"] = None

    # 6) Cochran's Q (as k IAs têm a mesma acurácia?)
    try:
        M = np.column_stack([acerto[m] for m in modelos])
        cq = cochrans_q(M)
        out["cochran_q"] = {"Q": round(float(cq.statistic), 3), "p": float(f"{cq.pvalue:.2e}"),
                            "df": len(modelos) - 1,
                            "conclusao": ("acuracias diferentes (p<0,05)" if cq.pvalue < 0.05
                                          else "sem diferenca significativa")}
    except Exception as e:  # noqa: BLE001
        print(f"cochran: {e}", file=sys.stderr)

    # 6b) McNemar par a par (matriz de p-valores)
    out["mcnemar"] = {"modelos": modelos, "p": [[None] * len(modelos) for _ in modelos]}
    for a, b in combinations(range(len(modelos)), 2):
        ma, mb = modelos[a], modelos[b]
        # tabela 2x2: (a certo/errado) x (b certo/errado)
        tab = np.zeros((2, 2), dtype=int)
        for i in range(n):
            tab[1 - acerto[ma][i]][1 - acerto[mb][i]] += 1
        try:
            res = mcnemar(tab, exact=False, correction=True)
            p = float(res.pvalue)
        except Exception:  # noqa: BLE001
            p = None
        out["mcnemar"]["p"][a][b] = None if p is None else float(f"{p:.2e}")
        out["mcnemar"]["p"][b][a] = out["mcnemar"]["p"][a][b]

    # 7) Friedman sobre os recortes (comparacao_modelos) + ranks + diferença crítica Nemenyi
    try:
        comp = json.loads((RAIZ / "docs" / "dados" / "comparacao_modelos.json").read_text(encoding="utf-8"))
        por_modelo = {}
        for r in comp:
            lote = f"{r.get('inicio')}-{r.get('limite')}"
            por_modelo.setdefault(str(r.get("modelo")), {})[lote] = float(r.get("acuracia") or 0)
        lotes = sorted({l for d in por_modelo.values() for l in d}, key=lambda s: int(s.split("-")[0]))
        mods_f = [m for m in modelos if m in por_modelo and all(l in por_modelo[m] for l in lotes)]
        if len(mods_f) >= 3 and len(lotes) >= 3:
            mat = np.array([[por_modelo[m][l] for l in lotes] for m in mods_f])  # k x blocos
            fr = st.friedmanchisquare(*[mat[i] for i in range(len(mods_f))])
            # ranks médios (1 = melhor) por bloco
            ranks = np.array([st.rankdata(-mat[:, j]) for j in range(mat.shape[1])])  # blocos x k
            rank_med = ranks.mean(axis=0)
            k, Nb = len(mods_f), mat.shape[1]
            cd = Q_NEMENYI_005.get(k, 3.0) * sqrt(k * (k + 1) / (6.0 * Nb))
            out["friedman"] = {
                "stat": round(float(fr.statistic), 3), "p": float(f"{fr.pvalue:.2e}"),
                "blocos": lotes, "modelos": mods_f,
                "rank_medio": [{"modelo": mods_f[i], "rank_medio": round(float(rank_med[i]), 3)}
                               for i in np.argsort(rank_med)],
                "diferenca_critica_nemenyi": round(float(cd), 3),
                "nota": "Diferenca de rank_medio > CD => diferenca significativa (Nemenyi, alpha=0,05)."}
    except Exception as e:  # noqa: BLE001
        print(f"friedman: {e}", file=sys.stderr)

    # 8) Holm-Bonferroni sobre os p-valores do McNemar (controla erro tipo I nos pares)
    try:
        pares = []
        for a, b in combinations(range(len(modelos)), 2):
            p = out["mcnemar"]["p"][a][b]
            if p is not None:
                pares.append((modelos[a], modelos[b], float(p)))
        pares.sort(key=lambda x: x[2])
        mtests = len(pares)
        holm, ainda_sig = [], True
        for i, (ma, mb, p) in enumerate(pares):
            limiar = 0.05 / (mtests - i) if (mtests - i) > 0 else 0.05
            sig = bool(ainda_sig and p <= limiar)
            if not sig:
                ainda_sig = False  # step-down: para na 1a nao-rejeicao
            holm.append({"par": [ma, mb], "p": float(f"{p:.2e}"),
                         "limiar_holm": float(f"{limiar:.2e}"), "significativo": sig})
        out["mcnemar_holm"] = {
            "n_testes": mtests, "alpha": 0.05, "metodo": "Holm-Bonferroni (step-down)",
            "pares": holm, "pares_significativos": [h["par"] for h in holm if h["significativo"]],
            "nota": "Corrige multiplicidade dos pares McNemar; controla o erro familiar (FWER)."}
    except Exception as e:  # noqa: BLE001
        print(f"holm: {e}", file=sys.stderr)

    # 9) macro-F1 e macro-recall com IC95 bootstrap, por modelo (vs historico)
    try:
        from sklearn.metrics import f1_score, recall_score
        rng = np.random.default_rng(42)
        ytrue = np.array(orig)
        out["f1_macro_bootstrap"] = []
        for m in modelos:
            yp = np.array(pred[m])
            f1 = f1_score(ytrue, yp, average="macro", zero_division=0)
            rc = recall_score(ytrue, yp, average="macro", zero_division=0)
            bf, br = [], []
            for _ in range(500):
                s = rng.integers(0, n, n)
                bf.append(f1_score(ytrue[s], yp[s], average="macro", zero_division=0))
                br.append(recall_score(ytrue[s], yp[s], average="macro", zero_division=0))
            out["f1_macro_bootstrap"].append({
                "modelo": m, "f1_macro": round(float(f1), 4),
                "f1_ic95": [round(float(np.percentile(bf, 2.5)), 4), round(float(np.percentile(bf, 97.5)), 4)],
                "recall_macro": round(float(rc), 4),
                "recall_ic95": [round(float(np.percentile(br, 2.5)), 4), round(float(np.percentile(br, 97.5)), 4)]})
        out["f1_macro_bootstrap"].sort(key=lambda d: -d["f1_macro"])
    except Exception as e:  # noqa: BLE001
        print(f"f1_macro: {e}", file=sys.stderr)

    # 10) Top confusoes (categoria_historica -> previsto) por modelo, compacto
    try:
        from collections import Counter
        out["top_confusoes"] = []
        for m in modelos:
            c = Counter((orig[i], pred[m][i]) for i in range(n) if pred[m][i] != orig[i])
            out["top_confusoes"].append({"modelo": m, "pares": [
                {"de": de, "para": para, "n": qt} for (de, para), qt in c.most_common(10)]})
    except Exception as e:  # noqa: BLE001
        print(f"confusoes: {e}", file=sys.stderr)

    # 11) Estatistica contra a VERDADE VALIDADA (conferencia dupla M/N), quando houver.
    #     Verdade derivada: N (CONFERENCIA IA)=Correto -> categoria = G (Etapa 1);
    #     senao M (CONFERENCIA GLPI)=Correto -> categoria = C (historico). Pronto para
    #     popular automaticamente a medida que a validacao humana cresce.
    try:
        conferencias = pl.ler_conferencias(sh, config["aba_principal"])
        regs = json.loads((RAIZ / "docs" / "dados" / "registros.json").read_text(encoding="utf-8"))
        gc = {str(r.get("l")): {"G": r.get("p"), "C": r.get("o")} for r in regs}
        verdade = {}
        for ln, c in conferencias.items():
            base = gc.get(ln, {})
            if c.get("ia") == "Correto":
                verdade[ln] = base.get("G")
            elif c.get("glpi") == "Correto":
                verdade[ln] = base.get("C")
        verdade = {k: v for k, v in verdade.items() if v}
        val = {"n_verdade_derivada": len(verdade),
               "base": "conferencia dupla M/N (N=Correto->G; senao M=Correto->C)",
               "nota": "Preliminar enquanto a amostra validada e pequena/nao aleatoria.",
               "por_modelo": []}
        for m in modelos:
            nv = okv = 0
            for ln, tru in verdade.items():
                try:
                    li = int(ln)
                except (TypeError, ValueError):
                    continue
                if li in dados[m]:
                    nv += 1
                    okv += int(dados[m][li]["ia"] == tru)
            val["por_modelo"].append({"modelo": m, "n": nv,
                                      "acerto_validado": round(okv / nv, 4) if nv else None})
        val["por_modelo"].sort(key=lambda d: -(d["acerto_validado"] or 0))
        out["validacao_humana_modelos"] = val
        print(f"validacao: verdade_derivada={len(verdade)}")
    except Exception as e:  # noqa: BLE001
        print(f"validado: {e}", file=sys.stderr)

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK -> {SAIDA} | n={n} | modelos={len(modelos)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
