#!/usr/bin/env python3
"""Classificador LSTM Bidirecional (espelha o motor de produção Malha IA).

Arquitetura: Embedding(8000,128) -> BiLSTM(64) -> Dropout(0.5) -> Dense(64,ReLU)
-> Dense(K, softmax). Otimizador Adam, perda sparse_categorical_crossentropy,
EarlyStopping(restore_best_weights). 100% local (sem APIs externas de LLM).

Interface: fit(textos, categorias), predict_com_conf(textos) -> (preds, confs),
save(dir) / load(dir) para persistir e reutilizar no cron (treino 1x, predição N).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")  # silencia logs INFO do TF

import numpy as np

LSTM_VOCAB_SIZE = 8000
LSTM_MAX_LEN = 120
LSTM_EMBED_DIM = 128
LSTM_UNITS = 64
LSTM_DENSE_UNITS = 64
LSTM_DROPOUT = 0.5
LSTM_LAYERS = 1

PERFIS_LSTM = {
    "padrao": {
        "vocab_size": 8000,
        "max_len": 120,
        "embed_dim": 128,
        "units": 64,
        "dense_units": 64,
        "dropout": 0.5,
        "layers": 1,
        "epochs": 15,
        "batch_size": 128,
        "paciencia": 3,
    },
    "robusto": {
        "vocab_size": 20000,
        "max_len": 220,
        "embed_dim": 192,
        "units": 128,
        "dense_units": 128,
        "dropout": 0.45,
        "layers": 2,
        "epochs": 25,
        "batch_size": 96,
        "paciencia": 5,
    },
}


def resolver_parametros_lstm(config: dict | None = None) -> dict:
    cfg = dict(config or {})
    perfil_config = cfg.pop("perfil", "padrao")
    perfil = os.getenv("LSTM_PERFIL") or perfil_config or "padrao"
    perfil = str(perfil).lower()
    params = dict(PERFIS_LSTM.get(perfil, PERFIS_LSTM["padrao"]))
    params.update({k: v for k, v in cfg.items() if v not in (None, "")})
    return params


def _tf():
    import tensorflow as tf
    return tf


class ClassificadorLSTM:
    def __init__(
        self,
        vocab_size: int = LSTM_VOCAB_SIZE,
        max_len: int = LSTM_MAX_LEN,
        embed_dim: int = LSTM_EMBED_DIM,
        units: int = LSTM_UNITS,
        dense_units: int = LSTM_DENSE_UNITS,
        dropout: float = LSTM_DROPOUT,
        layers: int = LSTM_LAYERS,
    ):
        self.vocab_size = vocab_size
        self.max_len = max_len
        self.embed_dim = embed_dim
        self.units = units
        self.dense_units = dense_units
        self.dropout = dropout
        self.layers = max(1, int(layers))
        self.model = None
        self.tokenizer = None
        self.classes_ = None  # np.ndarray de categorias (índice = id da classe)

    def _vetorizar(self, textos):
        tf = _tf()
        seqs = self.tokenizer.texts_to_sequences(list(textos))
        return tf.keras.preprocessing.sequence.pad_sequences(
            seqs, maxlen=self.max_len, padding="post", truncating="post"
        )

    def fit(self, textos, categorias, epochs: int = 15, batch_size: int = 128,
            validation_split: float = 0.1, paciencia: int = 3, verbose: int = 2,
            usar_class_weight: bool = True):
        tf = _tf()
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import (
            Embedding, Bidirectional, LSTM, Dense, Dropout,
        )
        from tensorflow.keras.preprocessing.text import Tokenizer
        from tensorflow.keras.callbacks import EarlyStopping
        from sklearn.utils.class_weight import compute_class_weight

        categorias = list(categorias)
        self.classes_ = np.array(sorted(set(categorias)), dtype=object)
        cat_para_id = {c: i for i, c in enumerate(self.classes_)}
        y = np.array([cat_para_id[c] for c in categorias], dtype=np.int32)

        class_weight = None
        if usar_class_weight:
            pesos = compute_class_weight(
                "balanced", classes=np.arange(len(self.classes_)), y=y
            )
            class_weight = {i: float(w) for i, w in enumerate(pesos)}

        self.tokenizer = Tokenizer(num_words=self.vocab_size, oov_token="<OOV>")
        self.tokenizer.fit_on_texts(list(textos))
        X = self._vetorizar(textos)

        n_classes = len(self.classes_)
        camadas = [Embedding(self.vocab_size, self.embed_dim, input_length=self.max_len)]
        for idx_camada in range(self.layers):
            camadas.append(Bidirectional(LSTM(
                self.units,
                return_sequences=(idx_camada < self.layers - 1),
            )))
            camadas.append(Dropout(float(self.dropout)))
        camadas.extend([
            Dense(int(self.dense_units), activation="relu"),
            Dense(n_classes, activation="softmax"),
        ])
        self.model = Sequential(camadas)
        self.model.compile(
            optimizer="adam",
            loss="sparse_categorical_crossentropy",
            metrics=["accuracy"],
        )
        early = EarlyStopping(monitor="val_loss", patience=paciencia,
                              restore_best_weights=True)
        self.model.fit(
            X, y,
            epochs=epochs, batch_size=batch_size,
            validation_split=validation_split,
            callbacks=[early], verbose=verbose,
            class_weight=class_weight,
        )
        return self

    def predict_com_conf(self, textos):
        X = self._vetorizar(textos)
        probs = self.model.predict(X, verbose=0)
        idx = probs.argmax(axis=1)
        preds = self.classes_[idx]
        confs = probs[np.arange(len(idx)), idx]
        return preds, confs

    def save(self, diretorio: str | Path) -> None:
        d = Path(diretorio)
        d.mkdir(parents=True, exist_ok=True)
        self.model.save(d / "modelo.keras")
        with (d / "tokenizer.json").open("w", encoding="utf-8") as f:
            f.write(self.tokenizer.to_json())
        with (d / "classes.json").open("w", encoding="utf-8") as f:
            json.dump(list(self.classes_), f, ensure_ascii=False)
        with (d / "config.json").open("w", encoding="utf-8") as f:
            json.dump(
                {"vocab_size": self.vocab_size, "max_len": self.max_len,
                 "embed_dim": self.embed_dim, "units": self.units,
                 "dense_units": self.dense_units, "dropout": self.dropout,
                 "layers": self.layers}, f,
            )

    @classmethod
    def load(cls, diretorio: str | Path) -> "ClassificadorLSTM":
        tf = _tf()
        from tensorflow.keras.preprocessing.text import tokenizer_from_json
        d = Path(diretorio)
        with (d / "config.json").open("r", encoding="utf-8") as f:
            cfg = json.load(f)
        obj = cls(**cfg)
        obj.model = tf.keras.models.load_model(d / "modelo.keras")
        with (d / "tokenizer.json").open("r", encoding="utf-8") as f:
            obj.tokenizer = tokenizer_from_json(f.read())
        with (d / "classes.json").open("r", encoding="utf-8") as f:
            obj.classes_ = np.array(json.load(f), dtype=object)
        return obj
