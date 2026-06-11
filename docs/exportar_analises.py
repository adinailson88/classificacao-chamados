#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 EXPORTADOR DE ANALISES — Painel de Classificacao de Chamados
================================================================================

Este script reproduz, de forma INDEPENDENTE do painel, os calculos de cada aba
do dashboard, lendo diretamente a SUA planilha Google. Cada bloco esta comentado
explicando O QUE e calculado, COMO e calculado e COMO LER o resultado.

REQUISITOS (uma vez so):
    pip install gspread google-auth numpy
    # opcionais (liberam os blocos de estatistica e taxonomia):
    pip install scipy scikit-learn

VOCE PRECISA TER:
 1. A planilha do experimento (aba CHAMADOS_ESQUELETO_REDUZIDO + abas CLASSIF__*).
 2. Uma credencial de conta de servico Google com acesso de leitura a planilha,
    salva como arquivo JSON (ex.: credenciais_sa.json).
 3. O ID da planilha (o trecho longo da URL entre /d/ e /edit).

COMO RODAR:
    python exportar_analises.py --credenciais credenciais_sa.json --planilha SEU_ID
    # ou defina as variaveis de ambiente GOOGLE_APPLICATION_CREDENTIALS e
    # SPREADSHEET_ID e rode sem argumentos.

O script e SOMENTE-LEITURA: nao escreve nada na planilha.

AVISO METODOLOGICO (vale para todos os blocos):
 - "Concordancia com o historico" compara a IA com a categoria registrada no
   GLPI (coluna C). O historico NAO e verdade absoluta — isso NAO e acuracia.
 - "Acerto validado" so existe onde um humano conferiu (colunas M/N/P).
================================================================================
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import unicodedata
from collections import Counter, defaultdict

import numpy as np

# ------------------------------------------------------------------------------
# 0. ACESSO A PLANILHA
# ------------------------------------------------------------------------------
# Colunas da aba principal (CHAMADOS_ESQUELETO_REDUZIDO), 1-based:
#   A=ID, B=TITULO, C=CATEGORIA COMPLETA (historico GLPI), D=DESCRICAO GLPI,
#   E=TITULO O.S.M., F=DESCRICAO O.S.M., G=Classificacao IA (etapa 1),
#   H=Avaliacao (%) (confianca da IA), M=CONFERENCIA GLPI (humano avaliou C),
#   N=CONFERENCIA IA (humano avaliou G), O=Classificacao IA - 2 (reclassificacao),
#   P=CONFERENCIA IA - 2 (humano avaliou O).
# Convencao das conferencias: 'Correto' = certo; outro texto = errado; vazio = nao conferido.

ABA_PRINCIPAL = "CHAMADOS_ESQUELETO_REDUZIDO"
MODELOS = ["naive_bayes", "regressao_logistica", "linear_svc", "sgd",
           "extra_trees", "random_forest", "lstm"]


def norm(s):
    t = unicodedata.normalize("NFKD", str(s or ""))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return " ".join(t.split()).casefold()


def parse_conf(v):
    """Converte '88,7%' / 0.887 / '0.887' para float em [0,1]."""
    try:
        f = float(str(v).replace("%", "").replace(",", ".").strip())
        return f / 100.0 if f > 1 else f
    except (ValueError, TypeError):
        return 0.0


def abrir(credenciais, planilha_id):
    import gspread
    from google.oauth2.service_account import Credentials
    escopo = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    cred = Credentials.from_service_account_file(credenciais, scopes=escopo)
    return gspread.authorize(cred).open_by_key(planilha_id)


def ler_principal(sh):
    """Le a aba principal inteira (A:P) e devolve lista de dicts por linha."""
    vals = sh.worksheet(ABA_PRINCIPAL).get_values("A1:P", value_render_option="UNFORMATTED_VALUE")
    out = []
    for pos, r in enumerate(vals[1:], start=2):
        def cel(c1):  # c1 = coluna 1-based
            return str(r[c1 - 1] or "").strip() if len(r) >= c1 else ""
        out.append({
            "linha": pos, "titulo": cel(2), "historico": cel(3),
            "desc_glpi": cel(4), "tit_osm": cel(5), "desc_osm": cel(6),
            "ia": cel(7), "conf": parse_conf(cel(8)),
            "conf_glpi": cel(13), "conf_ia": cel(14),
            "reclass": cel(15), "conf_reclass": cel(16),
        })
    return [c for c in out if c["historico"] or c["ia"]]


def veredito(v):
    """'Correto' -> True, outro texto -> False, vazio -> None (nao conferido)."""
    s = str(v or "").strip()
    if not s:
        return None
    return s.casefold() == "correto"


# ==============================================================================
# ABA 1 — CLASSIFICACAO (visao geral da etapa 1)
# ==============================================================================
def aba_classificacao(chamados):
    print("\n" + "=" * 70)
    print("ABA CLASSIFICACAO — etapa 1 (modelo oficial, coluna G)")
    print("=" * 70)
    com_ia = [c for c in chamados if c["ia"] and c["historico"]]
    # CONCORDANCIA = % de chamados em que a IA (G) repete o historico (C).
    # NAO e acuracia: o historico pode estar errado.
    concorda = sum(1 for c in com_ia if c["ia"] == c["historico"])
    print(f"Chamados classificados: {len(com_ia)}")
    if com_ia:
        print(f"Concordancia IA x historico: {concorda}/{len(com_ia)} = {100*concorda/len(com_ia):.2f}%")
    # FAIXAS DE CONFIANCA: o softmax do modelo, agrupado nas faixas do painel.
    faixas = Counter()
    for c in com_ia:
        faixas[">=95%" if c["conf"] >= 0.95 else ("70-95%" if c["conf"] >= 0.70 else "<70%")] += 1
    for f, n in sorted(faixas.items()):
        print(f"  faixa {f}: {n} chamados")


# ==============================================================================
# ABA 2 — CATEGORIAS (concordancia por categoria historica)
# ==============================================================================
def aba_categorias(chamados, top=15):
    print("\n" + "=" * 70)
    print("ABA CATEGORIAS — concordancia por categoria (vs historico)")
    print("=" * 70)
    porcat = defaultdict(lambda: [0, 0])  # categoria -> [n, concorda]
    for c in chamados:
        if not (c["ia"] and c["historico"]):
            continue
        porcat[c["historico"]][0] += 1
        if c["ia"] == c["historico"]:
            porcat[c["historico"]][1] += 1
    # Ordena por volume; mostra as `top` maiores.
    for cat, (n, ok) in sorted(porcat.items(), key=lambda kv: -kv[1][0])[:top]:
        print(f"  {cat[:55]:55s} n={n:5d} concordancia={100*ok/n:6.2f}%")
    print(f"  ... ({len(porcat)} categorias no total)")


# ==============================================================================
# ABA 3 — METRICAS (calibracao da confianca, modelo oficial)
# ==============================================================================
def aba_metricas(chamados, n_bins=10):
    print("\n" + "=" * 70)
    print("ABA METRICAS — calibracao: a confianca dita corresponde ao acerto?")
    print("=" * 70)
    # ECE (Expected Calibration Error): divide a confianca em bins; em cada bin,
    # compara a confianca MEDIA com a taxa de CONCORDANCIA observada; faz a media
    # ponderada das diferencas. ECE proximo de 0 = bem calibrado (vs historico!).
    dados = [(c["conf"], 1.0 if c["ia"] == c["historico"] else 0.0)
             for c in chamados if c["ia"] and c["historico"]]
    if not dados:
        print("  sem dados.")
        return
    conf = np.array([d[0] for d in dados]); ok = np.array([d[1] for d in dados])
    ece = 0.0
    for b in range(n_bins):
        lo, hi = b / n_bins, (b + 1) / n_bins
        m = (conf >= lo) & (conf < hi) if b < n_bins - 1 else (conf >= lo) & (conf <= hi)
        if m.sum() == 0:
            continue
        gap = abs(conf[m].mean() - ok[m].mean())
        ece += (m.sum() / len(conf)) * gap
        print(f"  bin {lo:.1f}-{hi:.1f}: n={int(m.sum()):5d} conf_media={conf[m].mean():.3f} "
              f"concordancia={ok[m].mean():.3f}")
    print(f"  ECE (vs historico) = {ece:.4f}  (quanto menor, melhor calibrado)")


# ==============================================================================
# ABA 4 — MODELOS (as 7 IAs, abas CLASSIF__<modelo>)
# ==============================================================================
def aba_modelos(sh):
    print("\n" + "=" * 70)
    print("ABA MODELOS — concordancia de cada IA com o historico")
    print("=" * 70)
    # Cada aba CLASSIF__<modelo> tem a predicao OUT-OF-FOLD daquele modelo para
    # cada chamado (a IA que rotulou a linha nunca treinou nela).
    preds = {}
    for m in MODELOS:
        try:
            vals = sh.worksheet(f"CLASSIF__{m}").get_values("A:K", value_render_option="UNFORMATTED_VALUE")
        except Exception:
            continue
        d = {}
        for r in vals[1:]:
            if len(r) < 6:
                continue
            try:
                ln = int(r[1])
            except (ValueError, TypeError):
                continue
            # colunas: 3=categoria_original (historico), 4=categoria_ia, 5=confianca
            d[ln] = (str(r[3]).strip(), str(r[4]).strip(), parse_conf(r[5]))
        if d:
            preds[m] = d
            ok = sum(1 for orig, p, _ in d.values() if p == orig)
            print(f"  {m:22s} n={len(d):6d} concordancia={100*ok/len(d):6.2f}%")
    return preds


# ==============================================================================
# ABA 5 — ESTATISTICA (testes nao parametricos entre as 7 IAs)
# ==============================================================================
def aba_estatistica(preds):
    print("\n" + "=" * 70)
    print("ABA ESTATISTICA — as diferencas entre IAs sao reais ou acaso?")
    print("=" * 70)
    try:
        from scipy.stats import binomtest, friedmanchisquare
    except ImportError:
        print("  (instale scipy para este bloco: pip install scipy)")
        return
    modelos = sorted(preds)
    if len(modelos) < 2:
        print("  menos de 2 modelos com dados.")
        return
    # Linhas presentes em TODOS os modelos (mesma base de comparacao).
    comuns = set.intersection(*(set(preds[m]) for m in modelos))
    linhas = sorted(comuns)
    acertos = {m: np.array([1 if preds[m][ln][1] == preds[m][ln][0] else 0 for ln in linhas])
               for m in modelos}
    # FRIEDMAN: teste global "todas as IAs tem o mesmo desempenho?" (nao
    # parametrico, amostras pareadas). p < 0,05 => ha pelo menos uma diferente.
    try:
        st, p = friedmanchisquare(*(acertos[m] for m in modelos))
        print(f"  Friedman: chi2={st:.2f} p={p:.2e} "
              f"({'ha diferenca entre as IAs' if p < 0.05 else 'sem diferenca detectavel'})")
    except Exception as e:
        print(f"  Friedman falhou: {e}")
    # McNEMAR (exato) por par: usa apenas os casos em que UMA acerta e a outra
    # erra (pares discordantes). p < 0,05 => diferenca real entre as duas.
    print("  McNemar par a par (apenas p<0,05):")
    algum = False
    for i, a in enumerate(modelos):
        for b in modelos[i + 1:]:
            so_a = int(((acertos[a] == 1) & (acertos[b] == 0)).sum())
            so_b = int(((acertos[a] == 0) & (acertos[b] == 1)).sum())
            if so_a + so_b == 0:
                continue
            p = binomtest(min(so_a, so_b), so_a + so_b, 0.5).pvalue
            if p < 0.05:
                algum = True
                melhor = a if so_a > so_b else b
                print(f"    {a} x {b}: p={p:.4f} (melhor: {melhor})")
    if not algum:
        print("    nenhum par significativo.")


# ==============================================================================
# ABA 6 — TAXONOMIA (termos por categoria + correlacao vocabular)
# ==============================================================================
def aba_taxonomia(chamados, top_n=10, min_chamados=10):
    print("\n" + "=" * 70)
    print("ABA TAXONOMIA — vocabulario por categoria e categorias 'gemeas'")
    print("=" * 70)
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.preprocessing import normalize
    except ImportError:
        print("  (instale scikit-learn para este bloco)")
        return
    # Representacao TF-IDF do texto (titulo + descricoes) de cada chamado.
    docs, cats = [], []
    for c in chamados:
        texto = " ".join(t for t in [c["titulo"], c["desc_glpi"], c["tit_osm"], c["desc_osm"]] if t)
        if texto and c["historico"]:
            docs.append(texto); cats.append(c["historico"])
    cont = Counter(cats)
    vec = TfidfVectorizer(strip_accents="unicode", lowercase=True, ngram_range=(1, 2),
                          min_df=5, max_features=30000)
    X = vec.fit_transform(docs)
    # CENTROIDE por categoria = vetor medio TF-IDF dos chamados da categoria.
    # CORRELACAO entre categorias = cosseno entre centroides (0 = vocabularios
    # independentes; 1 = mesmo vocabulario -> candidatas a fusao/desambiguacao).
    cats_ok = [c for c, n in cont.items() if n >= min_chamados]
    idx_por_cat = defaultdict(list)
    for i, c in enumerate(cats):
        if c in cats_ok:
            idx_por_cat[c].append(i)
    cents = {c: normalize(np.asarray(X[ix].mean(axis=0))) for c, ix in idx_por_cat.items()}
    pares = []
    nomes = sorted(cents)
    for i, a in enumerate(nomes):
        for b in nomes[i + 1:]:
            pares.append((float(cents[a] @ cents[b].T), a, b))
    pares.sort(reverse=True)
    print(f"  {len(nomes)} categorias com >= {min_chamados} chamados. Pares mais correlatos:")
    for v, a, b in pares[:top_n]:
        print(f"    {v:.3f}  {a}  x  {b}")


# ==============================================================================
# ABA 7 — RECLASSIFICACAO (abas RECLASS__<modelo>)
# ==============================================================================
def aba_reclassificacao(sh):
    print("\n" + "=" * 70)
    print("ABA RECLASSIFICACAO — quantos foram reclassificados e com que ganho")
    print("=" * 70)
    # Cada aba RECLASS__<modelo> registra antes/depois por chamado. 'resultado':
    #   corrigido        = errava antes, acerta depois (+1 no ganho)
    #   prejudicado      = acertava antes, erra depois (-1 no ganho)
    #   decidido_humano  = reuso da decisao conferida (regra de memoria)
    #   sem_referencia   = historico conferido como errado e sem verdade travada
    for m in MODELOS:
        try:
            vals = sh.worksheet(f"RECLASS__{m}").get_values("A:P", value_render_option="UNFORMATTED_VALUE")
        except Exception:
            continue
        if len(vals) < 2:
            continue
        cab = [norm(c) for c in vals[0]]
        i_res = cab.index(norm("resultado")) if norm("resultado") in cab else None
        res = Counter(str(r[i_res]).strip() for r in vals[1:] if i_res is not None and len(r) > i_res)
        corr, prej = res.get("corrigido", 0), res.get("prejudicado", 0)
        print(f"  {m:22s} reclassificados={sum(res.values()):5d} corrigidos={corr} "
              f"prejudicados={prej} ganho={corr-prej} reuso_humano={res.get('decidido_humano',0)}")


# ==============================================================================
# ABA 8 — DECISAO (acerto VALIDADO pela conferencia humana)
# ==============================================================================
def aba_decisao(chamados, preds):
    print("\n" + "=" * 70)
    print("ABA DECISAO — qual IA usar (contra a verdade conferida por humano)")
    print("=" * 70)
    # VERDADE VALIDADA por chamado (regra de memoria):
    #   N='Correto'  -> a verdade e a categoria da IA (G)
    #   M='Correto'  -> a verdade e o historico (C)
    #   P='Correto'  -> a verdade e a reclassificacao (O)
    verdade = {}
    for c in chamados:
        if veredito(c["conf_ia"]) is True and c["ia"]:
            verdade[c["linha"]] = c["ia"]
        elif veredito(c["conf_glpi"]) is True and c["historico"]:
            verdade[c["linha"]] = c["historico"]
        elif veredito(c["conf_reclass"]) is True and c["reclass"]:
            verdade[c["linha"]] = c["reclass"]
    print(f"  chamados com verdade validada: {len(verdade)}")
    if not verdade or not preds:
        print("  (termine a conferencia manual nas colunas M/N para liberar este bloco)")
        return
    # ACERTO VALIDADO por modelo = % de predicoes iguais a verdade validada.
    linhas = sorted(ln for ln in verdade if all(ln in preds[m] for m in preds))
    print(f"  linhas avaliaveis (verdade + predicao de todos os modelos): {len(linhas)}")
    ranking = []
    for m in sorted(preds):
        oks = [1 if preds[m][ln][1] == verdade[ln] else 0 for ln in linhas]
        if oks:
            ranking.append((float(np.mean(oks)), m))
    ranking.sort(reverse=True)
    for acc, m in ranking:
        print(f"    {m:22s} acerto_validado={100*acc:6.2f}% (n={len(linhas)})")
    # ENSEMBLE maioria simples: cada IA vota; vence a categoria mais votada.
    # Compare com a melhor IA para decidir se combinar compensa.
    if len(linhas) >= 10:
        ok_ens = 0
        for ln in linhas:
            votos = Counter(preds[m][ln][1] for m in preds)
            if votos.most_common(1)[0][0] == verdade[ln]:
                ok_ens += 1
        print(f"    {'MAIORIA SIMPLES (7 IAs)':22s} acerto_validado={100*ok_ens/len(linhas):6.2f}%")


# ------------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(description="Reproduz os calculos do painel a partir da planilha.")
    p.add_argument("--credenciais", default=os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "credenciais_sa.json"),
                   help="JSON da conta de servico (leitura).")
    p.add_argument("--planilha", default=os.environ.get("SPREADSHEET_ID", ""),
                   help="ID da planilha (URL entre /d/ e /edit).")
    args = p.parse_args()
    if not args.planilha:
        print("Informe --planilha SEU_ID (ou defina SPREADSHEET_ID).", file=sys.stderr)
        return 2
    try:
        sh = abrir(args.credenciais, args.planilha)
        chamados = ler_principal(sh)
    except Exception as e:
        print(f"Falha ao abrir a planilha: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    print(f"Planilha aberta. Chamados na aba principal: {len(chamados)}")

    aba_classificacao(chamados)
    aba_categorias(chamados)
    aba_metricas(chamados)
    preds = aba_modelos(sh)
    aba_estatistica(preds)
    aba_taxonomia(chamados)
    aba_reclassificacao(sh)
    aba_decisao(chamados, preds)
    print("\nFim. Todos os numeros acima foram calculados agora, direto da sua planilha.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
