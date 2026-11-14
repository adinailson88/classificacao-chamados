#!/usr/bin/env python3
"""Modelos candidatos da Trilha B: n-gramas de caracteres e embeddings de sentenca.

Os tres modelos seguem a mesma API do `modelos_zoo` (`fit` e `predict_score`) e
entram nas mesmas dobras dos sete modelos principais:

- ``tfidf_caracteres``: LinearSVC sobre TF-IDF de palavras (1-2) mais caracteres
  (2-5, ``char_wb``). Ajuda com erros de digitacao e abreviacoes locais;
- ``embedding_e5``: Regressao Logistica sobre embeddings de sentenca do
  ``intfloat/multilingual-e5-base``, sem ajuste fino;
- ``tfidf_embedding``: LinearSVC sobre a concatenacao dos n-gramas com o
  embedding.

O encoder e nao supervisionado e calculado uma unica vez por texto, de modo que
nenhum rotulo participa dos vetores. O ajuste dos classificadores continua
restrito ao treino de cada dobra.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import modelos_zoo as zoo  # noqa: E402

MODELO_EMBEDDING_PADRAO = "intfloat/multilingual-e5-base"
NOMES = ("tfidf_caracteres", "embedding_e5", "tfidf_embedding")
PESO_EMBEDDING_PADRAO = 1.0


def vetorizador_ngramas():
    """Palavras (1-2) do modelo base somadas a caracteres (2-5) dentro de palavras."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.pipeline import FeatureUnion
    return FeatureUnion([
        ("palavras", zoo._tfidf()),
        ("caracteres", TfidfVectorizer(
            analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True,
            strip_accents="unicode", lowercase=True, max_features=150000)),
    ])


def calcular_embeddings(textos: list[str], modelo: str = MODELO_EMBEDDING_PADRAO,
                        comprimento_maximo: int = 256, lote: int = 32,
                        registrar: Callable[[str], None] = print) -> dict[str, np.ndarray]:
    """Embeddings de sentenca (media dos tokens, normalizada) por texto unico."""
    import torch
    from transformers import AutoModel, AutoTokenizer

    torch.set_num_threads(max(1, torch.get_num_threads()))
    tokenizador = AutoTokenizer.from_pretrained(modelo)
    encoder = AutoModel.from_pretrained(modelo).eval()
    unicos = sorted(set(textos), key=len)
    tabela: dict[str, np.ndarray] = {}
    with torch.no_grad():
        for inicio in range(0, len(unicos), lote):
            parte = unicos[inicio:inicio + lote]
            # Convencao do e5: prefixo "query: " para entradas de classificacao.
            lote_tok = tokenizador(["query: " + t for t in parte], padding=True,
                                   truncation=True, max_length=comprimento_maximo,
                                   return_tensors="pt")
            saida = encoder(**lote_tok).last_hidden_state
            mascara = lote_tok["attention_mask"].unsqueeze(-1).to(saida.dtype)
            media = (saida * mascara).sum(1) / mascara.sum(1).clamp(min=1)
            media = torch.nn.functional.normalize(media, p=2, dim=1)
            for t, v in zip(parte, media.cpu().numpy().astype(np.float32)):
                tabela[t] = v
            if (inicio // lote) % 50 == 0:
                registrar(f"[embeddings] {inicio + len(parte)}/{len(unicos)}")
    return tabela


class _Concatena:
    """Transformador: TF-IDF esparso e embedding denso lado a lado."""

    def __init__(self, tabela: dict[str, np.ndarray], peso: float):
        self.tabela = tabela
        self.peso = peso
        self.vetorizador = vetorizador_ngramas()

    def _densa(self, textos):
        from scipy.sparse import csr_matrix
        m = np.vstack([self.tabela[t] for t in textos]) * self.peso
        return csr_matrix(m)

    def fit_transform(self, textos):
        from scipy.sparse import hstack
        textos = list(textos)
        return hstack([self.vetorizador.fit_transform(textos), self._densa(textos)]).tocsr()

    def transform(self, textos):
        from scipy.sparse import hstack
        textos = list(textos)
        return hstack([self.vetorizador.transform(textos), self._densa(textos)]).tocsr()


class ModeloEmbedding:
    """Classificador sobre embeddings (com ou sem n-gramas), API do zoo."""

    def __init__(self, tabela: dict[str, np.ndarray], com_ngramas: bool,
                 peso: float = PESO_EMBEDDING_PADRAO):
        from sklearn.linear_model import LogisticRegression
        from sklearn.svm import LinearSVC
        self.tabela = tabela
        self.com_ngramas = com_ngramas
        self.peso = peso
        self.classes_ = None
        self._concatena = _Concatena(tabela, peso) if com_ngramas else None
        self.clf = (LinearSVC(class_weight="balanced", random_state=42) if com_ngramas
                    else LogisticRegression(max_iter=1000, class_weight="balanced"))

    def _matriz(self, textos, ajustar: bool = False):
        if self._concatena is not None:
            return (self._concatena.fit_transform(textos) if ajustar
                    else self._concatena.transform(textos))
        return np.vstack([self.tabela[t] for t in textos])

    def fit(self, textos, categorias):
        self.clf.fit(self._matriz(list(textos), ajustar=True), list(categorias))
        self.classes_ = self.clf.classes_
        return self

    def _proba(self, textos):
        X = self._matriz(list(textos))
        if self.com_ngramas:
            m = np.asarray(self.clf.decision_function(X))
            e = np.exp(m - m.max(axis=1, keepdims=True))
            return e / e.sum(axis=1, keepdims=True)
        return self.clf.predict_proba(X)

    def predict_score(self, textos):
        p = self._proba(textos)
        idx = p.argmax(axis=1)
        return self.classes_[idx], p[np.arange(len(idx)), idx]

    def predict_dist(self, textos):
        return self.classes_, self._proba(textos)


def criar_modelo(nome: str, tabela: dict[str, np.ndarray] | None = None,
                 peso: float = PESO_EMBEDDING_PADRAO) -> Any:
    from sklearn.svm import LinearSVC
    if nome == "tfidf_caracteres":
        return zoo._ModeloMargem(LinearSVC(class_weight="balanced", random_state=42),
                                 vetorizador=vetorizador_ngramas())
    if nome in ("embedding_e5", "tfidf_embedding"):
        if tabela is None:
            raise ValueError(f"{nome} exige a tabela de embeddings")
        return ModeloEmbedding(tabela, com_ngramas=(nome == "tfidf_embedding"),
                               peso=peso)
    raise ValueError(f"modelo alternativo desconhecido: {nome}")
