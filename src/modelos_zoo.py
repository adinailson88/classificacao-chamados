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


def _tfidf_com_glossario():
    """TF-IDF + bloco de cobertura do glossário por categoria (log-odds), em
    FeatureUnion: o classificador passa a "consultar" o glossário junto com o
    texto, como uma coluna adicional -- nao substitui o TF-IDF, soma a ele."""
    from sklearn.pipeline import FeatureUnion
    from glossario_features import GlossarioFeaturizer
    return FeatureUnion([("tfidf", _tfidf()), ("glossario", GlossarioFeaturizer())])


class _ModeloProba:
    """Pipeline TF-IDF + classificador com predict_proba (score = prob. máxima)."""

    def __init__(self, clf, vetorizador=None):
        from sklearn.pipeline import Pipeline
        self.pipe = Pipeline([("tfidf", vetorizador or _tfidf()), ("clf", clf)])
        self.classes_ = None

    def fit(self, textos, categorias):
        self.pipe.fit(list(textos), list(categorias))
        self.classes_ = self.pipe.classes_
        return self

    def predict_score(self, textos):
        proba = self.pipe.predict_proba(list(textos))
        idx = proba.argmax(axis=1)
        return self.classes_[idx], proba[np.arange(len(idx)), idx]

    def predict_dist(self, textos):
        """(classes_, matriz n x K de probabilidades) — permite escolher a melhor
        categoria EXCLUINDO classes vetadas (memoria de conferencia humana)."""
        return self.classes_, self.pipe.predict_proba(list(textos))


class _ModeloMargem:
    """Para LinearSVC (sem proba): score = softmax da decision_function."""

    def __init__(self, clf, vetorizador=None):
        from sklearn.pipeline import Pipeline
        self.pipe = Pipeline([("tfidf", vetorizador or _tfidf()), ("clf", clf)])
        self.classes_ = None

    def fit(self, textos, categorias):
        self.pipe.fit(list(textos), list(categorias))
        self.classes_ = self.pipe.named_steps["clf"].classes_
        return self

    def predict_score(self, textos):
        p = self._proba(textos)
        idx = p.argmax(axis=1)
        return self.classes_[idx], p[np.arange(len(idx)), idx]

    def _proba(self, textos):
        m = np.asarray(self.pipe.decision_function(list(textos)))
        # Com duas classes, decision_function devolve um vetor 1-D de margens.
        # `atleast_2d` o transformaria em (1, n), invertendo amostras e classes;
        # o reshape mantem uma linha por amostra.
        if m.ndim == 1:
            m = m.reshape(-1, 1)
        if m.shape[1] == 1:  # caso binário
            m = np.hstack([-m, m])
        e = np.exp(m - m.max(axis=1, keepdims=True))
        return e / e.sum(axis=1, keepdims=True)

    def predict_dist(self, textos):
        """(classes_, matriz n x K do softmax da margem)."""
        return self.classes_, self._proba(textos)


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

    def predict_dist(self, textos):
        """(classes_, matriz n x K) tanto para o LSTM quanto para o fallback RF."""
        if self.eh_lstm:
            return self.clf.predict_dist(textos)
        return self.clf.classes_, self.clf.predict_proba(list(textos))


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
        # Otimizacoes opcionais (default = comportamento original preservado):
        # subamostragem do treino, orcamento de tempo de parede e early stopping.
        self.max_train = int(os.environ.get("TRANSFORMER_MAX_TRAIN", "0"))      # 0 = base inteira
        # Estrategia de selecao do treino: "" / "estratificada" (subamostra aleatoria
        # estratificada) ou "cluster_coreset" (selecao representativa por clustering,
        # mesmo criterio de src/bertimbau_coreset.py). EXPERIMENTAL; default preserva.
        self.select = os.environ.get("TRANSFORMER_SELECT", "").lower()
        self.time_budget = float(os.environ.get("TRANSFORMER_TIME_BUDGET_S", "0"))  # 0 = sem limite
        self.early_stop = os.environ.get("TRANSFORMER_EARLY_STOP", "0").lower() in ("1", "true", "sim")
        self.patience = int(os.environ.get("TRANSFORMER_PATIENCE", "1"))
        self.eval_frac = float(os.environ.get("TRANSFORMER_EVAL_FRAC", "0.1"))
        self.seed = int(os.environ.get("TRANSFORMER_SEED", "42"))
        self._fb = None              # fallback (LSTM/RF) se transformers indisponivel
        self._tok = self._model = None
        self.classes_ = None
        self._id2lab = None
        # Resumo do ultimo treino (consumido pelo estado/dashboard do BERTimbau).
        self.train_info = {}

    @property
    def usou_fallback(self) -> bool:
        """True quando o ultimo fit() nao conseguiu fazer fine-tuning real
        (torch/transformers indisponivel) e caiu para LSTM/RF. Quem chama
        fit()+predict() DEVE checar isto antes de publicar o resultado como
        'transformer_ft' — achado de 2026-07-25: o cron automatico nunca
        instala torch/transformers, entao toda predicao rotulada
        'transformer_ft' nele e na verdade LSTM disfarcado."""
        return self.train_info.get("status") == "fallback_lstm"

    def _subamostra_estratificada(self, textos, y, limite):
        """Reduz o conjunto de treino para 'limite' linhas preservando, na medida
        do possivel, a proporcao por categoria (estratificada). Retorna (textos, y)."""
        import random
        if limite <= 0 or limite >= len(y):
            return textos, y
        por_classe = {}
        for i, lab in enumerate(y):
            por_classe.setdefault(lab, []).append(i)
        rng = random.Random(self.seed)
        n = len(y)
        escolhidos = []
        for lab, idxs in por_classe.items():
            cota = max(1, round(limite * len(idxs) / n))  # garante >=1 por classe
            cota = min(cota, len(idxs))
            escolhidos.extend(rng.sample(idxs, cota))
        rng.shuffle(escolhidos)
        escolhidos = escolhidos[:max(limite, len(por_classe))]  # nunca abaixo de 1/classe
        return [textos[i] for i in escolhidos], [y[i] for i in escolhidos]

    def fit(self, textos, categorias):
        import time
        t0 = time.time()
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
            self.train_info = {"status": "fallback_lstm", "motivo": f"{type(e).__name__}: {e}"}
            return self

        labels = sorted(set(cats))
        lab2id = {c: i for i, c in enumerate(labels)}
        self._id2lab = {i: c for c, i in lab2id.items()}
        self.classes_ = np.array(labels)
        y = [lab2id[c] for c in cats]

        n_total = len(y)
        metodo_selecao = "completo"
        if self.select == "cluster_coreset":
            try:
                import bertimbau_coreset as bc
                alvo = self.max_train if self.max_train > 0 else 4000
                idx_sel = bc.selecionar_indices(textos, [self._id2lab[i] for i in y],
                                                seed=self.seed, max_total=alvo)
                if idx_sel and len(idx_sel) < n_total:
                    textos = [textos[i] for i in idx_sel]
                    y = [y[i] for i in idx_sel]
                    metodo_selecao = "cluster_coreset"
                    print(f"[transformer_ft] selecao cluster_coreset: {len(y)}/{n_total} "
                          f"(alvo={alvo}).", file=sys.stderr)
            except Exception as e:  # noqa: BLE001
                print(f"[transformer_ft] cluster_coreset indisponivel ({type(e).__name__}: {e}); "
                      "caindo para subamostra estratificada.", file=sys.stderr)
        if metodo_selecao == "completo":
            textos, y = self._subamostra_estratificada(textos, y, self.max_train)
            if len(y) < n_total:
                metodo_selecao = "estratificada"
                print(f"[transformer_ft] subamostragem estratificada: {len(y)}/{n_total} "
                      f"(TRANSFORMER_MAX_TRAIN={self.max_train}).", file=sys.stderr)

        # Holdout estratificado para early stopping (so quando viavel).
        idx_tr, idx_ev = list(range(len(y))), []
        if self.early_stop and len(y) >= 50:
            try:
                from sklearn.model_selection import train_test_split
                idx_tr, idx_ev = train_test_split(
                    list(range(len(y))), test_size=self.eval_frac, random_state=self.seed,
                    stratify=y if len(set(y)) > 1 else None)
            except Exception as e:  # noqa: BLE001
                print(f"[transformer_ft] holdout estratificado indisponivel ({e}); sem early stopping.",
                      file=sys.stderr)
                idx_tr, idx_ev = list(range(len(y))), []

        self._tok = AutoTokenizer.from_pretrained(self.base)
        self._model = AutoModelForSequenceClassification.from_pretrained(self.base, num_labels=len(labels))
        device = "cuda" if torch.cuda.is_available() else "cpu"
        usar_fp16 = bool(os.environ.get("TRANSFORMER_FP16", "1").lower() in ("1", "true", "sim")
                         and device == "cuda")
        self._model.to(device)

        # Padding DINAMICO: tokeniza por lote (pad ao maior do lote), nao a base toda.
        # Resultado identico ao padding global, porem mais rapido e com menos memoria.
        tok, max_len = self._tok, self.max_len
        textos_tr = [textos[i] for i in idx_tr]
        y_tr = [y[i] for i in idx_tr]

        def collate(batch):
            xs = [b[0] for b in batch]
            ys = [b[1] for b in batch]
            enc = tok(xs, truncation=True, padding=True, max_length=max_len, return_tensors="pt")
            enc["labels"] = torch.tensor(ys)
            return enc

        ds = list(zip(textos_tr, y_tr))
        dl = DataLoader(ds, batch_size=self.batch, shuffle=True, collate_fn=collate)
        opt = torch.optim.AdamW(self._model.parameters(), lr=self.lr)
        total = max(1, len(dl) * self.epochs)
        sched = get_linear_schedule_with_warmup(opt, int(0.1 * total), total)
        scaler = torch.cuda.amp.GradScaler() if usar_fp16 else None

        def avaliar_macro_f1():
            if not idx_ev:
                return None
            from sklearn.metrics import f1_score
            self._model.eval()
            preds, reais = [], []
            with torch.no_grad():
                for i in range(0, len(idx_ev), self.batch):
                    sub = idx_ev[i:i + self.batch]
                    enc = tok([textos[j] for j in sub], truncation=True, padding=True,
                              max_length=max_len, return_tensors="pt")
                    logits = self._model(input_ids=enc["input_ids"].to(device),
                                         attention_mask=enc["attention_mask"].to(device)).logits
                    preds.extend(logits.argmax(dim=1).cpu().tolist())
                    reais.extend(y[j] for j in sub)
            self._model.train()
            return float(f1_score(reais, preds, average="macro", zero_division=0))

        melhor_f1, melhor_estado, sem_melhora = -1.0, None, 0
        epocas_rodadas, parou_por_tempo = 0, False
        self._model.train()
        for ep in range(self.epochs):
            for enc in dl:
                if self.time_budget > 0 and (time.time() - t0) > self.time_budget:
                    parou_por_tempo = True
                    break
                opt.zero_grad()
                if scaler is not None:
                    with torch.cuda.amp.autocast():
                        out = self._model(input_ids=enc["input_ids"].to(device),
                                          attention_mask=enc["attention_mask"].to(device),
                                          labels=enc["labels"].to(device))
                    scaler.scale(out.loss).backward()
                    scaler.unscale_(opt)
                    torch.nn.utils.clip_grad_norm_(self._model.parameters(), 1.0)
                    scaler.step(opt); scaler.update()
                else:
                    out = self._model(input_ids=enc["input_ids"].to(device),
                                      attention_mask=enc["attention_mask"].to(device),
                                      labels=enc["labels"].to(device))
                    out.loss.backward()
                    torch.nn.utils.clip_grad_norm_(self._model.parameters(), 1.0)
                    opt.step()
                sched.step()
            epocas_rodadas = ep + 1
            f1 = avaliar_macro_f1()
            dt = time.time() - t0
            msg = f"[transformer_ft] epoca {ep + 1}/{self.epochs} ({dt:.0f}s)"
            if f1 is not None:
                msg += f" | macro-F1(val)={f1:.4f}"
            print(msg + (" | parou por orcamento de tempo" if parou_por_tempo else ""), file=sys.stderr)
            if f1 is not None:
                if f1 > melhor_f1 + 1e-4:
                    melhor_f1, sem_melhora = f1, 0
                    melhor_estado = {k: v.detach().cpu().clone() for k, v in self._model.state_dict().items()}
                else:
                    sem_melhora += 1
            if parou_por_tempo:
                break
            if self.early_stop and idx_ev and sem_melhora >= self.patience:
                print(f"[transformer_ft] early stopping na epoca {ep + 1} (sem melhora >= {self.patience}).",
                      file=sys.stderr)
                break

        if melhor_estado is not None:
            self._model.load_state_dict(melhor_estado)  # load_best_model_at_end
            print(f"[transformer_ft] restaurado melhor modelo (macro-F1 val={melhor_f1:.4f}).", file=sys.stderr)

        self.train_info = {
            "status": "ok",
            "n_treino": len(y_tr),
            "n_total_disponivel": n_total,
            "n_validacao": len(idx_ev),
            "n_categorias": len(labels),
            "epocas_pedidas": self.epochs,
            "epocas_rodadas": epocas_rodadas,
            "early_stopping": bool(self.early_stop and idx_ev),
            "parou_por_tempo": parou_por_tempo,
            "macro_f1_validacao": round(melhor_f1, 4) if melhor_f1 >= 0 else None,
            "max_len": self.max_len,
            "batch": self.batch,
            "fp16": usar_fp16,
            "subamostrado": len(y) < n_total,
            "metodo_selecao": metodo_selecao,
            "segundos": round(time.time() - t0, 1),
        }
        return self

    def predict_score(self, textos):
        if self._fb is not None:
            return self._fb.predict_score(textos)
        _, prob = self.predict_dist(textos)
        idx = prob.argmax(axis=1)
        preds = np.array([self._id2lab[int(j)] for j in idx])
        return preds, prob[np.arange(len(idx)), idx]

    def predict_dist(self, textos):
        """(classes_, matriz n x K do softmax completo)."""
        if self._fb is not None:
            return self._fb.predict_dist(textos)
        import torch
        textos = [str(t) for t in textos]
        device = next(self._model.parameters()).device
        self._model.eval()
        blocos = []
        with torch.no_grad():
            for i in range(0, len(textos), self.batch):
                lote = textos[i:i + self.batch]
                enc = self._tok(lote, truncation=True, padding=True, max_length=self.max_len, return_tensors="pt")
                logits = self._model(input_ids=enc["input_ids"].to(device),
                                     attention_mask=enc["attention_mask"].to(device)).logits
                blocos.append(torch.softmax(logits, dim=1).cpu().numpy())
        return self.classes_, np.vstack(blocos) if blocos else np.zeros((0, len(self.classes_ or [])))


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
        # random_state=42 explicito: LinearSVC (liblinear) usa um gerador
        # aleatorio interno na otimizacao por coordenadas; sem semente fixa,
        # a mesma base pode produzir previsoes diferentes entre execucoes.
        return _ModeloMargem(LinearSVC(class_weight="balanced", random_state=42))
    if nome == "linear_svc_glossario":
        # EXPERIMENTAL (nao entra em MODELOS_LEVES/MODELOS_TODOS nem no
        # retreino canonico): mesmo LinearSVC, mas o vetorizador soma ao
        # TF-IDF um bloco de features de cobertura do glossario por categoria
        # (termos_relevantes.json). Comparar contra 'linear_svc' via
        # comparar_modelos.py antes de considerar promover.
        return _ModeloMargem(LinearSVC(class_weight="balanced", random_state=42),
                             vetorizador=_tfidf_com_glossario())
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
