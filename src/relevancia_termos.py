#!/usr/bin/env python3
"""Termos característicos por categoria + mapa de correlação entre categorias.

Responde a duas perguntas de pesquisa, tratando o vocabulário como sinal
exploratório (NÃO como validação de acurácia):

1. **Quais palavras a IA/o texto associam a cada categoria?**
   Ex.: para uma categoria de hidráulica, termos como `agua`, `vazamento`,
   `torneira`, `sanitario`. Usa duas leituras complementares:
   - `peso_tfidf`: termo mais "pesado" no centróide TF-IDF da categoria
     (frequente E discriminante dentro da categoria);
   - `log_odds_z`: razão de chances log com prior de Dirichlet informativo
     (Monroe, Colaresi & Quinn, 2008) — mede o quanto o termo é
     *característico* da categoria frente a todas as outras, com z-score robusto
     para termos raros. É a leitura recomendada para "palavras-chave da categoria".

2. **Quão próximas são as categorias entre si?** (o "mapa de correlação")
   Similaridade do cosseno entre os centróides TF-IDF de cada par de categorias.
   Análogo a um mapa de calor de geoprocessamento: célula clara/quente quando a
   similaridade tende a 1 (categorias com vocabulário sobreposto, candidatas a
   confusão/fusão na taxonomia); escura quando tende a 0 (bem separadas).

PREMISSAS METODOLÓGICAS
- Esta rotina é EXPLORATÓRIA / de triagem de taxonomia. Ela não decide categoria,
  não grava `Classificacao IA`, não toca em `CATEGORIA COMPLETA` (histórico) e não
  é métrica de acurácia validada.
- Os termos são AGREGADOS sobre todo o corpus (não é texto de um chamado). Ainda
  assim, para não expor tokens identificáveis (nomes/matrículas que apareçam pouco),
  aplica-se `--min-df` (default 5) e descartam-se tokens puramente numéricos.
- Sem `--aplicar` = dry-run (só calcula e grava os JSON agregados em docs/dados/).
  Com `--aplicar`, grava também as abas privadas RELEVANCIA_TERMOS e
  CORRELACAO_CATEGORIAS na planilha. Não sobrescreve dado bruto.

Saídas (sempre geradas, agregadas e sanitizadas):
- docs/dados/termos_relevantes.json
- docs/dados/correlacao_categorias.json
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planilha as pl  # noqa: E402
from tempo import agora_bahia  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
SAIDA = RAIZ / "docs" / "dados"
ABA_TERMOS = "RELEVANCIA_TERMOS"
ABA_CORRELACAO = "CORRELACAO_CATEGORIAS"

# Stopwords PT-BR compactas + ruído de chamado/OSM. sklearn não traz PT nativo.
STOPWORDS_PT = {
    "a", "ao", "aos", "as", "ate", "com", "como", "da", "das", "de", "dela", "dele",
    "deles", "depois", "do", "dos", "e", "ela", "elas", "ele", "eles", "em", "entre",
    "era", "essa", "essas", "esse", "esses", "esta", "estas", "este", "estes", "eu",
    "foi", "fomos", "for", "foram", "isso", "isto", "ja", "la", "lhe", "lhes", "mais",
    "mas", "me", "mesmo", "meu", "meus", "minha", "minhas", "muito", "na", "nas", "nao",
    "nem", "no", "nos", "nossa", "nossas", "nosso", "nossos", "num", "numa", "o", "os",
    "ou", "para", "pela", "pelas", "pelo", "pelos", "por", "qual", "quando", "que",
    "quem", "se", "sem", "ser", "seu", "seus", "so", "sob", "sobre", "sua", "suas",
    "tambem", "te", "tem", "tendo", "ter", "teu", "teus", "tua", "tuas", "um", "uma",
    "umas", "uns", "voce", "voces", "ja", "pra", "pro", "ainda", "apos", "cada", "onde",
    # ruído frequente em chamados/OSM que não ajuda a caracterizar a categoria
    "favor", "solicito", "solicitacao", "chamado", "os", "osm", "predio", "bloco",
    "sala", "andar", "campus", "setor", "local", "ufsb", "servico", "necessario",
    "verificar", "realizar", "providencia", "providencias",
}


def norm(s: Any) -> str:
    t = unicodedata.normalize("NFKD", str(s or ""))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return " ".join(t.split()).casefold()


def cel(linha: list[Any], idx: int | None) -> str:
    return str(linha[idx] or "").strip() if idx is not None and idx < len(linha) else ""


def carregar_config(caminho: Path) -> dict[str, Any]:
    with caminho.open("r", encoding="utf-8") as f:
        return json.load(f)


def carregar_chamados(ws, range_a1: str) -> list[dict[str, Any]]:
    """Lê (linha, categoria histórica, texto agregado) — mesma convenção da
    validação não supervisionada. Ignora linhas sem categoria ou sem texto."""
    valores = pl.ler_valores(ws, range_a1)
    cab = valores[0] if valores else []
    idx = {norm(n): i for i, n in enumerate(cab)}

    campos_texto = ["TITULO", "DESCRICAO GLPI", "TITULO O.S.M.", "DESCRICAO O.S.M."]
    i_cat = idx.get(norm("CATEGORIA COMPLETA"))

    chamados: list[dict[str, Any]] = []
    for pos, linha in enumerate(valores[1:], start=2):
        categoria = cel(linha, i_cat)
        partes = [cel(linha, idx.get(norm(c))) for c in campos_texto]
        texto = "\n".join(p for p in partes if p)
        if not categoria or not texto:
            continue
        chamados.append({"linha": pos, "categoria": categoria, "texto": texto})
    return chamados


def _token_valido(tok: str) -> bool:
    """Descarta números puros e tokens muito curtos (ruído/identificável)."""
    t = tok.replace(" ", "")
    if len(t) < 3:
        return False
    if any(ch.isdigit() for ch in t):
        return False
    return True


def calcular(chamados: list[dict[str, Any]], top_n: int, min_df: int,
             min_chamados_categoria: int) -> dict[str, Any]:
    """Núcleo: termos característicos por categoria + matriz de correlação."""
    from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
    from sklearn.preprocessing import normalize

    textos = [c["texto"] for c in chamados]
    categorias = [c["categoria"] for c in chamados]

    por_cat: dict[str, list[int]] = defaultdict(list)
    for i, cat in enumerate(categorias):
        por_cat[cat].append(i)
    # Só categorias com massa suficiente para um sinal estável.
    cats = sorted(c for c, idxs in por_cat.items() if len(idxs) >= min_chamados_categoria)

    stop = sorted(STOPWORDS_PT)

    # --- (1a) Centróides TF-IDF: peso por termo e matriz de correlação ---
    tfidf = TfidfVectorizer(strip_accents="unicode", lowercase=True, ngram_range=(1, 2),
                            min_df=min_df, max_features=30000, stop_words=stop)
    Xtf = tfidf.fit_transform(textos)
    vocab_tf = np.array(tfidf.get_feature_names_out())
    centroides = {}
    for cat in cats:
        centroides[cat] = np.asarray(Xtf[por_cat[cat]].mean(axis=0)).ravel()

    # --- (1b) Log-odds com prior Dirichlet informativo (Monroe et al. 2008) ---
    contagem = CountVectorizer(strip_accents="unicode", lowercase=True, ngram_range=(1, 2),
                               min_df=min_df, max_features=30000, stop_words=stop)
    Xc = contagem.fit_transform(textos)
    vocab_ct = np.array(contagem.get_feature_names_out())
    total_por_termo = np.asarray(Xc.sum(axis=0)).ravel().astype(float)  # y_.w
    n_total = float(total_por_termo.sum())                              # n_.
    a0 = 1000.0                                                         # massa do prior
    alfa = a0 * (total_por_termo / max(n_total, 1.0))                   # a_w
    soma_alfa = float(alfa.sum())

    termos_por_categoria: dict[str, Any] = {}
    for cat in cats:
        y_cw = np.asarray(Xc[por_cat[cat]].sum(axis=0)).ravel().astype(float)
        n_c = float(y_cw.sum())
        y_rest = total_por_termo - y_cw
        n_rest = n_total - n_c
        # log-odds-ratio com prior + variância → z-score
        num = (y_cw + alfa) / (n_c + soma_alfa - y_cw - alfa)
        den = (y_rest + alfa) / (n_rest + soma_alfa - y_rest - alfa)
        with np.errstate(divide="ignore", invalid="ignore"):
            delta = np.log(num) - np.log(den)
            var = 1.0 / (y_cw + alfa) + 1.0 / (y_rest + alfa)
            z = delta / np.sqrt(var)
        z = np.nan_to_num(z, nan=-1e9, posinf=-1e9, neginf=-1e9)

        # ranking log-odds (característico vs resto), filtrando tokens inválidos
        ordem = np.argsort(z)[::-1]
        top_logodds = []
        for j in ordem:
            termo = str(vocab_ct[j])
            if not _token_valido(termo) or y_cw[j] < min_df:
                continue
            top_logodds.append({"termo": termo, "z": round(float(z[j]), 3),
                                 "freq": int(y_cw[j])})
            if len(top_logodds) >= top_n:
                break

        # ranking por peso TF-IDF no centróide (frequente E discriminante)
        cen = centroides[cat]
        ordem_tf = np.argsort(cen)[::-1]
        top_tfidf = []
        for j in ordem_tf:
            termo = str(vocab_tf[j])
            if not _token_valido(termo) or cen[j] <= 0:
                continue
            top_tfidf.append({"termo": termo, "peso": round(float(cen[j]), 4)})
            if len(top_tfidf) >= top_n:
                break

        termos_por_categoria[cat] = {
            "n_chamados": len(por_cat[cat]),
            "top_log_odds": top_logodds,
            "top_tfidf": top_tfidf,
        }

    # --- (2) Matriz de correlação (cosseno entre centróides) ---
    M = np.vstack([centroides[c] for c in cats]) if cats else np.zeros((0, 0))
    Mn = normalize(M) if M.size else M
    sim = (Mn @ Mn.T) if M.size else np.zeros((0, 0))
    matriz = [[round(float(sim[i, j]), 4) for j in range(len(cats))] for i in range(len(cats))]

    # pares mais semanticamente próximos (fora da diagonal) — candidatos a confusão
    pares = []
    for i in range(len(cats)):
        for j in range(i + 1, len(cats)):
            pares.append({"categoria_a": cats[i], "categoria_b": cats[j],
                          "similaridade": round(float(sim[i, j]), 4)})
    pares.sort(key=lambda p: p["similaridade"], reverse=True)

    return {
        "categorias": cats,
        "termos_por_categoria": termos_por_categoria,
        "matriz_correlacao": matriz,
        "pares_mais_proximos": pares[:50],
        "parametros": {"top_n": top_n, "min_df": min_df,
                       "min_chamados_categoria": min_chamados_categoria,
                       "representacao": f"tfidf_{Xtf.shape[1]}_termos",
                       "metodo_termos": "log_odds_dirichlet_prior + centroide_tfidf",
                       "metodo_correlacao": "cosseno_centroides_tfidf"},
    }


def gravar_json(res: dict[str, Any], gerado: str) -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    termos = {
        "gerado_em": gerado,
        "natureza": "exploratorio_triagem_taxonomia (NAO e metrica de acuracia validada)",
        "parametros": res["parametros"],
        "categorias": res["categorias"],
        "termos_por_categoria": res["termos_por_categoria"],
    }
    correlacao = {
        "gerado_em": gerado,
        "natureza": "mapa_correlacao_vocabular (cosseno entre centroides TF-IDF)",
        "leitura": "1 = vocabulario sobreposto (candidatas a confusao/fusao); 0 = bem separadas",
        "categorias": res["categorias"],
        "matriz": res["matriz_correlacao"],
        "pares_mais_proximos": res["pares_mais_proximos"],
    }
    (SAIDA / "termos_relevantes.json").write_text(
        json.dumps(termos, ensure_ascii=False, indent=2), encoding="utf-8")
    (SAIDA / "correlacao_categorias.json").write_text(
        json.dumps(correlacao, ensure_ascii=False, indent=2), encoding="utf-8")


def gravar_abas(sh, res: dict[str, Any], gerado: str) -> None:
    """Grava abas privadas (detalhe legível na planilha). Não toca dado bruto."""
    cab_termos = ["categoria", "n_chamados", "ranking", "termo", "score", "metodo", "data_execucao"]
    linhas_termos = []
    for cat, info in res["termos_por_categoria"].items():
        for r, t in enumerate(info["top_log_odds"], start=1):
            linhas_termos.append([cat, info["n_chamados"], r, t["termo"], t["z"], "log_odds_z", gerado])
        for r, t in enumerate(info["top_tfidf"], start=1):
            linhas_termos.append([cat, info["n_chamados"], r, t["termo"], t["peso"], "peso_tfidf", gerado])
    pl.escrever_aba(sh, ABA_TERMOS, cab_termos, linhas_termos)

    cats = res["categorias"]
    cab_corr = ["categoria"] + cats + ["data_execucao"]
    linhas_corr = [[cats[i]] + res["matriz_correlacao"][i] + [gerado] for i in range(len(cats))]
    pl.escrever_aba(sh, ABA_CORRELACAO, cab_corr, linhas_corr)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Termos característicos por categoria + mapa de correlação.")
    p.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    p.add_argument("--credenciais", default=None)
    p.add_argument("--top-n", type=int, default=25, help="Termos por categoria em cada ranking.")
    p.add_argument("--min-df", type=int, default=5, help="Frequência mínima do termo (anti-ruído/identificável).")
    p.add_argument("--min-chamados-categoria", type=int, default=10,
                   help="Ignora categorias com menos chamados que isto.")
    p.add_argument("--aplicar", action="store_true", help="Grava abas privadas na planilha (além dos JSON).")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    config = carregar_config(args.config)
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

    res = calcular(chamados, args.top_n, args.min_df, args.min_chamados_categoria)
    gravar_json(res, gerado)

    print(json.dumps({
        "gerado_em": gerado,
        "n_chamados": len(chamados),
        "n_categorias_analisadas": len(res["categorias"]),
        "representacao": res["parametros"]["representacao"],
        "top_pares_proximos": res["pares_mais_proximos"][:5],
        "json": ["docs/dados/termos_relevantes.json", "docs/dados/correlacao_categorias.json"],
        "modo": "aplicar" if args.aplicar else "dry-run",
    }, ensure_ascii=False, indent=2))

    if not args.aplicar:
        print("modo=dry-run (JSON gerados; nada gravado na planilha).")
        return 0

    gravar_abas(sh, res, gerado)
    print(f"OK: abas {ABA_TERMOS} e {ABA_CORRELACAO} gravadas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
