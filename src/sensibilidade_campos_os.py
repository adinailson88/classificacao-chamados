#!/usr/bin/env python3
"""Sensibilidade do classificador e do controle de risco aos campos da ordem de servico.

Pedido dos pareceres da RAP (06/11/2026): os campos TITULO O.S.M. e DESCRICAO O.S.M.
sao redigidos pelos servidores depois da analise do chamado e nao existem na
abertura. Este script compara, nas mesmas particoes, o modelo treinado com os
quatro campos e o modelo treinado so com TITULO e DESCRICAO GLPI.

Ferramenta READ-ONLY: le a aba principal (textos) e a aba do corte de dados do
artigo (referencia revisada, categoria historica, data, unidade) e grava apenas
numeros agregados em docs/dados/sensibilidade_campos_os.json. Nao publica
titulos, descricoes nem IDs.

Desenho
- Grupos textuais pelo texto normalizado de TITULO + DESCRICAO GLPI. Como
  textos identicos nos quatro campos tem tambem os dois primeiros identicos,
  esses grupos sao validos para as duas condicoes e as particoes sao as mesmas.
- Categorias com menos de 5 grupos distintos ficam fora; a validacao cruzada
  usa StratifiedGroupKFold (5 dobras, semente 42).
- Modelo: TF-IDF de palavras (1-2) e de caracteres (3-5) com LinearSVC de pesos
  balanceados, parametros padrao (o mesmo do kit de replicacao). Nao e o
  tfidf_embedding do artigo; o que interessa aqui e a diferenca entre condicoes.
- Controle de risco: em cada cenario, 20% dos grupos de treino formam a
  calibracao; 20 niveis de cobertura definidos pelos escores da calibracao;
  Learn-then-Test com teste binomial exato ao nivel delta/20 (delta = 0,05);
  limiar convencional = maior cobertura com erro de calibracao <= alvo; com
  margem = ajustado a 5% e avaliado contra 10%. O escore e a maior funcao de
  decisao; a calibracao isotonica do artigo preserva a ordem e nao altera os
  limiares por cobertura.
- 14 cenarios como no artigo: particao aleatoria por grupo, prospectivo,
  origem movel 2022 a 2026, Reitoria para cada um dos tres campi de maior
  volume e uma unidade fora (quatro unidades).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import beta, binom
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import f1_score
from sklearn.model_selection import GroupShuffleSplit, StratifiedGroupKFold
from sklearn.pipeline import FeatureUnion, make_pipeline
from sklearn.svm import LinearSVC

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planilha as pl  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "docs" / "dados" / "sensibilidade_campos_os.json"
SEMENTE = 42
DELTA = 0.05
NIVEIS = 20
UNIDADES = ["Reitoria", "Campus Sosígenes Costa", "Campus Jorge Amado", "Campus Paulo Freire"]


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s.lower()).strip()


def novo_modelo():
    texto = FeatureUnion([
        ("palavras", TfidfVectorizer(ngram_range=(1, 2), strip_accents="unicode",
                                     sublinear_tf=True, max_features=30000)),
        ("caracteres", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), strip_accents="unicode",
                                       sublinear_tf=True, min_df=2, max_features=60000)),
    ])
    return make_pipeline(texto, LinearSVC(class_weight="balanced"))


def prever(modelo, textos):
    d = modelo.decision_function(textos)
    classes = modelo.classes_
    return classes[d.argmax(axis=1)], d.max(axis=1)


def cp(k, n):
    if n == 0:
        return (None, None)
    lo = beta.ppf(0.025, k, n - k + 1) if k else 0.0
    hi = beta.ppf(0.975, k + 1, n - k) if k < n else 1.0
    return (round(float(lo), 4), round(float(hi), 4))


def ler_base(config, credenciais, aba_corte):
    sh = pl.abrir_planilha(pl.id_planilha(config), credenciais)
    principal = sh.worksheet(config["aba_principal"]).get_all_values()
    cab = [pl.normalizar_cabecalho(c) for c in principal[0]]

    def col(*nomes):
        for n in nomes:
            n = pl.normalizar_cabecalho(n)
            if n in cab:
                return cab.index(n)
        raise SystemExit(f"coluna ausente: {nomes}")

    c_id, c_tit, c_desc = col("ID Chamado"), col("TÍTULO", "TITULO"), col("DESCRIÇÃO GLPI", "DESCRICAO GLPI")
    c_tos, c_dos = col("TÍTULO O.S.M.", "TITULO O.S.M."), col("DESCRIÇÃO O.S.M.", "DESCRICAO O.S.M.")
    textos = {}
    for l in principal[1:]:
        l = l + [""] * (len(cab) - len(l))
        i = str(l[c_id]).strip()
        if i:
            textos[i] = (l[c_tit], l[c_desc], l[c_tos], l[c_dos])
    corte = sh.worksheet(aba_corte).get_all_values()
    cc = [str(c).strip() for c in corte[0]]
    ix = {n: cc.index(n) for n in ("id_chamado", "categoria_historica", "referencia_humana",
                                     "data_abertura", "campus", "periodo")}
    base = []
    for l in corte[1:]:
        i = str(l[ix["id_chamado"]]).strip()
        if not i or i not in textos:
            continue
        tit, desc, tos, dos = textos[i]
        quatro = " ".join(str(x) for x in (tit, desc, tos, dos)).strip()
        if not quatro or not l[ix["referencia_humana"]].strip():
            continue
        base.append({
            "dois": f"{tit} {desc}".strip(), "quatro": quatro,
            "tem_os": bool(str(tos).strip() or str(dos).strip()),
            "grupo": norm(f"{tit} {desc}"),
            "ref": l[ix["referencia_humana"]].strip(), "hist": l[ix["categoria_historica"]].strip(),
            "ano": int(str(l[ix["data_abertura"]])[:4]), "campus": l[ix["campus"]].strip(),
            "periodo": l[ix["periodo"]].strip(), "folha": norm(l[ix["referencia_humana"]].split(">")[-1]),
            "os_norm": norm(f"{tos} {dos}"), "dois_norm": norm(f"{tit} {desc}"),
        })
    return base


def filtrar_categorias(base):
    grupos = defaultdict(set)
    for r in base:
        grupos[r["ref"]].add(r["grupo"])
    manter = {c for c, g in grupos.items() if len(g) >= 5}
    return [r for r in base if r["ref"] in manter], sorted(set(grupos) - manter)


def dobras(base):
    y = np.array([r["ref"] for r in base])
    g = np.array([r["grupo"] for r in base])
    skf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEMENTE)
    return list(skf.split(np.zeros(len(base)), y, g))


def validacao_cruzada(base, campo, folds):
    y = np.array([r["ref"] for r in base])
    hist = np.array([r["hist"] for r in base])
    x = np.array([r[campo] for r in base], dtype=object)
    pred = np.empty(len(base), dtype=object)
    for tr, te in folds:
        m = novo_modelo().fit(x[tr], y[tr])
        pred[te], _ = prever(m, x[te])
    acc = float((pred == y).mean())
    div = pred != hist
    corr = int((div & (pred == y)).sum())
    prej = int((div & (hist == y)).sum())
    return {"acuracia": round(acc, 4), "macro_f1": round(float(f1_score(y, pred, average="macro")), 4),
            "divergencias_do_historico": int(div.sum()), "corrigidos_sob_auditoria": corr,
            "prejudicados_sob_auditoria": prej, "ganho_sob_auditoria": corr - prej}, pred


def limiar_ltt(esc, acerto, alvo):
    ordem = np.argsort(-esc)
    e, a = esc[ordem], acerto[ordem]
    n = len(e)
    escolhido = None
    for j in range(1, NIVEIS + 1):
        k = max(1, int(round(n * j / NIVEIS)))
        erros = int((1 - a[:k]).sum())
        p = binom.cdf(erros, k, alvo)
        if p <= DELTA / NIVEIS:
            escolhido = e[k - 1]
    return escolhido


def limiar_convencional(esc, acerto, alvo):
    ordem = np.argsort(-esc)
    e, a = esc[ordem], acerto[ordem]
    erro_acum = np.cumsum(1 - a) / np.arange(1, len(a) + 1)
    ok = np.where(erro_acum <= alvo)[0]
    return e[ok.max()] if len(ok) else None


def avaliar(lim, esc, acerto):
    if lim is None:
        return {"limiar": False, "cobertura": 0.0, "erro": None, "ic95_erro": [None, None]}
    m = esc >= lim
    n, k = int(m.sum()), int((1 - acerto[m]).sum())
    return {"limiar": True, "cobertura": round(n / len(esc), 4),
            "erro": round(k / n, 4) if n else None, "ic95_erro": list(cp(k, n)), "n_automatizado": n}


def cenario(base, campo, idx_tr, idx_te):
    if len(idx_te) == 0 or len(idx_tr) == 0:
        return None
    y = np.array([r["ref"] for r in base])
    g = np.array([r["grupo"] for r in base])
    x = np.array([r[campo] for r in base], dtype=object)
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEMENTE)
    fit_rel, cal_rel = next(gss.split(idx_tr, groups=g[idx_tr]))
    fit, cal = idx_tr[fit_rel], idx_tr[cal_rel]
    m = novo_modelo().fit(x[fit], y[fit])
    pc, ec = prever(m, x[cal])
    pt, et = prever(m, x[idx_te])
    ac, at = (pc == y[cal]).astype(int), (pt == y[idx_te]).astype(int)
    out = {"n_treino": int(len(fit)), "n_calibracao": int(len(cal)), "n_teste": int(len(idx_te)),
           "acuracia_teste": round(float(at.mean()), 4)}
    for alvo in (0.10, 0.05):
        out[f"ltt_{int(alvo * 100)}"] = avaliar(limiar_ltt(ec, ac, alvo), et, at)
    out["convencional_10"] = avaliar(limiar_convencional(ec, ac, 0.10), et, at)
    out["convencional_margem_10"] = avaliar(limiar_convencional(ec, ac, 0.05), et, at)
    return out


def cenarios(base, folds):
    n = np.arange(len(base))
    ano = np.array([r["ano"] for r in base])
    campus = np.array([r["campus"] for r in base])
    periodo = np.array([r["periodo"] for r in base])
    tr0, te0 = folds[0]
    cen = {"aleatorio_por_grupo": (tr0, te0),
           "prospectivo": (n[periodo == "historico"], n[periodo == "prospectivo"])}
    for a in range(2022, 2027):
        cen[f"origem_movel_{a}"] = (n[ano < a], n[ano == a])
    for c in UNIDADES[1:]:
        cen[f"reitoria_para_{norm(c).replace(' ', '_')}"] = (n[campus == "Reitoria"], n[campus == c])
    for c in UNIDADES:
        cen[f"fora_{norm(c).replace(' ', '_')}"] = (n[campus != c], n[campus == c])
    return cen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--credenciais")
    ap.add_argument("--aba-corte", default="CORTE_B_20261030")
    args = ap.parse_args()
    t0 = time.time()
    config = json.loads((RAIZ / "config_experimento.json").read_text(encoding="utf-8"))
    base, excluidas = filtrar_categorias(ler_base(config, args.credenciais, args.aba_corte))
    print(f"chamados {len(base)}; categorias {len({r['ref'] for r in base})}; excluidas {len(excluidas)}", flush=True)
    folds = dobras(base)
    tem_os = sum(r["tem_os"] for r in base)
    folha_os = sum(1 for r in base if r["folha"] and r["folha"] in r["os_norm"])
    folha_dois = sum(1 for r in base if r["folha"] and r["folha"] in r["dois_norm"])
    res = {
        "gerado_em": time.strftime("%Y-%m-%d %H:%M"),
        "script_origem": "src/sensibilidade_campos_os.py",
        "corpus": {"chamados": len(base), "categorias": len({r["ref"] for r in base}),
                   "categorias_excluidas": len(excluidas), "grupos_textuais": len({r["grupo"] for r in base}),
                   "com_algum_campo_de_os": tem_os,
                   "nome_da_categoria_no_texto_da_os": folha_os,
                   "nome_da_categoria_em_titulo_ou_descricao": folha_dois},
        "validacao_cruzada": {}, "controle_de_risco": {},
    }
    preds = {}
    for campo in ("quatro", "dois"):
        res["validacao_cruzada"][campo], preds[campo] = validacao_cruzada(base, campo, folds)
        print(campo, res["validacao_cruzada"][campo], f"{time.time() - t0:.0f}s", flush=True)
    y = np.array([r["ref"] for r in base])
    tos = np.array([r["tem_os"] for r in base])
    res["validacao_cruzada"]["por_presenca_de_os"] = {
        nome: {campo: round(float((preds[campo][m] == y[m]).mean()), 4) for campo in preds} | {"n": int(m.sum())}
        for nome, m in (("com_os", tos), ("sem_os", ~tos))}
    for nome, (tr, te) in cenarios(base, folds).items():
        res["controle_de_risco"][nome] = {campo: cenario(base, campo, np.asarray(tr), np.asarray(te))
                                          for campo in ("quatro", "dois")}
        print(nome, json.dumps(res["controle_de_risco"][nome], ensure_ascii=False), f"{time.time() - t0:.0f}s",
              flush=True)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"gravado {SAIDA} em {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
