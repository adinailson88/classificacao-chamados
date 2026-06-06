#!/usr/bin/env python3
"""Diagnostico de calibracao por modelo a partir dos JSONs publicados.

Este script NAO ajusta calibrador. Ele mede, para cada IA materializada, se a
confianca bruta se comporta como probabilidade empirica de acerto contra a
categoria historica. A calibracao definitiva depende da validacao humana.
"""

from __future__ import annotations

import json
from pathlib import Path

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


def _faixa(conf: float) -> str:
    for lo, hi, rotulo in FAIXAS:
        if lo <= conf < hi:
            return rotulo
    return ">=95%"


def _bucket():
    return {"n": 0, "ok": 0, "conf": 0.0, "brier": 0.0}


def _fecha(d: dict) -> dict:
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


def diagnosticar_registros(modelo: str, registros: list[dict]) -> dict:
    geral = _bucket()
    bins = {rotulo: _bucket() for _, _, rotulo in FAIXAS}
    for r in registros:
        conf = max(0.0, min(1.0, _n(r.get("c"))))
        ok = 1 if _n(r.get("k")) >= 1 else 0
        for alvo in (geral, bins[_faixa(conf)]):
            alvo["n"] += 1
            alvo["ok"] += ok
            alvo["conf"] += conf
            alvo["brier"] += (conf - ok) ** 2

    total = geral["n"]
    ece = 0.0
    mce = 0.0
    for b in bins.values():
        if not b["n"]:
            continue
        acc = b["ok"] / b["n"]
        conf = b["conf"] / b["n"]
        gap_abs = abs(conf - acc)
        ece += (b["n"] / total) * gap_abs if total else 0.0
        mce = max(mce, gap_abs)

    fechado = _fecha(geral)
    por_faixa = [{"faixa": rotulo, **_fecha(bins[rotulo])} for _, _, rotulo in FAIXAS]
    faixa95 = next((x for x in por_faixa if x["faixa"] == ">=95%"), {"n": 0})
    return {
        "modelo": modelo,
        "total": total,
        "acerto_historico": fechado["acerto_historico"],
        "confianca_media": fechado["confianca_media"],
        "brier": fechado["brier"],
        "ece": round(ece, 4),
        "mce": round(mce, 4),
        "faixa_95": faixa95,
        "por_faixa": por_faixa,
        "calibrador_ajustado": False,
        "tipo_confianca": "bruta; diagnostico contra historico",
    }


def calcular_de_arquivos(dados_dir: Path = DADOS_PADRAO, modelos: list[str] | None = None) -> dict:
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
        try:
            registros = json.loads(arq.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            registros = []
        if registros:
            saidas.append(diagnosticar_registros(modelo, registros))

    ranking_ece = sorted(saidas, key=lambda x: (x["ece"], -x["acerto_historico"], x["modelo"]))
    min_suporte_95 = max(100, int(sum(x["total"] for x in saidas) / max(1, len(saidas)) * 0.01))
    elegiveis_95 = [x for x in saidas if x.get("faixa_95", {}).get("n", 0) >= min_suporte_95]
    ranking_95 = sorted(
        elegiveis_95,
        key=lambda x: (-x.get("faixa_95", {}).get("acerto_historico", 0.0),
                       -x.get("faixa_95", {}).get("n", 0),
                       x["modelo"]),
    )
    return {
        "gerado_em": agora_bahia(),
        "fonte": "docs/dados/registros_<modelo>.json",
        "alvo": "categoria historica; validacao humana ainda nao iniciada",
        "calibrador_ajustado": False,
        "metrica": "ECE/MCE/Brier medidos sobre confianca bruta",
        "suporte_minimo_faixa_95": min_suporte_95,
        "modelos": saidas,
        "melhor_ece": ranking_ece[0]["modelo"] if ranking_ece else "",
        "melhor_faixa_95": ranking_95[0]["modelo"] if ranking_95 else "",
        "observacao": (
            "Diagnostico preliminar. LinearSVC/SGD usam margem normalizada, LSTM usa softmax, "
            "arvores usam voto e modelos probabilisticos usam predict_proba. Nenhuma dessas "
            "saidas deve ser tratada como confianca calibrada sem ajuste posterior."
        ),
    }


def main() -> int:
    out = calcular_de_arquivos(DADOS_PADRAO)
    destino = DADOS_PADRAO / "calibracao_modelos.json"
    destino.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"modelos={len(out['modelos'])} | melhor_ece={out['melhor_ece']} | saida={destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
