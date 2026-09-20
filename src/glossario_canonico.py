#!/usr/bin/env python3
"""Glossario de termos caracteristicos (log-odds) restrito ao CORPUS CANONICO
do ARTIGO_CONGELADO (n=13.972, 41 categorias) -- nao ao corpus operacional
vivo que src/relevancia_termos.py usa por padrao.

Motivacao: o artigo relata acuracia/F1 sobre as 13.972 linhas das particoes
canonicas (docs/dados/particoes_canonicas_mapa.csv), com CATEGORIA DE
REFERENCIA REVISADA (M/N/P + coluna manual Q), nao a categoria historica do
GLPI. Uma tabela de apendice sobre vocabulario por categoria so e
cientificamente comparavel ao resto do artigo se usar exatamente o mesmo
subconjunto de linhas e o mesmo rotulo -- por isso este script:

1. Le a planilha viva (READ-ONLY) com a mesma extracao de
   construir_grupos_textuais.ler_registros();
2. Filtra para as linhas cujo SHA-256 do ID esta em
   particoes_canonicas_mapa.csv (as 13.972 do corpus de modelagem);
3. Rotula cada linha com referencia_humana() (regra M/N/P/Q congelada),
   igual a Tabela A2 do artigo -- nao a categoria historica (coluna C);
4. Falha (fail-closed) se a contagem final != 13.972 ou categorias != 41:
   sinal de que a planilha viva divergiu do corpus congelado desde o
   Passo 2 (grupos_textuais.py ja verifica isso para o hash do corpus
   completo; aqui verifica-se a extremidade -- linhas e categorias do
   subconjunto de modelagem).
5. Reusa o NUCLEO estatistico de relevancia_termos.calcular() (log-odds
   com prior de Dirichlet, Monroe et al. 2008 + correlacao por cosseno),
   sem duplicar a formula.

Saida: imprime o JSON completo em stdout (nao grava em docs/dados/, para
nao confundir com o glossario operacional vivo ja publicado ali).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import construir_grupos_textuais as cgt  # noqa: E402
import planilha as pl  # noqa: E402
import relevancia_termos as rt  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
MAPA_PARTICOES_PADRAO = RAIZ / "docs" / "dados" / "particoes_canonicas_mapa.csv"

N_ESPERADO = 13972
CATEGORIAS_ESPERADAS = 41


def carregar_ids_canonicos(caminho: Path) -> set[str]:
    with caminho.open("r", encoding="utf-8", newline="") as f:
        return {linha["id_sha256"] for linha in csv.DictReader(f) if linha.get("id_sha256")}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Glossario log-odds restrito ao corpus canonico do artigo.")
    p.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    p.add_argument("--credenciais", default=None)
    p.add_argument("--mapa-particoes", type=Path, default=MAPA_PARTICOES_PADRAO)
    p.add_argument("--top-n", type=int, default=15, help="Termos por categoria em cada ranking.")
    p.add_argument("--min-df", type=int, default=5)
    p.add_argument("--min-chamados-categoria", type=int, default=1,
                   help="1 = nao filtra: todas as 41 categorias canonicas entram.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    with args.config.open("r", encoding="utf-8") as f:
        config = json.load(f)

    ids_canonicos = carregar_ids_canonicos(args.mapa_particoes)
    print(f"ids_canonicos_carregados={len(ids_canonicos)}", file=sys.stderr)

    try:
        sh = pl.abrir_planilha(pl.id_planilha(config), args.credenciais)
        registros_brutos = cgt.ler_registros(sh, config)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001
        print(f"Falha ao acessar planilha: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    chamados = []
    for r in registros_brutos:
        digest = hashlib.sha256(r["id"].encode("utf-8")).hexdigest()
        if digest not in ids_canonicos:
            continue
        categoria = cgt.referencia_humana(r)
        if not categoria:
            continue
        partes = [r.get(c, "") for c in cgt.CAMPOS_TEXTUAIS]
        texto = "\n".join(p for p in partes if p)
        if not texto:
            continue
        chamados.append({"linha": None, "categoria": categoria, "texto": texto})

    n = len(chamados)
    cats = sorted({c["categoria"] for c in chamados})
    print(f"corpus_canonico_filtrado: n={n} (esperado {N_ESPERADO}) | "
          f"categorias={len(cats)} (esperado {CATEGORIAS_ESPERADAS})", file=sys.stderr)

    if n != N_ESPERADO or len(cats) != CATEGORIAS_ESPERADAS:
        print(
            "FAIL-CLOSED: o corpus canonico reconstruido da planilha viva nao bate com o "
            f"congelado (n={n} vs {N_ESPERADO}; categorias={len(cats)} vs {CATEGORIAS_ESPERADAS}). "
            "A planilha operacional divergiu do ARTIGO_CONGELADO desde o Passo 2/3; "
            "nao gero o glossario canonico sobre um corpus que nao pode ser provado identico.",
            file=sys.stderr,
        )
        return 3

    res = rt.calcular(chamados, args.top_n, args.min_df, args.min_chamados_categoria)
    saida = {
        "natureza": ("glossario_log_odds_CORPUS_CANONICO (n=13.972; 41 categorias; "
                     "categoria = referencia revisada, igual a Tabela A2 do artigo; "
                     "NAO e metrica de acuracia validada)"),
        "n_corpus": n,
        "n_categorias": len(cats),
        "parametros": res["parametros"],
        "categorias": res["categorias"],
        "termos_por_categoria": res["termos_por_categoria"],
        "matriz_correlacao": res["matriz_correlacao"],
        "pares_mais_proximos": res["pares_mais_proximos"],
    }
    print("===JSON_INICIO===")
    print(json.dumps(saida, ensure_ascii=False))
    print("===JSON_FIM===")
    print(f"OK: glossario canonico calculado | n={n} | categorias={len(cats)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
