#!/usr/bin/env python3
"""Compara os mesmos modelos em quatro condicoes, a partir dos JSON da Trilha B.

1. nossa base -> nossa base (OOF agrupado, taxonomia completa);
2. nossa base -> UFRN (nossa taxonomia mapeada a `divisao`, concordancia);
3. UFRN -> UFRN (teste em 2025 em diante, seis divisoes);
4. UFRN -> nossa base (previsao em `divisao`, comparada a correspondencia proposta).

Le somente artefatos agregados (sem texto) e escreve um relatorio em Markdown e um
JSON. A correlacao de postos (Spearman) entre condicoes mede se o mesmo modelo
continua melhor quando muda a base, a direcao ou a taxonomia.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[1]
DADOS_B = RAIZ / "docs" / "dados" / "trilha_b"


def _carregar(caminho: Path) -> dict[str, Any]:
    return json.loads(caminho.read_text(encoding="utf-8"))


def _postos(valores: dict[str, float]) -> dict[str, float]:
    """Postos 1..n (1 = maior valor), empates com a media dos postos."""
    ordem = sorted(valores, key=lambda k: -valores[k])
    saida: dict[str, float] = {}
    i = 0
    while i < len(ordem):
        j = i
        while j + 1 < len(ordem) and valores[ordem[j + 1]] == valores[ordem[i]]:
            j += 1
        for k in range(i, j + 1):
            saida[ordem[k]] = (i + j) / 2 + 1
        i = j + 1
    return saida


def spearman(a: dict[str, float], b: dict[str, float]) -> float | None:
    comuns = sorted(set(a) & set(b))
    if len(comuns) < 3:
        return None
    pa, pb = _postos({k: a[k] for k in comuns}), _postos({k: b[k] for k in comuns})
    n = len(comuns)
    ma = sum(pa.values()) / n
    mb = sum(pb.values()) / n
    num = sum((pa[k] - ma) * (pb[k] - mb) for k in comuns)
    da = sum((pa[k] - ma) ** 2 for k in comuns) ** 0.5
    db = sum((pb[k] - mb) ** 2 for k in comuns) ** 0.5
    return round(num / (da * db), 4) if da and db else None


def reunir(retreino: dict[str, Any], alternativas: dict[str, Any] | None,
           direto: dict[str, Any], reverso: dict[str, Any]) -> dict[str, Any]:
    cond: dict[str, dict[str, float]] = {
        "nossa_para_nossa": {}, "nossa_para_ufrn": {},
        "ufrn_para_ufrn": {}, "ufrn_para_nossa": {}}
    for m in retreino["modelos"]:
        cond["nossa_para_nossa"][m["modelo"]] = m["acuracia"]
    if alternativas:
        for m in alternativas["retreino"]["modelos"]:
            cond["nossa_para_nossa"][m["modelo"]] = m["acuracia"]
    for nome, m in direto["modelos"].items():
        if m["concordancia_com_correspondencia"] is not None:
            cond["nossa_para_ufrn"][nome] = m["concordancia_com_correspondencia"]
    for nome, m in reverso["resultados"].items():
        cond["ufrn_para_ufrn"][nome] = m["ufrn_teste"]["acuracia"]
        cond["ufrn_para_nossa"][nome] = m["nossa_base"]["acuracia"]
    nomes = list(cond)
    correlacoes = []
    for i, a in enumerate(nomes):
        for b in nomes[i + 1:]:
            correlacoes.append({"condicoes": [a, b], "n_modelos": len(set(cond[a]) & set(cond[b])),
                                "spearman": spearman(cond[a], cond[b])})
    return {"acuracia_por_condicao": cond, "correlacao_de_postos": correlacoes}


def renderizar(res: dict[str, Any]) -> str:
    cond = res["acuracia_por_condicao"]
    nomes = list(cond)
    modelos = sorted({m for c in cond.values() for m in c},
                     key=lambda m: -(cond["nossa_para_nossa"].get(m) or 0))
    rotulo = {"nossa_para_nossa": "Nossa para nossa (OOF, 41 categorias)",
              "nossa_para_ufrn": "Nossa para UFRN (concordância com `divisao`)",
              "ufrn_para_ufrn": "UFRN para UFRN (teste 2025+, 6 divisões)",
              "ufrn_para_nossa": "UFRN para nossa (6 divisões, correspondência proposta)"}
    linhas = ["# Os mesmos modelos em quatro condições", "",
              "Acurácia (ou concordância) por modelo. Em cada coluna, a taxonomia e a base "
              "mudam; os scripts de treino são os mesmos.", "",
              "| Modelo | " + " | ".join(rotulo[n] for n in nomes) + " |",
              "|---|" + "---:|" * len(nomes)]
    for m in modelos:
        celulas = [f"{cond[n][m]:.4f}".replace(".", ",") if m in cond[n] else "n/d" for n in nomes]
        linhas.append(f"| {m} | " + " | ".join(celulas) + " |")
    linhas += ["", "## Correlação de postos entre condições (Spearman)", "",
               "| Condições | Modelos em comum | Spearman |", "|---|---:|---:|"]
    for c in res["correlacao_de_postos"]:
        s = "n/d" if c["spearman"] is None else f"{c['spearman']:.3f}".replace(".", ",")
        linhas.append(f"| {rotulo[c['condicoes'][0]]} × {rotulo[c['condicoes'][1]]} | "
                      f"{c['n_modelos']} | {s} |")
    return "\n".join(linhas) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dados", type=Path, default=DADOS_B)
    p.add_argument("--markdown", type=Path, required=True)
    p.add_argument("--json", type=Path, required=True)
    a = p.parse_args()
    alt = a.dados / "alternativas.json"
    res = reunir(_carregar(a.dados / "retreino.json"),
                 _carregar(alt) if alt.exists() else None,
                 _carregar(a.dados / "ufrn_resumo.json"),
                 _carregar(a.dados / "ufrn_reverso.json"))
    a.json.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    a.markdown.write_text(renderizar(res), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
