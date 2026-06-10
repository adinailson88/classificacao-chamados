#!/usr/bin/env python3
"""Cruzamento: matriz de confusão IA×histórico × mapa de correlação vocabular.

Junta dois sinais que, sozinhos, não bastam para decidir taxonomia:

1. **Confusão IA×histórico**: com que frequência os chamados cuja categoria
   HISTÓRICA é A acabam recebendo a categoria B pela IA (coluna G / Etapa 1).
   `confusao[A][B] = P(IA prevê B | histórico = A)` (normalizada por linha).
   É concordância/divergência contra o histórico — NÃO acerto validado.
2. **Correlação vocabular**: cosseno entre os centróides TF-IDF das categorias
   (reaproveita `relevancia_termos.calcular`). Mede sobreposição de vocabulário.

O cruzamento ranqueia os pares (A,B) que são **ao mesmo tempo**:
- muito confundidos (a IA troca A por B com frequência), e
- semanticamente próximos (vocabulário sobreposto).

Esses pares são os **candidatos mais fortes a revisão de taxonomia** (fusão,
renomeação ou critério de desambiguação) — etapa 46 do roteiro. O score é
exploratório e prioriza revisão humana; não funde nem renomeia nada
automaticamente, não altera o histórico e não é métrica de acurácia validada.

Sem `--aplicar` = dry-run (gera JSON em docs/dados/). Com `--aplicar`, grava
também a aba privada CRUZAMENTO_TAXONOMIA.

Saídas:
- docs/dados/confusao_historico_ia.json
- docs/dados/cruzamento_taxonomia.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planilha as pl  # noqa: E402
import relevancia_termos as rt  # noqa: E402
from tempo import agora_bahia  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
SAIDA = RAIZ / "docs" / "dados"
ABA_SAIDA = "CRUZAMENTO_TAXONOMIA"


def carregar_chamados(ws, range_a1: str) -> list[dict[str, Any]]:
    """Lê (linha, categoria histórica C, texto, categoria IA G). Reusa a
    normalização e o `cel` de relevancia_termos para manter a convenção."""
    valores = pl.ler_valores(ws, range_a1)
    cab = valores[0] if valores else []
    idx = {rt.norm(n): i for i, n in enumerate(cab)}
    campos_texto = ["TITULO", "DESCRICAO GLPI", "TITULO O.S.M.", "DESCRICAO O.S.M."]
    i_cat = idx.get(rt.norm("CATEGORIA COMPLETA"))
    i_ia = idx.get(rt.norm("Classificacao IA"))

    chamados: list[dict[str, Any]] = []
    for pos, linha in enumerate(valores[1:], start=2):
        categoria = rt.cel(linha, i_cat)
        partes = [rt.cel(linha, idx.get(rt.norm(c))) for c in campos_texto]
        texto = "\n".join(p for p in partes if p)
        if not categoria or not texto:
            continue
        chamados.append({
            "linha": pos,
            "categoria": categoria,
            "texto": texto,
            "categoria_ia": rt.cel(linha, i_ia),
        })
    return chamados


def matriz_confusao(chamados: list[dict[str, Any]], cats: list[str]) -> dict[str, Any]:
    """Confusão IA×histórico restrita às categorias analisadas (mesmo conjunto da
    correlação). Linha = histórico, coluna = previsão da IA, normalizada por linha."""
    pos = {c: i for i, c in enumerate(cats)}
    n = len(cats)
    bruta = np.zeros((n, n), dtype=float)
    fora = 0           # IA previu categoria fora do conjunto analisado
    sem_pred = 0       # chamado sem previsão da IA
    for c in chamados:
        a = c["categoria"]
        b = c["categoria_ia"]
        if a not in pos:
            continue
        if not b:
            sem_pred += 1
            continue
        if b not in pos:
            fora += 1
            continue
        bruta[pos[a]][pos[b]] += 1
    soma_linha = bruta.sum(axis=1, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        norm = np.where(soma_linha > 0, bruta / soma_linha, 0.0)
    return {
        "matriz_bruta": bruta.astype(int).tolist(),
        "matriz_normalizada": np.round(norm, 4).tolist(),
        "suporte_por_categoria": bruta.sum(axis=1).astype(int).tolist(),
        "previsoes_fora_do_conjunto": int(fora),
        "chamados_sem_previsao_ia": int(sem_pred),
    }


def cruzar(cats: list[str], correlacao: list[list[float]],
           confusao_norm: list[list[float]], top: int) -> list[dict[str, Any]]:
    """Para cada par ordenado A->B (A != B): taxa de confusão (IA troca A por B)
    e correlação vocabular (simétrica). Score = média geométrica dos dois sinais,
    realçando pares altos NAS DUAS dimensões."""
    pares = []
    n = len(cats)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            conf = float(confusao_norm[i][j])
            corr = float(correlacao[i][j])
            if conf <= 0 and corr <= 0:
                continue
            score = float(np.sqrt(max(conf, 0.0) * max(corr, 0.0)))
            pares.append({
                "categoria_historica": cats[i],
                "categoria_ia": cats[j],
                "taxa_confusao": round(conf, 4),
                "correlacao_vocabular": round(corr, 4),
                "score_revisao": round(score, 4),
            })
    pares.sort(key=lambda p: p["score_revisao"], reverse=True)
    return pares[:top]


def gravar_json(cats, confusao, cruzamento, corr_gerado, gerado) -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / "confusao_historico_ia.json").write_text(json.dumps({
        "gerado_em": gerado,
        "natureza": "concordancia_IA_x_historico (NAO e acerto validado por humano)",
        "leitura": "linha = categoria historica; coluna = previsao da IA; valor normalizado por linha",
        "categorias": cats,
        "matriz_normalizada": confusao["matriz_normalizada"],
        "matriz_bruta": confusao["matriz_bruta"],
        "suporte_por_categoria": confusao["suporte_por_categoria"],
        "previsoes_fora_do_conjunto": confusao["previsoes_fora_do_conjunto"],
        "chamados_sem_previsao_ia": confusao["chamados_sem_previsao_ia"],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    (SAIDA / "cruzamento_taxonomia.json").write_text(json.dumps({
        "gerado_em": gerado,
        "natureza": "exploratorio_revisao_taxonomia (prioriza revisao humana; nao funde categorias)",
        "leitura": "score alto = par confundido pela IA E com vocabulario sobreposto -> candidato a fusao/desambiguacao",
        "fonte_correlacao": corr_gerado,
        "candidatos_revisao": cruzamento,
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Cruzamento confusão IA×histórico × correlação vocabular.")
    p.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    p.add_argument("--credenciais", default=None)
    p.add_argument("--top", type=int, default=40, help="Pares no ranking de candidatos.")
    p.add_argument("--min-df", type=int, default=5)
    p.add_argument("--min-chamados-categoria", type=int, default=10)
    p.add_argument("--aplicar", action="store_true", help="Grava aba privada CRUZAMENTO_TAXONOMIA.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    config = rt.carregar_config(args.config)
    gerado = agora_bahia()

    try:
        sh = pl.abrir_planilha(pl.id_planilha(config), args.credenciais)
        ws = sh.worksheet(config["aba_principal"])
        chamados = carregar_chamados(ws, "A:P")
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001
        print(f"Falha ao acessar planilha: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    if len(chamados) < 2:
        print("Informação insuficiente para verificar.")
        return 1

    # Correlação vocabular (mesma rotina da relevância de termos, mesmo conjunto de cats).
    res = rt.calcular(chamados, top_n=10, min_df=args.min_df,
                      min_chamados_categoria=args.min_chamados_categoria)
    cats = res["categorias"]
    correlacao = res["matriz_correlacao"]

    confusao = matriz_confusao(chamados, cats)
    cruzamento = cruzar(cats, correlacao, confusao["matriz_normalizada"], args.top)

    gravar_json(cats, confusao, cruzamento, gerado, gerado)

    print(json.dumps({
        "gerado_em": gerado,
        "n_chamados": len(chamados),
        "n_categorias": len(cats),
        "chamados_sem_previsao_ia": confusao["chamados_sem_previsao_ia"],
        "previsoes_fora_do_conjunto": confusao["previsoes_fora_do_conjunto"],
        "top_candidatos_revisao": cruzamento[:5],
        "json": ["docs/dados/confusao_historico_ia.json", "docs/dados/cruzamento_taxonomia.json"],
        "modo": "aplicar" if args.aplicar else "dry-run",
    }, ensure_ascii=False, indent=2))

    if not args.aplicar:
        print("modo=dry-run (JSON gerados; nada gravado na planilha).")
        return 0

    cab = ["categoria_historica", "categoria_ia", "taxa_confusao",
           "correlacao_vocabular", "score_revisao", "data_execucao"]
    linhas = [[c["categoria_historica"], c["categoria_ia"], c["taxa_confusao"],
               c["correlacao_vocabular"], c["score_revisao"], gerado] for c in cruzamento]
    pl.escrever_aba(sh, ABA_SAIDA, cab, linhas)
    print(f"OK: aba {ABA_SAIDA} gravada com {len(linhas)} linhas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
