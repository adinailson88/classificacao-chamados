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

import sys

import numpy as np

MODELOS_LEVES = ["naive_bayes", "regressao_logistica", "linear_svc",
                 "sgd", "extra_trees", "random_forest"]
# Modelos PESADOS (rede neural / transformer). transformer_ft = BERTimbau com
# fine-tuning de classificacao (contextual, self-attention; exige transformers+torch).
MODELOS_PESADOS = ["lstm", "transformer_ft"]
MODELOS_TODOS = MODELOS_LEVES + MODELOS_PESADOS

# Transformer pre-treinado em portugues (BERTimbau). Pode ser trocado por env.
import os  # noqa: E402
TRANSFORMER_BASE = os.environ.get("TRANSFORMER_BASE", "neuralmind/bert-base-portuguese-cased")


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


class _ModeloTransformerFT:
    """BERTimbau (transformer pre-treinado em portugues) com FINE-TUNING de
    classificacao de sequencia. Diferente do TF-IDF (saco de palavras), usa
    self-attention: avalia a FRASE inteira em contexto. Pesado: exige transformers
    + torch. Se indisponiveis, faz FALLBACK para LSTM/RF (o fluxo nunca quebra).

    Hiperparametros conservadores por padrao (CPU). Ajustaveis por env:
    TRANSFORMER_EPOCHS, TRANSFORMER_MAXLEN, TRANSFORMER_BATCH, TRANSFORMER_LR.
    """

    def __init__(self, base: str = TRANSFORMER_BASE):
        self.base = base
        self.epochs = int(os.environ.get("TRANSFORMER_EPOCHS", "3"))
        self.max_len = int(os.environ.get("TRANSFORMER_MAXLEN", "192"))
        self.batch = int(os.environ.get("TRANSFORMER_BATCH", "16"))
        self.lr = float(os.environ.get("TRANSFORMER_LR", "2e-5"))
        self._fb = None              # fallback (LSTM/RF) se transformers indisponivel
        self._tok = self._model = None
        self.classes_ = None
        self._id2lab = None

    def fit(self, textos, categorias):
        textos = [str(t) for t in textos]
        cats = [str(c) for c in categorias]
        try:
            import torch
            from torch.utils.data import DataLoader
            from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                                      get_linear_schedule_with_warmup)
        except Exception as e:  # noqa: BLE001
            print(f"[transformer_ft] transformers/torch indisponivel ({type(e).__name__}: {e}); "
                  "fallback LSTM/RF.", file=sys.stderr)
            self._fb = _ModeloLSTM().fit(textos, cats)
            self.classes_ = getattr(self._fb, "classes_", None)
            return self

        labels = sorted(set(cats))
        lab2id = {c: i for i, c in enumerate(labels)}
        self._id2lab = {i: c for c, i in lab2id.items()}
        self.classes_ = np.array(labels)
        y = [lab2id[c] for c in cats]

        self._tok = AutoTokenizer.from_pretrained(self.base)
        self._model = AutoModelForSequenceClassification.from_pretrained(self.base, num_labels=len(labels))
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model.to(device)

        enc = self._tok(textos, truncation=True, padding=True, max_length=self.max_len, return_tensors="pt")
        ds = torch.utils.data.TensorDataset(enc["input_ids"], enc["attention_mask"], torch.tensor(y))
        dl = DataLoader(ds, batch_size=self.batch, shuffle=True)
        opt = torch.optim.AdamW(self._model.parameters(), lr=self.lr)
        total = max(1, len(dl) * self.epochs)
        sched = get_linear_schedule_with_warmup(opt, int(0.1 * total), total)

        self._model.train()
        for ep in range(self.epochs):
            for ids, mask, lab in dl:
                opt.zero_grad()
                out = self._model(input_ids=ids.to(device), attention_mask=mask.to(device), labels=lab.to(device))
                out.loss.backward()
                torch.nn.utils.clip_grad_norm_(self._model.parameters(), 1.0)
                opt.step(); sched.step()
            print(f"[transformer_ft] epoca {ep + 1}/{self.epochs} concluida.", file=sys.stderr)
        return self

    def predict_score(self, textos):
        if self._fb is not None:
            return self._fb.predict_score(textos)
        import torch
        textos = [str(t) for t in textos]
        device = next(self._model.parameters()).device
        self._model.eval()
        preds, scores = [], []
        with torch.no_grad():
            for i in range(0, len(textos), self.batch):
                lote = textos[i:i + self.batch]
                enc = self._tok(lote, truncation=True, padding=True, max_length=self.max_len, return_tensors="pt")
                logits = self._model(input_ids=enc["input_ids"].to(device),
                                     attention_mask=enc["attention_mask"].to(device)).logits
                prob = torch.softmax(logits, dim=1)
                p, idx = prob.max(dim=1)
                preds.extend(self._id2lab[int(j)] for j in idx.cpu())
                scores.extend(float(x) for x in p.cpu())
        return np.array(preds), np.array(scores)


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
    if nome in ("transformer_ft", "bertimbau", "transformer"):
        return _ModeloTransformerFT()
    raise ValueError(f"modelo desconhecido: {nome}")
