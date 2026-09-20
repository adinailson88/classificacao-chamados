#!/usr/bin/env python3
"""Feature de GLOSSÁRIO por categoria: cobertura de termos-assinatura (log-odds)
como bloco de features adicional para os modelos leves — o LinearSVC passa a
"consultar" o glossário junto com o texto, sem substituir o TF-IDF.

Fonte do glossário: docs/dados/termos_relevantes.json (gerado por
src/relevancia_termos.py — log-odds com prior de Dirichlet, já em produção
para a análise exploratória de taxonomia/erros). Este módulo só CONSOME esse
JSON; não recalcula termos.

Motivação (achado 2026-09-20): a categoria "Outros > Erro de chamado" tem
17,86% de taxa de erro da IA (3ª pior) e seu glossário característico é
majoritariamente vocabulário de TI/acesso (computador, email, senha, sigaa,
conta) — fora do domínio de manutenção predial. A feature de cobertura dá ao
classificador um sinal explícito e interpretável dessa contaminação, em vez
de depender só do peso aprendido pelos n-gramas do TF-IDF.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin

RAIZ = Path(__file__).resolve().parents[1]
TERMOS_JSON_PADRAO = RAIZ / "docs" / "dados" / "termos_relevantes.json"


def _norm(s: Any) -> str:
    t = unicodedata.normalize("NFKD", str(s or ""))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return " ".join(t.split()).casefold()


def carregar_glossario(caminho: Path = TERMOS_JSON_PADRAO, top_n: int = 15,
                       z_minimo: float = 3.0) -> dict[str, list[str]]:
    """{categoria: [termos]} — os top_n termos de maior log-odds (z >= z_minimo)
    de cada categoria em termos_relevantes.json. z_minimo descarta termos cujo
    sinal de característico-da-categoria não é estatisticamente robusto."""
    try:
        d = json.loads(Path(caminho).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    glossario: dict[str, list[str]] = {}
    for cat, info in (d.get("termos_por_categoria") or {}).items():
        termos = [t["termo"] for t in (info.get("top_log_odds") or [])
                 if t.get("z", 0) >= z_minimo][:top_n]
        if termos:
            glossario[cat] = termos
    return glossario


class GlossarioFeaturizer(BaseEstimator, TransformerMixin):
    """Transforma cada texto em um vetor de cobertura do glossário por
    categoria: fração dos termos-assinatura da categoria presentes no texto.

    Sklearn-compatible (fit/transform), plugável num FeatureUnion junto com o
    TfidfVectorizer. O glossário é carregado uma vez (estático, calculado
    fora do fit) — reflete o corpus no momento em que relevancia_termos.py
    rodou por último, não recalcula por dobra de validação cruzada.
    """

    def __init__(self, caminho: Path = TERMOS_JSON_PADRAO, top_n: int = 15,
                z_minimo: float = 3.0):
        self.caminho = caminho
        self.top_n = top_n
        self.z_minimo = z_minimo

    def fit(self, X, y=None):
        glossario = carregar_glossario(self.caminho, self.top_n, self.z_minimo)
        self.categorias_ = sorted(glossario)
        self.termos_norm_ = [
            [_norm(t) for t in glossario[cat]] for cat in self.categorias_
        ]
        return self

    def transform(self, X):
        if not getattr(self, "categorias_", None):
            return np.zeros((len(X), 0))
        linhas = []
        for texto in X:
            t = " " + _norm(texto) + " "
            linhas.append([
                sum(1 for termo in termos if f" {termo} " in t or termo in t) / len(termos)
                for termos in self.termos_norm_
            ])
        return np.asarray(linhas, dtype=float)

    def get_feature_names_out(self, input_features=None):
        return np.array([f"glossario::{c}" for c in getattr(self, "categorias_", [])])
