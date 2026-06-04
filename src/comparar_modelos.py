#!/usr/bin/env python3
"""Compara baseline TF-IDF+LogReg vs LSTM no MESMO holdout estratificado 80/20.

Mede a concordância com o histórico (categoria_original) no conjunto de teste,
para responder objetivamente se o LSTM supera o baseline. Não escreve na planilha.
Lê dados/snapshot_etapa_1.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

sys.path.insert(0, str(Path(__file__).resolve().parent))
from modelo_lstm import ClassificadorLSTM  # noqa: E402


RAIZ = Path(__file__).resolve().parents[1]
SNAPSHOT_PADRAO = RAIZ / "dados" / "snapshot_etapa_1.json"


def carregar_elegiveis(snapshot_path: Path, min_por_classe: int):
    snap = json.loads(snapshot_path.read_text(encoding="utf-8"))
    textos, cats = [], []
    for l in snap.get("linhas", []):
        c = l.get("categoria_original", "").strip()
        t = (l.get("texto_classificacao") or "").strip()
        if c and t:
            textos.append(t)
            cats.append(c)
    # remove classes raras (não dá para estratificar com <2; ruído estatístico)
    cont = Counter(cats)
    mantidos = [(t, c) for t, c in zip(textos, cats) if cont[c] >= min_por_classe]
    descartadas = sum(1 for c in cont if cont[c] < min_por_classe)
    textos = [t for t, _ in mantidos]
    cats = [c for _, c in mantidos]
    return textos, cats, descartadas


def baseline_pipeline() -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(strip_accents="unicode", lowercase=True,
                                  ngram_range=(1, 2), min_df=1, max_features=30000)),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced", solver="lbfgs")),
    ])


def metricas(nome, y_true, y_pred):
    acc = accuracy_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
    concord = sum(int(a == b) for a, b in zip(y_true, y_pred))
    print(f"[{nome}] concordancia={concord}/{len(y_true)} "
          f"({100.0*concord/len(y_true):.2f}%) | acuracia={acc:.4f} | f1_macro={f1:.4f}")
    return {"concordancia": concord, "n": len(y_true), "acuracia": round(acc, 4),
            "f1_macro": round(f1, 4)}


def parse_args():
    p = argparse.ArgumentParser(description="Compara baseline vs LSTM em holdout 80/20.")
    p.add_argument("--snapshot-json", type=Path, default=SNAPSHOT_PADRAO)
    p.add_argument("--test-size", type=float, default=0.2)
    p.add_argument("--min-por-classe", type=int, default=2)
    p.add_argument("--epochs", type=int, default=15)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    textos, cats, descartadas = carregar_elegiveis(args.snapshot_json, args.min_por_classe)
    if len(textos) < 10:
        print("Informação insuficiente para verificar.")
        return 1

    X_tr, X_te, y_tr, y_te = train_test_split(
        textos, cats, test_size=args.test_size, random_state=42, stratify=cats
    )
    print(f"n_total={len(textos)} | treino={len(X_tr)} | teste={len(X_te)} | "
          f"n_classes={len(set(cats))} | classes_descartadas(<{args.min_por_classe})={descartadas}")
    print("-" * 70)

    # Baseline
    base = baseline_pipeline()
    base.fit(X_tr, y_tr)
    pred_base = base.predict(X_te)
    m_base = metricas("baseline TF-IDF+LogReg", y_te, pred_base)

    # LSTM
    print("treinando LSTM (pode levar alguns minutos)...")
    lstm = ClassificadorLSTM()
    lstm.fit(X_tr, y_tr, epochs=args.epochs, verbose=2)
    pred_lstm, _ = lstm.predict_com_conf(X_te)
    m_lstm = metricas("LSTM Bidirecional", y_te, [str(p) for p in pred_lstm])

    print("-" * 70)
    delta = 100.0 * (m_lstm["concordancia"] / m_lstm["n"] - m_base["concordancia"] / m_base["n"])
    print(f"DELTA concordancia (LSTM - baseline) = {delta:+.2f} pontos percentuais")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
