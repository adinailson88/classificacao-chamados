#!/usr/bin/env python3
"""Zoo modular de modelos locais leves para COMPARAÇÃO (sem API externa).

Todos os modelos expõem a mesma interface:
    m = criar_modelo(nome)
    m.fit(textos, categorias)
    preds, scores = m.predict_score(textos)   # score = confiança/probabilidade 0-1

Modelos leves (TF-IDF + classificador): naive_bayes, regressao_logistica,
linear_svc, sgd, extra_trees, random_forest. Também 'lstm' (reusa o classificador
de produção, exige TensorFlow). FastText/Transformer ficam como extensão futura
(dependências pesadas) — basta acrescentar aqui sem mudar o runner.
"""

from __future__ import annotations

import numpy as np

MODELOS_LEVES = ["naive_bayes", "regressao_logistica", "linear_svc",
                 "sgd", "extra_trees", "random_forest"]
MODELOS_TODOS = MODELOS_LEVES + ["lstm"]


def _tfidf():
    from sklearn.feature_extraction.text import TfidfVectorizer
    return TfidfVectorizer(strip_accents="unicode", lowercase=True,
                           ngram_range=(1, 2), min_df=1, max_features=30000)


class _ModeloProba:
    """Pipeline TF-IDF + classificador com predict_proba (score = prob. máxima)."""

    def __init__(self, clf):
        from sklearn.pipeline import Pipeline
        self.pipe = Pipeline([("tfidf", _tfidf()), ("clf", clf)])
        self.classes_ = None

    def fit(self, textos, categorias):
        self.pipe.fit(list(textos), list(categorias))
        self.classes_ = self.pipe.classes_
        return self

    def predict_score(self, textos):
        proba = self.pipe.predict_proba(list(textos))
        idx = proba.argmax(axis=1)
        return self.classes_[idx], proba[np.arange(len(idx)), idx]


class _ModeloMargem:
    """Para LinearSVC (sem proba): score = softmax da decision_function."""

    def __init__(self, clf):
        from sklearn.pipeline import Pipeline
        self.pipe = Pipeline([("tfidf", _tfidf()), ("clf", clf)])
        self.classes_ = None

    def fit(self, textos, categorias):
        self.pipe.fit(list(textos), list(categorias))
        self.classes_ = self.pipe.named_steps["clf"].classes_
        return self

    def predict_score(self, textos):
        m = np.atleast_2d(self.pipe.decision_function(list(textos)))
        if m.shape[1] == 1:  # caso binário
            m = np.hstack([-m, m])
        e = np.exp(m - m.max(axis=1, keepdims=True))
        p = e / e.sum(axis=1, keepdims=True)
        idx = p.argmax(axis=1)
        return self.classes_[idx], p[np.arange(len(idx)), idx]


class _ModeloLSTM:
    """Reusa o classificador de produção (LSTM primário; RF se TF indisponível)."""

    def __init__(self):
        self.clf = None
        self.eh_lstm = False

    def fit(self, textos, categorias):
        import classificador_producao as cp
        self.clf, self.eh_lstm = cp.treinar_classificador(textos, categorias, verbose=0)
        return self

    def predict_score(self, textos):
        import classificador_producao as cp
        return cp.predizer(self.clf, self.eh_lstm, textos)


def criar_modelo(nome: str):
    from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
    from sklearn.linear_model import LogisticRegression, SGDClassifier
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.svm import LinearSVC

    nome = (nome or "").strip().lower()
    if nome == "naive_bayes":
        return _ModeloProba(MultinomialNB())
    if nome == "regressao_logistica":
        return _ModeloProba(LogisticRegression(max_iter=1000, class_weight="balanced"))
    if nome == "linear_svc":
        return _ModeloMargem(LinearSVC(class_weight="balanced"))
    if nome == "sgd":
        return _ModeloProba(SGDClassifier(loss="log_loss", class_weight="balanced", random_state=42))
    if nome == "extra_trees":
        return _ModeloProba(ExtraTreesClassifier(n_estimators=200, class_weight="balanced",
                                                 n_jobs=-1, random_state=42))
    if nome == "random_forest":
        return _ModeloProba(RandomForestClassifier(n_estimators=200, class_weight="balanced",
                                                   n_jobs=-1, random_state=42))
    if nome == "lstm":
        return _ModeloLSTM()
    raise ValueError(f"modelo desconhecido: {nome}")
