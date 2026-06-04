#!/usr/bin/env python3
"""Classificador de produção: LSTM primário + RF fallback + faixas de confiança.

Espelha motor_classificacao_v1.py:
- LSTM Bidirecional como classificador primário (100% local);
- se TensorFlow indisponível ou base insuficiente, cai para RandomForest (TF-IDF);
- faixas de confiança definem o nome do Executor (coluna I):
    conf >= 0,95  -> alta  -> "LSTM" / "RF_Fallback"
    0,70 <= conf  -> baixa -> "LSTM_BAIXA_CONF" / "RF_Fallback_BAIXA_CONF"
    conf <  0,70  -> baixa, e a categoria HUMANA é mantida (não sobrescreve)
- criticidade (coluna J) por heurística de palavras-chave.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

LIMIAR_ALTA = 0.95
LIMIAR_BAIXA = 0.70
MIN_BASE_LSTM = 200

_CRIT_ALTA = ["urgente", "incêndio", "incendio", "queda", "choque",
              "alagamento", "infiltração grave", "perigo"]
_CRIT_MEDIA = ["reparo", "substituição", "substituicao", "quebra",
               "falha", "defeito", "corretiva"]


def estimar_criticidade(texto: str) -> str:
    t = (texto or "").lower()
    if any(p in t for p in _CRIT_ALTA):
        return "Alta"
    if any(p in t for p in _CRIT_MEDIA):
        return "Média"
    return "Baixa"


def treinar_classificador(textos, categorias, verbose: int = 2):
    """Treina LSTM (primário) ou RF (fallback). Retorna (clf, eh_lstm)."""
    try:
        import tensorflow  # noqa: F401
        from modelo_lstm import ClassificadorLSTM
        if len(textos) >= MIN_BASE_LSTM:
            clf = ClassificadorLSTM()
            clf.fit(textos, categorias, verbose=verbose)
            return clf, True
        print(f"[producao] base pequena ({len(textos)}) — fallback RF.", file=sys.stderr)
    except Exception as e:  # noqa: BLE001
        print(f"[producao] LSTM indisponível ({type(e).__name__}: {e}) — fallback RF.",
              file=sys.stderr)

    from sklearn.ensemble import RandomForestClassifier
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.pipeline import Pipeline
    rf = Pipeline([
        ("tfidf", TfidfVectorizer(strip_accents="unicode", lowercase=True,
                                  ngram_range=(1, 2), min_df=1, max_features=30000)),
        ("clf", RandomForestClassifier(n_estimators=200, class_weight="balanced",
                                       n_jobs=-1, random_state=42)),
    ])
    rf.fit(textos, categorias)
    return rf, False


def predizer(clf, eh_lstm, textos):
    """Retorna (preds, confs) para qualquer um dos classificadores."""
    if eh_lstm:
        return clf.predict_com_conf(textos)
    probs = clf.predict_proba(textos)
    classes = clf.classes_
    idx = probs.argmax(axis=1)
    return classes[idx], probs[np.arange(len(idx)), idx]


def nome_executor(conf: float, eh_lstm: bool) -> str:
    """Nome do executor por faixa (Etapa 15 do roteiro)."""
    if conf >= LIMIAR_ALTA:
        return "LSTM" if eh_lstm else "RF_Fallback"
    return "LSTM_BAIXA_CONF" if eh_lstm else "RF_Fallback_BAIXA_CONF"


def faixa_confianca(conf: float) -> str:
    """Faixa para as métricas (Etapa 14): abaixo_70 / entre_70_95 / acima_95."""
    if conf >= LIMIAR_ALTA:
        return "acima_95"
    if conf >= LIMIAR_BAIXA:
        return "entre_70_95"
    return "abaixo_70"


def aplicar_faixa(pred, conf: float, eh_lstm: bool):
    """Retorna (categoria_final, executor). No experimento grava-se SEMPRE a
    predição da IA (para medir concordância e divergências honestamente)."""
    return str(pred), nome_executor(conf, eh_lstm)
