#!/usr/bin/env python3
"""Modelo ROBUSTO ("quase-LLM" local) para reclassificação dos casos difíceis.

Ideia: um modelo mais pesado, baseado em EMBEDDINGS de um transformer multilíngue
(sentence-transformers, 100% local, sem APIs externas de LLM) + classificador
LogisticRegression sobre os embeddings. Roda raramente e em poucos chamados (os de
menor confiança), na etapa de reclassificação.

Se `sentence-transformers` não estiver instalado, faz FALLBACK para o classificador
de produção (LSTM/RF) — assim o fluxo nunca quebra.

Interface do objeto retornado: `.predict_com_conf(textos) -> (preds, confs)`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

MODELO_ST = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class ClassificadorTransformer:
    """Embeddings de transformer multilíngue + LogisticRegression."""

    def __init__(self, nome_modelo: str = MODELO_ST):
        from sentence_transformers import SentenceTransformer
        self.encoder = SentenceTransformer(nome_modelo)
        self.clf = None
        self.classes_ = None

    def fit(self, textos, categorias):
        from sklearn.linear_model import LogisticRegression
        X = self.encoder.encode(list(textos), batch_size=64,
                                show_progress_bar=False, normalize_embeddings=True)
        self.clf = LogisticRegression(max_iter=2000, class_weight="balanced")
        self.clf.fit(X, list(categorias))
        self.classes_ = self.clf.classes_
        return self

    def predict_com_conf(self, textos):
        X = self.encoder.encode(list(textos), batch_size=64,
                                show_progress_bar=False, normalize_embeddings=True)
        probs = self.clf.predict_proba(X)
        idx = probs.argmax(axis=1)
        return self.classes_[idx], probs[np.arange(len(idx)), idx]


def treinar(textos, categorias):
    """Retorna (modelo, tag). Tenta transformer; se indisponível, cai para LSTM/RF.

    tag é usada no nome do executor (ex.: Reclass_<tag>).
    """
    try:
        import sentence_transformers  # noqa: F401
        clf = ClassificadorTransformer().fit(textos, categorias)
        return clf, "Robusto"
    except Exception as e:  # noqa: BLE001
        print(f"[robusto] transformer indisponível ({type(e).__name__}: {e}) — "
              "fallback LSTM/RF.", file=sys.stderr)
        import classificador_producao as cp

        clf, eh_lstm = cp.treinar_classificador(textos, categorias)

        class _Wrap:
            def predict_com_conf(self, x):
                return cp.predizer(clf, eh_lstm, x)

        return _Wrap(), ("LSTM" if eh_lstm else "RF")
