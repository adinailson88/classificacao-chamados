#!/usr/bin/env python3
"""Classifica a partir do snapshot do repo (arquitetura GitHub-first).

Modos:
  full        (padrão) — classifica TODAS as linhas elegíveis com predições
              out-of-fold (StratifiedKFold), sem vazamento. Uso científico:
              mede a concordância IA x histórico em toda a base.
  incremental — classifica apenas as linhas PENDENTES (com categoria+texto mas
              sem Classificação IA), treinando no conjunto rotulado. Uso
              operacional/cron: conforme novos chamados entram, classifica só eles.
              Se não houver pendentes, é no-op (0 linhas).

Lê dados/snapshot_etapa_1.json e grava classificacao_etapa_1.json + logs +
metricas. NÃO escreve na planilha.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import json

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
    """Linhas rotuladas e com texto útil (base histórica do experimento)."""
    return [
        linha
        for linha in linhas
        if linha.get("categoria_original", "").strip()
        and (linha.get("texto_classificacao") or "").strip()
    ]


def label_confianca(conf: float, baixa: float, alta: float) -> str:
    if conf >= alta:
        return "alta"
    if conf >= baixa:
        return "media"
    return "baixa"


def eh_conferido(valor: Any) -> bool:
    return str(valor or "").strip().upper() in {"TRUE", "VERDADEIRO", "SIM"}


def parse_conf(valor: Any) -> float | None:
    """Converte a confiança armazenada (fração 0-1 ou 0-100) em fração 0-1."""
    txt = str(valor or "").replace("%", "").replace(",", ".").strip()
    if not txt:
        return None
    try:
        v = float(txt)
    except ValueError:
        return None
    return v / 100.0 if v > 1 else v


def predizer_out_of_fold(
    textos: list[str],
    categorias: list[str],
    n_splits: int,
) -> tuple[np.ndarray, np.ndarray, list[int]]:
    """Predições e confianças out-of-fold. Retorna (preds, confs, turno_por_linha)."""
    n = len(textos)
    preds = np.empty(n, dtype=object)
    confs = np.zeros(n, dtype=float)
    turno_por_linha = [0] * n

    contagem = Counter(categorias)
    minimo_classe = min(contagem.values())

    X = np.array(textos, dtype=object)
    y = np.array(categorias, dtype=object)

    if minimo_classe < 2:
        modelo = construir_modelo()
        modelo.fit(list(X), list(y))
        probs = modelo.predict_proba(list(X))
        classes = modelo.named_steps["clf"].classes_
        idx_max = probs.argmax(axis=1)
        preds[:] = classes[idx_max]
        confs[:] = probs[np.arange(n), idx_max]
        return preds, confs, turno_por_linha

    splits_efetivos = max(2, min(n_splits, minimo_classe))
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


def predizer_incremental(
    textos_treino: list[str],
    categorias_treino: list[str],
    textos_pendentes: list[str],
) -> tuple[np.ndarray, np.ndarray]:
    """Treina no conjunto rotulado e prediz só as linhas pendentes."""
    modelo = construir_modelo()
    modelo.fit(textos_treino, categorias_treino)
    probs = modelo.predict_proba(textos_pendentes)
    classes = modelo.named_steps["clf"].classes_
    idx_max = probs.argmax(axis=1)
    preds = classes[idx_max]
    confs = probs[np.arange(len(textos_pendentes)), idx_max]
    return preds, confs


def classificar_subset(modelo: str, textos_treino, cats_treino, subset):
    """Classifica `subset` treinando em (textos_treino, cats_treino).

    baseline -> retorna (preds, confs, None, None).
    producao -> LSTM/RF + faixas: retorna (preds_categoria, confs, executores, criticidades).
    """
    textos_alvo = [l["texto_classificacao"] for l in subset]
    if modelo == "producao":
        import classificador_producao as cp
        clf, eh_lstm = cp.treinar_classificador(textos_treino, cats_treino)
        preds_raw, confs = cp.predizer(clf, eh_lstm, textos_alvo)
        preds, executores, criticidades = [], [], []
        for l, p, c in zip(subset, preds_raw, confs):
            cat, exe = cp.aplicar_faixa(p, float(c), eh_lstm)
            preds.append(cat)
            executores.append(exe)
            criticidades.append(cp.estimar_criticidade(l["texto_classificacao"]))
        return (np.array(preds, dtype=object), np.asarray(confs, dtype=float),
                executores, criticidades)
    preds, confs = predizer_incremental(textos_treino, cats_treino, textos_alvo)
    return preds, confs, None, None


def montar_saidas(
    snapshot: dict[str, Any],
    subset: list[dict[str, Any]],
    preds,
    confs,
    turnos: list[int],
    modo: str,
    estrategia: str,
    limiar_baixa: float,
    limiar_alta: float,
    saida: Path,
    executores: list[str] | None = None,
    criticidades: list[str] | None = None,
) -> None:
    """Constrói e grava classificacao_etapa_1.json + logs + metricas.

    executores/criticidades: opcionais, por linha (modo produção LSTM/RF).
    Sem eles, usa o nome do modelo baseline e criticidade vazia.
    """
    gerado_em = agora_bahia()
    resultado_linhas: list[dict[str, Any]] = []
    log_linhas: list[dict[str, Any]] = []
    acertos = 0

    for i, (linha, pred, conf, turno) in enumerate(zip(subset, preds, confs, turnos)):
        avaliacao = round(float(conf), 4)  # fração 0-1; coluna H formatada como %
        confere = str(pred) == linha["categoria_original"]
        acertos += int(confere)
        rotulo = label_confianca(float(conf), limiar_baixa, limiar_alta)
        executor = executores[i] if executores is not None else MODELO
        criticidade = criticidades[i] if criticidades is not None else ""

        resultado_linhas.append(
            {
                "linha_planilha": linha["linha_planilha"],
                "id_chamado": linha.get("id_chamado", ""),
                "categoria_original": linha["categoria_original"],
                "classificacao_ia": str(pred),
                "avaliacao": avaliacao,
                "executor": executor,
                "criticidade": criticidade,
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
                "avaliacao": avaliacao,
                "confere_historico": confere,
                "confianca_label": rotulo,
            }
        )

    total = len(resultado_linhas)
    y_true = [linha["categoria_original"] for linha in subset]
    y_pred = [str(p) for p in preds]
    metricas = {
        "run_id": snapshot.get("run_id", ""),
        "gerado_em": gerado_em,
        "modelo": MODELO,
        "modo": modo,
        "estrategia": estrategia,
        "total_classificadas": total,
        "concordancia_ia_historico": acertos,
        "concordancia_pct": round(100.0 * acertos / total, 2) if total else 0.0,
        "acuracia": round(float(accuracy_score(y_true, y_pred)), 4) if total else 0.0,
        "f1_macro": round(float(f1_score(y_true, y_pred, average="macro", zero_division=0)), 4) if total else 0.0,
        "f1_weighted": round(float(f1_score(y_true, y_pred, average="weighted", zero_division=0)), 4) if total else 0.0,
        "n_classes": len(set(y_true)),
    }

    turnos_contagem = Counter(turnos)
    log_turnos = [
        {
            "gerado_em": gerado_em,
            "run_id": snapshot.get("run_id", ""),
            "turno": turno,
            "linhas_no_turno": qtd,
            "modelo": MODELO,
            "modo": modo,
        }
        for turno, qtd in sorted(turnos_contagem.items())
    ]

    saida_obj = {
        "run_id": snapshot.get("run_id", ""),
        "gerado_em": gerado_em,
        "modelo": MODELO,
        "modo": modo,
        "estrategia": estrategia,
        "total_classificadas": total,
        "linhas": resultado_linhas,
    }

    gravar_json(saida, saida_obj)
    gravar_jsonl(LOG_TURNOS, log_turnos)
    gravar_jsonl(LOG_LINHAS, log_linhas)
    gravar_json(METRICAS, metricas)

    print(f"modelo={MODELO}")
    print(f"modo={modo}")
    print(f"total_classificadas={total}")
    if total:
        print(f"concordancia={acertos}/{total} ({metricas['concordancia_pct']}%)")
        print(f"acuracia={metricas['acuracia']} f1_macro={metricas['f1_macro']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classifica a partir do snapshot do repo, sem escrever na planilha."
    )
    parser.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    parser.add_argument("--snapshot-json", type=Path, default=SNAPSHOT_PADRAO)
    parser.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    parser.add_argument("--modo", choices=["full", "incremental", "reclassificacao"], default="full")
    parser.add_argument("--modelo", choices=["baseline", "producao"], default="baseline",
                        help="baseline=TF-IDF+LogReg; producao=LSTM primário + RF fallback + faixas.")
    parser.add_argument("--n-splits", type=int, default=5)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = carregar_json(args.config)
    limiares = config.get("classificacao", {})
    limiar_baixa = float(limiares.get("limiar_confianca_baixa", 0.7))
    limiar_alta = float(limiares.get("limiar_alta_confianca", 0.95))

    snapshot = carregar_json(args.snapshot_json)
    elegiveis = selecionar_elegiveis(snapshot.get("linhas") or [])

    if len(elegiveis) < 2:
        print("Informação insuficiente para verificar.")
        return 1

    if args.modo == "incremental":
        pendentes = [l for l in elegiveis if not l.get("classificacao_ia", "").strip()]
        if not pendentes:
            # Nenhuma linha nova: grava resultado vazio e encerra (no-op).
            montar_saidas(
                snapshot, [], np.array([]), np.array([]), [],
                "incremental", "treino_total_predict_pendentes", limiar_baixa, limiar_alta, args.saida,
            )
            print("pendentes=0 (nada a classificar)")
            return 0
        textos_treino = [l["texto_classificacao"] for l in elegiveis]
        cats_treino = [l["categoria_original"] for l in elegiveis]
        preds, confs, executores, criticidades = classificar_subset(
            args.modelo, textos_treino, cats_treino, pendentes
        )
        turnos = [1] * len(pendentes)
        montar_saidas(
            snapshot, pendentes, preds, confs, turnos,
            "incremental", f"treino_total_predict_pendentes_{args.modelo}",
            limiar_baixa, limiar_alta, args.saida, executores, criticidades,
        )
        return 0

    if args.modo == "reclassificacao":
        rcfg = config.get("reclassificacao", {})
        limiar_sel = float(rcfg.get("selecionar_confianca_menor_que", 0.95))
        tam_lote = int(rcfg.get("tamanho_lote", 200))
        delta = 0.05  # melhoria mínima de confiança para sobrescrever

        candidatos = []  # (linha, conf_antiga)
        for l in elegiveis:
            if not l.get("classificacao_ia", "").strip():
                continue  # ainda não classificado -> é tarefa do modo incremental
            if eh_conferido(l.get("conferencia", "")):
                continue  # revisão humana: não mexer
            conf_ant = parse_conf(l.get("avaliacao_atual", ""))
            if conf_ant is None or conf_ant >= limiar_sel:
                continue
            candidatos.append((l, conf_ant))
            if len(candidatos) >= tam_lote:
                break

        if not candidatos:
            montar_saidas(snapshot, [], np.array([]), np.array([]), [],
                          "reclassificacao", "treino_total_reavalia_baixa_conf",
                          limiar_baixa, limiar_alta, args.saida)
            print("candidatos=0 (nada para reclassificar)")
            return 0

        textos_treino = [l["texto_classificacao"] for l in elegiveis]
        cats_treino = [l["categoria_original"] for l in elegiveis]
        cand_linhas = [l for l, _ in candidatos]
        preds, confs, executores, criticidades = classificar_subset(
            args.modelo, textos_treino, cats_treino, cand_linhas
        )

        subset, sub_preds, sub_confs, sub_exec, sub_crit = [], [], [], [], []
        for i, ((l, conf_ant), pred, conf_novo) in enumerate(zip(candidatos, preds, confs)):
            cat_ant = l.get("classificacao_ia", "").strip()
            melhorou = (float(conf_novo) > conf_ant + delta) or \
                       (str(pred) != cat_ant and float(conf_novo) >= conf_ant)
            if melhorou:
                subset.append(l)
                sub_preds.append(pred)
                sub_confs.append(conf_novo)
                if executores is not None:
                    sub_exec.append(executores[i])
                    sub_crit.append(criticidades[i])

        montar_saidas(snapshot, subset, np.array(sub_preds, dtype=object),
                      np.array(sub_confs), [1] * len(subset),
                      "reclassificacao", f"treino_total_reavalia_baixa_conf_{args.modelo}",
                      limiar_baixa, limiar_alta, args.saida,
                      sub_exec or None, sub_crit or None)
        print(f"candidatos={len(candidatos)} reclassificados={len(subset)}")
        return 0

    # modo full (out-of-fold)
    textos = [l["texto_classificacao"] for l in elegiveis]
    categorias = [l["categoria_original"] for l in elegiveis]
    preds, confs, turnos = predizer_out_of_fold(textos, categorias, args.n_splits)
    montar_saidas(
        snapshot, elegiveis, preds, confs, turnos,
        "full", "out_of_fold_stratified_kfold", limiar_baixa, limiar_alta, args.saida,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
