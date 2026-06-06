#!/usr/bin/env python3
"""Calibracao escalar da confianca: P(previsao correta | confianca_bruta).

Entrada: docs/dados/registros_<modelo>.json, sem texto de chamado.
Saida: docs/dados/calibracao_ajustada_modelos.json, agregado.

Esta calibracao e preliminar contra a categoria historica. Ela nao calibra a
probabilidade por classe; calibra a decisao operacional central do projeto:
"com esta confianca, qual a chance empirica de a previsao estar correta?".
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import KFold

from tempo import agora_bahia

RAIZ = Path(__file__).resolve().parents[1]
DADOS_PADRAO = RAIZ / "docs" / "dados"
FAIXAS = [
    (0.0, 0.5, "<50%"),
    (0.5, 0.7, "50-70%"),
    (0.7, 0.8, "70-80%"),
    (0.8, 0.9, "80-90%"),
    (0.9, 0.95, "90-95%"),
    (0.95, 1.01, ">=95%"),
]


def _n(v) -> float:
    try:
        return float(str(v).replace("%", "").replace(",", ".").strip())
    except (TypeError, ValueError):
        return 0.0


def _bucket():
    return {"n": 0, "ok": 0, "conf": 0.0, "brier": 0.0}


def _faixa(v: float) -> str:
    for lo, hi, rotulo in FAIXAS:
        if lo <= v < hi:
            return rotulo
    return ">=95%"


def _fechar(d: dict) -> dict:
    n = d["n"]
    if not n:
        return {"n": 0, "acerto_historico": 0.0, "confianca_media": 0.0, "gap": 0.0, "brier": 0.0}
    acc = d["ok"] / n
    conf = d["conf"] / n
    return {
        "n": n,
        "acerto_historico": round(acc, 4),
        "confianca_media": round(conf, 4),
        "gap": round(conf - acc, 4),
        "brier": round(d["brier"] / n, 4),
    }


def medir(y: np.ndarray, prob: np.ndarray) -> dict:
    bins = {rotulo: _bucket() for _, _, rotulo in FAIXAS}
    geral = _bucket()
    for ok, p in zip(y, prob):
        p = float(max(0.0, min(1.0, p)))
        ok_i = int(ok)
        for alvo in (geral, bins[_faixa(p)]):
            alvo["n"] += 1
            alvo["ok"] += ok_i
            alvo["conf"] += p
            alvo["brier"] += (p - ok_i) ** 2
    total = geral["n"]
    ece = 0.0
    mce = 0.0
    for b in bins.values():
        if not b["n"]:
            continue
        acc = b["ok"] / b["n"]
        conf = b["conf"] / b["n"]
        gap = abs(conf - acc)
        ece += (b["n"] / total) * gap if total else 0.0
        mce = max(mce, gap)
    por_faixa = [{"faixa": rotulo, **_fechar(bins[rotulo])} for _, _, rotulo in FAIXAS]
    return {
        **_fechar(geral),
        "ece": round(ece, 4),
        "mce": round(mce, 4),
        "por_faixa": por_faixa,
        "faixa_95": next(x for x in por_faixa if x["faixa"] == ">=95%"),
    }


def _sigmoid_oof(x: np.ndarray, y: np.ndarray, folds: int) -> np.ndarray:
    out = np.zeros(len(y), dtype=float)
    kf = KFold(n_splits=min(folds, len(y)), shuffle=True, random_state=42)
    for tr, te in kf.split(x):
        if len(set(y[tr])) < 2:
            out[te] = float(np.mean(y[tr])) if len(tr) else 0.0
            continue
        clf = LogisticRegression(solver="lbfgs")
        clf.fit(x[tr].reshape(-1, 1), y[tr])
        out[te] = clf.predict_proba(x[te].reshape(-1, 1))[:, 1]
    return out


def _isotonic_oof(x: np.ndarray, y: np.ndarray, folds: int) -> np.ndarray:
    out = np.zeros(len(y), dtype=float)
    kf = KFold(n_splits=min(folds, len(y)), shuffle=True, random_state=42)
    for tr, te in kf.split(x):
        if len(set(y[tr])) < 2:
            out[te] = float(np.mean(y[tr])) if len(tr) else 0.0
            continue
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        iso.fit(x[tr], y[tr])
        out[te] = iso.predict(x[te])
    return out


def _mapa_calibrador(x: np.ndarray, y: np.ndarray, metodo: str, npts: int = 101) -> dict:
    """Ajusta o calibrador escolhido em TODOS os dados (nao out-of-fold) e amostra
    P(acerto | confianca_bruta) numa grade de npts pontos em [0,1]. Esse mapa e
    reaplicavel a novas confiancas (ver aplicar_calibrado), p.ex. na reclassificacao.
    """
    grade = np.linspace(0.0, 1.0, npts)
    if len(set(y.tolist())) < 2:
        yg = np.full(npts, float(np.mean(y)) if len(y) else 0.0)
    elif metodo == "sigmoid":
        clf = LogisticRegression(solver="lbfgs")
        clf.fit(x.reshape(-1, 1), y)
        yg = clf.predict_proba(grade.reshape(-1, 1))[:, 1]
    else:
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        iso.fit(x, y)
        yg = iso.predict(grade)
    return {"metodo": metodo, "npts": npts, "y_grid": [round(float(v), 4) for v in yg]}


def aplicar_calibrado(calibrador: dict, conf) -> float:
    """Aplica o mapa do calibrador (grade y_grid em [0,1]) a uma confianca bruta,
    por interpolacao linear. Sem mapa, retorna a confianca original."""
    g = (calibrador or {}).get("y_grid")
    if not g:
        try:
            return float(conf)
        except (TypeError, ValueError):
            return 0.0
    try:
        c = max(0.0, min(1.0, float(conf)))
    except (TypeError, ValueError):
        return 0.0
    pos = c * (len(g) - 1)
    i = int(pos)
    if i >= len(g) - 1:
        return float(g[-1])
    frac = pos - i
    return float(g[i] * (1 - frac) + g[i + 1] * frac)


def calibrar_modelo(modelo: str, registros: list[dict], folds: int) -> dict:
    x = np.array([_n(r.get("c")) for r in registros], dtype=float)
    y = np.array([1 if _n(r.get("k")) >= 1 else 0 for r in registros], dtype=int)
    bruto = medir(y, x)
    candidatos = {
        "sigmoid": _sigmoid_oof(x, y, folds),
        "isotonic": _isotonic_oof(x, y, folds),
    }
    medidos = {nome: medir(y, prob) for nome, prob in candidatos.items()}
    melhor_metodo = sorted(medidos, key=lambda m: (medidos[m]["ece"], medidos[m]["brier"], m))[0]
    melhor = medidos[melhor_metodo]
    return {
        "modelo": modelo,
        "total": len(registros),
        "folds": min(folds, len(registros)),
        "calibrador_ajustado": True,
        "alvo": "acerto contra categoria historica",
        "metodo_escolhido": melhor_metodo,
        "antes": bruto,
        "depois": melhor,
        "comparacao_metodos": medidos,
        "delta_ece": round(melhor["ece"] - bruto["ece"], 4),
        "delta_brier": round(melhor["brier"] - bruto["brier"], 4),
        # Mapa reaplicavel (ajustado em todos os dados) para inferencia, ex.: selecao
        # de candidatos da reclassificacao por confianca CALIBRADA.
        "calibrador": _mapa_calibrador(x, y, melhor_metodo),
    }


def calcular_de_arquivos(dados_dir: Path = DADOS_PADRAO, modelos: list[str] | None = None,
                         folds: int = 5) -> dict:
    if modelos is None:
        modelos = sorted(
            p.stem.removeprefix("registros_")
            for p in dados_dir.glob("registros_*.json")
            if p.stem != "registros"
        )
    saidas = []
    for modelo in modelos:
        arq = dados_dir / f"registros_{modelo}.json"
        if not arq.exists():
            continue
        registros = json.loads(arq.read_text(encoding="utf-8"))
        if len(registros) >= 10:
            saidas.append(calibrar_modelo(modelo, registros, folds))
    ranking = sorted(saidas, key=lambda m: (m["depois"]["ece"], -m["depois"]["acerto_historico"], m["modelo"]))
    return {
        "gerado_em": agora_bahia(),
        "fonte": "docs/dados/registros_<modelo>.json",
        "tipo": "calibracao escalar out-of-fold da probabilidade de acerto",
        "alvo": "categoria historica; validacao humana ainda nao iniciada",
        "folds": folds,
        "modelos": saidas,
        "melhor_ece_ajustado": ranking[0]["modelo"] if ranking else "",
        "observacao": (
            "Calibracao preliminar: aprende P(previsao correta | confianca_bruta) contra "
            "historico. A calibracao definitiva deve usar categoria_validada."
        ),
    }


def main() -> int:
    out = calcular_de_arquivos(DADOS_PADRAO)
    destino = DADOS_PADRAO / "calibracao_ajustada_modelos.json"
    destino.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"modelos={len(out['modelos'])} | melhor_ece_ajustado={out['melhor_ece_ajustado']} | saida={destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
