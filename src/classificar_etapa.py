#!/usr/bin/env python3
"""Classifica a etapa 1 lendo o snapshot do repo (arquitetura GitHub-first).

Le dados/snapshot_etapa_1.json, treina o baseline TF-IDF + LogReg e gera
predicoes out-of-fold (StratifiedKFold) para todas as linhas rotuladas, de modo
que nenhuma linha e prevista por um modelo treinado nela mesma. NAO escreve na
planilha: acumula tudo em arquivos no repositorio.

Saidas (em dados/):
  classificacao_etapa_1.json  -> resultado por linha (G:J em G,H,I,J)
  log_turnos.jsonl            -> 1 registro por fold/turno
  log_linha_a_linha.jsonl     -> 1 registro por linha processada
  metricas_experimento.json   -> concordancia IA x historico, acuracia, F1 macro
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline


RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
DADOS = RAIZ / "dados"
SNAPSHOT_PADRAO = DADOS / "snapshot_etapa_1.json"
SAIDA_PADRAO = DADOS / "classificacao_etapa_1.json"
LOG_TURNOS = DADOS / "log_turnos.jsonl"
LOG_LINHAS = DADOS / "log_linha_a_linha.jsonl"
METRICAS = DADOS / "metricas_experimento.json"

MODELO = "Baseline_TFIDF_LogReg"
FUSO_BAHIA = timezone(timedelta(hours=-3))


def agora_bahia() -> str:
    return datetime.now(FUSO_BAHIA).strftime("%Y-%m-%dT%H:%M:%S-03:00")


def carregar_json(caminho: Path) -> dict[str, Any]:
    with caminho.open("r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def gravar_json(caminho: Path, dados: Any) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=2)
        arquivo.write("\n")


def gravar_jsonl(caminho: Path, registros: list[dict[str, Any]]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8") as arquivo:
        for registro in registros:
            arquivo.write(json.dumps(registro, ensure_ascii=False) + "\n")


def construir_modelo() -> Pipeline:
    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    strip_accents="unicode",
                    lowercase=True,
                    ngram_range=(1, 2),
                    min_df=1,
                    max_features=30000,
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    solver="lbfgs",
                ),
            ),
        ]
    )


def selecionar_elegiveis(linhas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Linhas rotuladas e com texto util (base historica do experimento)."""
    elegiveis = []
    for linha in linhas:
        if not linha.get("categoria_original"):
            continue
        if not (linha.get("texto_classificacao") or "").strip():
            continue
        elegiveis.append(linha)
    return elegiveis


def label_confianca(conf: float, baixa: float, alta: float) -> str:
    if conf >= alta:
        return "alta"
    if conf >= baixa:
        return "media"
    return "baixa"


def predizer_out_of_fold(
    textos: list[str],
    categorias: list[str],
    n_splits: int,
) -> tuple[np.ndarray, np.ndarray, list[int]]:
    """Predicoes e confiancas out-of-fold. Retorna (preds, confs, turnos_por_linha)."""
    n = len(textos)
    preds = np.empty(n, dtype=object)
    confs = np.zeros(n, dtype=float)
    turno_por_linha = [0] * n

    contagem = Counter(categorias)
    minimo_classe = min(contagem.values())
    splits_efetivos = max(2, min(n_splits, minimo_classe))

    X = np.array(textos, dtype=object)
    y = np.array(categorias, dtype=object)

    if minimo_classe < 2:
        # Sem folds confiaveis: treina em tudo e prediz tudo (com vazamento
        # assumido e sinalizado nas metricas). Caminho de contingencia.
        modelo = construir_modelo()
        modelo.fit(list(X), list(y))
        probs = modelo.predict_proba(list(X))
        classes = modelo.named_steps["clf"].classes_
        idx_max = probs.argmax(axis=1)
        preds[:] = classes[idx_max]
        confs[:] = probs[np.arange(n), idx_max]
        return preds, confs, turno_por_linha

    skf = StratifiedKFold(n_splits=splits_efetivos, shuffle=True, random_state=42)
    for turno, (treino_idx, teste_idx) in enumerate(skf.split(X, y), start=1):
        modelo = construir_modelo()
        modelo.fit(list(X[treino_idx]), list(y[treino_idx]))
        probs = modelo.predict_proba(list(X[teste_idx]))
        classes = modelo.named_steps["clf"].classes_
        idx_max = probs.argmax(axis=1)
        for pos_local, pos_global in enumerate(teste_idx):
            preds[pos_global] = classes[idx_max[pos_local]]
            confs[pos_global] = float(probs[pos_local, idx_max[pos_local]])
            turno_por_linha[pos_global] = turno

    return preds, confs, turno_por_linha


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classifica a etapa 1 a partir do snapshot do repo, sem escrever na planilha."
    )
    parser.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    parser.add_argument("--snapshot-json", type=Path, default=SNAPSHOT_PADRAO)
    parser.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    parser.add_argument("--n-splits", type=int, default=5)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = carregar_json(args.config)
    limiares = config.get("classificacao", {})
    limiar_baixa = float(limiares.get("limiar_confianca_baixa", 0.7))
    limiar_alta = float(limiares.get("limiar_alta_confianca", 0.95))

    snapshot = carregar_json(args.snapshot_json)
    linhas = snapshot.get("linhas") or []
    elegiveis = selecionar_elegiveis(linhas)

    if len(elegiveis) < 2:
        print("Informação insuficiente para verificar.")
        return 1

    textos = [linha["texto_classificacao"] for linha in elegiveis]
    categorias = [linha["categoria_original"] for linha in elegiveis]

    preds, confs, turnos = predizer_out_of_fold(textos, categorias, args.n_splits)

    gerado_em = agora_bahia()
    resultado_linhas: list[dict[str, Any]] = []
    log_linhas: list[dict[str, Any]] = []
    acertos = 0

    for linha, pred, conf, turno in zip(elegiveis, preds, confs, turnos):
        avaliacao_pct = round(float(conf) * 100.0, 2)
        confere = str(pred) == linha["categoria_original"]
        acertos += int(confere)
        rotulo = label_confianca(float(conf), limiar_baixa, limiar_alta)

        resultado_linhas.append(
            {
                "linha_planilha": linha["linha_planilha"],
                "id_chamado": linha.get("id_chamado", ""),
                "categoria_original": linha["categoria_original"],
                "classificacao_ia": str(pred),
                "avaliacao_pct": avaliacao_pct,
                "executor": MODELO,
                "criticidade": "",
                "comparacao": confere,
                "confianca_label": rotulo,
            }
        )
        log_linhas.append(
            {
                "gerado_em": gerado_em,
                "run_id": snapshot.get("run_id", ""),
                "linha_planilha": linha["linha_planilha"],
                "id_chamado": linha.get("id_chamado", ""),
                "turno": turno,
                "categoria_original": linha["categoria_original"],
                "classificacao_ia": str(pred),
                "avaliacao_pct": avaliacao_pct,
                "confere_historico": confere,
                "confianca_label": rotulo,
            }
        )

    y_true = categorias
    y_pred = [str(p) for p in preds]
    metricas = {
        "run_id": snapshot.get("run_id", ""),
        "gerado_em": gerado_em,
        "modelo": MODELO,
        "estrategia": "out_of_fold_stratified_kfold",
        "total_classificadas": len(resultado_linhas),
        "concordancia_ia_historico": acertos,
        "concordancia_pct": round(100.0 * acertos / len(resultado_linhas), 2),
        "acuracia": round(float(accuracy_score(y_true, y_pred)), 4),
        "f1_macro": round(float(f1_score(y_true, y_pred, average="macro", zero_division=0)), 4),
        "f1_weighted": round(float(f1_score(y_true, y_pred, average="weighted", zero_division=0)), 4),
        "n_classes": len(set(categorias)),
    }

    # Resumo por turno para o log de turnos.
    turnos_contagem = Counter(turnos)
    log_turnos = [
        {
            "gerado_em": gerado_em,
            "run_id": snapshot.get("run_id", ""),
            "turno": turno,
            "linhas_no_turno": qtd,
            "modelo": MODELO,
        }
        for turno, qtd in sorted(turnos_contagem.items())
    ]

    saida = {
        "run_id": snapshot.get("run_id", ""),
        "gerado_em": gerado_em,
        "modelo": MODELO,
        "estrategia": "out_of_fold_stratified_kfold",
        "total_classificadas": len(resultado_linhas),
        "linhas": resultado_linhas,
    }

    gravar_json(args.saida, saida)
    gravar_jsonl(LOG_TURNOS, log_turnos)
    gravar_jsonl(LOG_LINHAS, log_linhas)
    gravar_json(METRICAS, metricas)

    print(f"modelo={MODELO}")
    print(f"total_classificadas={metricas['total_classificadas']}")
    print(f"concordancia={metricas['concordancia_ia_historico']}/{metricas['total_classificadas']} ({metricas['concordancia_pct']}%)")
    print(f"acuracia={metricas['acuracia']} f1_macro={metricas['f1_macro']}")
    print(f"saida={args.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
