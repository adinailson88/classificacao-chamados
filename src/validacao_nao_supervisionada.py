#!/usr/bin/env python3
"""Validação não supervisionada para priorizar a Classificação IA - 2.

Este script não decide a categoria correta e não grava Classificação IA - 2.
Ele calcula sinais semânticos e de consenso para orientar revisão humana e
revalidação robusta:

- distância do chamado ao centróide da categoria histórica;
- categoria semanticamente mais próxima;
- margem semântica;
- outlier por percentil dentro da própria categoria;
- consenso das abas CLASSIF__<modelo>, quando existirem;
- prioridade de revisão.

Sem --aplicar = dry-run. Com --aplicar, grava a aba privada
VALIDACAO_NAO_SUPERVISIONADA. Não publica texto livre de chamados.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planilha as pl  # noqa: E402
from tempo import agora_bahia  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
ABA_SAIDA = "VALIDACAO_NAO_SUPERVISIONADA"
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


def carregar_chamados(ws, range_a1: str) -> list[dict[str, Any]]:
    valores = pl.ler_valores(ws, range_a1)
    cab = valores[0] if valores else []
    idx = {norm(n): i for i, n in enumerate(cab)}

    campos_texto = [
        "TITULO",
        "DESCRICAO GLPI",
        "TITULO O.S.M.",
        "DESCRICAO O.S.M.",
    ]
    i_id = idx.get(norm("ID Chamado"))
    i_cat = idx.get(norm("CATEGORIA COMPLETA"))
    i_g = idx.get(norm("Classificacao IA"))
    i_h = idx.get(norm("Avaliacao (%)"))

    chamados: list[dict[str, Any]] = []
    for pos, linha in enumerate(valores[1:], start=2):
        categoria = cel(linha, i_cat)
        partes = [cel(linha, idx.get(norm(c))) for c in campos_texto]
        texto = "\n".join(p for p in partes if p)
        if not categoria or not texto:
            continue
        chamados.append({
            "linha": pos,
            "id": cel(linha, i_id),
            "categoria": categoria,
            "texto": texto,
            "categoria_g": cel(linha, i_g),
            "conf_g": parse_float(cel(linha, i_h)),
        })
    return chamados


def carregar_votos_modelos(sh, config: dict[str, Any], modelos: list[str]) -> dict[int, list[dict[str, Any]]]:
    mm = config.get("multimodelo", {})
    template = mm.get("aba_classificacao", "CLASSIF__{modelo}")
    votos: dict[int, list[dict[str, Any]]] = defaultdict(list)

    for modelo in modelos:
        aba = template.replace("{modelo}", modelo)
        try:
            vals = sh.worksheet(aba).get_values("A:K", value_render_option="UNFORMATTED_VALUE")
        except Exception:  # noqa: BLE001
            continue
        if not vals:
            continue
        cab = vals[0]
        idx = {norm(n): i for i, n in enumerate(cab)}
        i_linha = idx.get(norm("linha_planilha"))
        i_pred = idx.get(norm("categoria_ia"))
        i_conf = idx.get(norm("confianca"))
        if i_linha is None or i_pred is None:
            continue
        for r in vals[1:]:
            try:
                linha = int(cel(r, i_linha))
            except (ValueError, TypeError):
                continue
            pred = cel(r, i_pred)
            if not pred:
                continue
            votos[linha].append({
                "modelo": modelo,
                "pred": pred,
                "conf": parse_float(cel(r, i_conf)),
            })
    return votos


def resumo_votos(votos: list[dict[str, Any]], categoria_historica: str) -> dict[str, Any]:
    if not votos:
        return {
            "categoria_majoritaria": "",
            "qtd_modelos_concordantes": 0,
            "n_categorias_sugeridas": 0,
            "entropia_votos": 0.0,
            "consenso_contra_historico": "NAO",
        }
    cont = Counter(v["pred"] for v in votos if v.get("pred"))
    categoria_majoritaria, qtd = cont.most_common(1)[0]
    total = sum(cont.values())
    entropia = 0.0
    for n in cont.values():
        p = n / total
        entropia -= p * math.log(p, 2)
    return {
        "categoria_majoritaria": categoria_majoritaria,
        "qtd_modelos_concordantes": qtd,
        "n_categorias_sugeridas": len(cont),
        "entropia_votos": round(entropia, 4),
        "consenso_contra_historico": "SIM" if categoria_majoritaria != categoria_historica and qtd >= 5 else "NAO",
    }


def calcular_semantica(chamados: list[dict[str, Any]], n_componentes: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score
    from sklearn.preprocessing import normalize

    textos = [c["texto"] for c in chamados]
    categorias = [c["categoria"] for c in chamados]

    vec = TfidfVectorizer(strip_accents="unicode", lowercase=True, ngram_range=(1, 2), min_df=1, max_features=30000)
    X = vec.fit_transform(textos)
    max_comp = max(2, min(n_componentes, X.shape[0] - 1, X.shape[1] - 1))
    if max_comp >= 2:
        Xr = TruncatedSVD(n_components=max_comp, random_state=42).fit_transform(X)
    else:
        Xr = X.toarray()
    Xr = normalize(Xr)

    por_cat: dict[str, list[int]] = defaultdict(list)
    for i, cat in enumerate(categorias):
        por_cat[cat].append(i)

    centroides = {}
    for cat, idxs in por_cat.items():
        centroides[cat] = normalize(np.mean(Xr[idxs], axis=0, keepdims=True))[0]

    distancias_proprias: dict[str, list[float]] = defaultdict(list)
    linhas = []
    for i, c in enumerate(chamados):
        cat = c["categoria"]
        x = Xr[i]
        dist_propria = float(1 - np.dot(x, centroides[cat]))
        distancias_proprias[cat].append(dist_propria)

    limiares = {
        cat: float(np.percentile(vals, 90)) if vals else 0.0
        for cat, vals in distancias_proprias.items()
    }

    for i, c in enumerate(chamados):
        x = Xr[i]
        cat_hist = c["categoria"]
        dist_hist = float(1 - np.dot(x, centroides[cat_hist]))
        melhor_cat = cat_hist
        melhor_dist = dist_hist
        for cat, centro in centroides.items():
            d = float(1 - np.dot(x, centro))
            if d < melhor_dist:
                melhor_dist = d
                melhor_cat = cat
        margem = dist_hist - melhor_dist
        outlier = dist_hist >= limiares.get(cat_hist, 0.0) and len(por_cat[cat_hist]) >= 5
        linhas.append({
            "linha": c["linha"],
            "id": c["id"],
            "categoria_historica": cat_hist,
            "distancia_categoria_historica": round(dist_hist, 6),
            "categoria_semantica_mais_proxima": melhor_cat,
            "distancia_categoria_mais_proxima": round(melhor_dist, 6),
            "margem_semantica": round(margem, 6),
            "score_outlier": round(dist_hist, 6),
            "outlier_semantico": "SIM" if outlier else "NAO",
        })

    metricas: dict[str, Any] = {
        "n_chamados": len(chamados),
        "n_categorias": len(por_cat),
        "representacao": f"tfidf_svd_{Xr.shape[1]}",
        "silhouette": None,
        "davies_bouldin": None,
        "calinski_harabasz": None,
    }
    labels = np.array(categorias)
    if len(set(categorias)) >= 2 and len(chamados) > len(set(categorias)):
        try:
            metricas["silhouette"] = round(float(silhouette_score(Xr, labels)), 6)
        except Exception:  # noqa: BLE001
            pass
        try:
            metricas["davies_bouldin"] = round(float(davies_bouldin_score(Xr, labels)), 6)
        except Exception:  # noqa: BLE001
            pass
        try:
            metricas["calinski_harabasz"] = round(float(calinski_harabasz_score(Xr, labels)), 6)
        except Exception:  # noqa: BLE001
            pass

    return linhas, metricas


def prioridade(item: dict[str, Any], votos: dict[str, Any]) -> tuple[str, str]:
    motivos = []
    if item["outlier_semantico"] == "SIM":
        motivos.append("outlier na categoria histórica")
    if item["categoria_semantica_mais_proxima"] != item["categoria_historica"] and item["margem_semantica"] > 0.05:
        motivos.append("outra categoria semanticamente mais próxima")
    if votos["consenso_contra_historico"] == "SIM":
        motivos.append("consenso forte dos modelos contra histórico")
    if votos["qtd_modelos_concordantes"] >= 6 and votos["categoria_majoritaria"] != item["categoria_historica"]:
        return "Alta", " + ".join(motivos or ["consenso forte contra histórico"])
    if len(motivos) >= 2:
        return "Alta", " + ".join(motivos)
    if motivos:
        return "Media", " + ".join(motivos)
    return "Baixa", "sem sinal forte"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validação não supervisionada para priorizar Classificação IA - 2.")
    p.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    p.add_argument("--credenciais", default=None)
    p.add_argument("--n-componentes", type=int, default=100)
    p.add_argument("--aplicar", action="store_true", help="Grava abas privadas na planilha.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    config = carregar_config(args.config)
    modelos = list(config.get("multimodelo", {}).get("modelos_leves", [])) + list(config.get("multimodelo", {}).get("modelos_pesados", []))
    gerado = agora_bahia()

    try:
        sh = pl.abrir_planilha(pl.id_planilha(config), args.credenciais)
        ws = sh.worksheet(config["aba_principal"])
        chamados = carregar_chamados(ws, "A:P")
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001
        print(f"Falha ao acessar planilha: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    if len(chamados) < 2:
        print("Informação insuficiente para verificar.")
        return 1

    semantica, metricas = calcular_semantica(chamados, args.n_componentes)
    votos_modelos = carregar_votos_modelos(sh, config, modelos)

    linhas = []
    cont_prioridade = Counter()
    for item in semantica:
        rv = resumo_votos(votos_modelos.get(int(item["linha"]), []), item["categoria_historica"])
        pr, motivo = prioridade(item, rv)
        cont_prioridade[pr] += 1
        linhas.append([
            item["linha"],
            item["id"],
            item["categoria_historica"],
            item["distancia_categoria_historica"],
            item["categoria_semantica_mais_proxima"],
            item["distancia_categoria_mais_proxima"],
            item["margem_semantica"],
            item["score_outlier"],
            item["outlier_semantico"],
            rv["categoria_majoritaria"],
            rv["qtd_modelos_concordantes"],
            rv["n_categorias_sugeridas"],
            rv["entropia_votos"],
            rv["consenso_contra_historico"],
            pr,
            motivo,
            gerado,
        ])

    linhas.sort(key=lambda r: ({"Alta": 0, "Media": 1, "Baixa": 2}.get(r[14], 9), -float(r[6]), int(r[0])))

    cab = [
        "linha", "id_chamado", "categoria_historica", "distancia_categoria_historica",
        "categoria_semantica_mais_proxima", "distancia_categoria_mais_proxima", "margem_semantica",
        "score_outlier", "outlier_semantico", "categoria_majoritaria_modelos",
        "qtd_modelos_concordantes", "n_categorias_sugeridas", "entropia_votos",
        "consenso_contra_historico", "prioridade_revisao", "motivo_prioridade", "data_execucao",
    ]

    print(json.dumps({
        "gerado_em": gerado,
        "metricas": metricas,
        "prioridades": dict(cont_prioridade),
        "linhas": len(linhas),
        "modo": "aplicar" if args.aplicar else "dry-run",
    }, ensure_ascii=False, indent=2))

    if not args.aplicar:
        print("modo=dry-run (nada gravado na planilha).")
        return 0

    pl.escrever_aba(sh, ABA_SAIDA, cab, linhas)
    pl.append_aba(
        sh,
        ABA_CONTROLE,
        ["data_execucao", "etapa", "status", "qtd_candidatos", "qtd_processados", "modelo_usado", "aplicou_na_coluna_O", "observacao_tecnica"],
        [[gerado, "1-validacao-nao-supervisionada", "OK", len(linhas), len(linhas), metricas["representacao"], "NAO", json.dumps(dict(cont_prioridade), ensure_ascii=False)]],
    )
    print(f"OK: aba {ABA_SAIDA} gravada com {len(linhas)} linhas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
