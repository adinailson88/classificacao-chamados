#!/usr/bin/env python3
"""Figuras dos termos de maior peso por categoria (Trilha B).

Treina o LinearSVC sobre palavras (1-2) e caracteres do corte B, a partir de uma
copia local do snapshot (privada), e desenha, para cada categoria, as palavras que
mais empurram o chamado para ela e as que mais empurram para longe. As categorias
saem em ordem decrescente de frequencia, ``--por-pagina`` por figura. So os PNG vao
para o repositorio e apenas depois de revisados, porque os termos vem do texto dos
chamados; ``--termos-txt`` grava a lista para essa revisao, fora do repositorio. O
modelo e treinado no corte inteiro para estabilizar os pesos, entao as figuras
descrevem o que o modelo aprende, nao seu desempenho.

Uso: python src/figuras_pesos_trilha_b.py --snapshot-json snapshot.json docs/trilha_b/figuras
"""

from __future__ import annotations

import argparse
import sys
import textwrap
from collections import Counter
from pathlib import Path
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))


def termos_de_maior_peso(pesos: Sequence[float], nomes: Sequence[str], n_palavras: int,
                         positivos: int = 6, negativos: int = 3
                         ) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
    """Maiores pesos positivos e negativos entre as primeiras ``n_palavras`` colunas."""
    idx = sorted(range(n_palavras), key=lambda i: pesos[i])
    pos = [(nomes[i], float(pesos[i])) for i in reversed(idx[-positivos:])]
    neg = [(nomes[i], float(pesos[i])) for i in idx[:negativos]]
    return pos, neg


def paginar(itens: Sequence, por_pagina: int) -> list[list]:
    return [list(itens[i:i + por_pagina]) for i in range(0, len(itens), por_pagina)]


def numero(v: float) -> str:
    return f"{v:+.2f}".replace(".", ",").replace("-", "−")


def desenhar(paineis: list[dict], saida: Path, colunas: int = 2, linhas: int = 3) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.family": "serif", "font.size": 9,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, axs = plt.subplots(linhas, colunas, figsize=(7.2, 2.9 * linhas), squeeze=False)
    alvos = axs.ravel()
    for ax in alvos[len(paineis):]:
        ax.axis("off")
    for ax, p in zip(alvos, paineis):
        itens = [(t, v, "#1f4e79") for t, v in p["pos"]] + [(t, v, "#c0504d") for t, v in p["neg"]]
        ys = list(range(len(itens)))[::-1]
        ax.barh(ys, [v for _, v, _ in itens], color=[c for _, _, c in itens], height=0.65)
        ax.set_yticks(ys)
        ax.set_yticklabels([t for t, _, _ in itens], fontsize=7.5)
        for y, (_, v, _) in zip(ys, itens):
            ax.text(v + (0.04 if v >= 0 else -0.04), y, numero(v), va="center",
                    ha="left" if v >= 0 else "right", fontsize=7)
        ax.axvline(0, color="#444444", lw=0.6)
        ax.set_xlim(-1.3, 2.6)
        titulo = "\n".join(textwrap.wrap(f"{p['titulo']} (n = {p['n']:,})".replace(",", "."), 46))
        ax.set_title(titulo, fontsize=8, loc="left")
        ax.tick_params(axis="x", labelsize=7)
    fig.supxlabel("peso no LinearSVC (positivo empurra o chamado para a categoria)", fontsize=8)
    fig.tight_layout()
    saida.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(saida, dpi=300)
    plt.close(fig)


def main() -> int:
    import json
    from sklearn.svm import LinearSVC

    import modelos_alternativos as ma
    import trilha_b as tb

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("saida", type=Path)
    p.add_argument("--snapshot-json", type=Path, required=True)
    p.add_argument("--por-pagina", type=int, default=6)
    p.add_argument("--termos-txt", type=Path, default=None,
                   help="grava os termos para revisao (nao versionar)")
    args = p.parse_args()

    manifesto = json.loads(tb.MANIFESTO_B.read_text(encoding="utf-8"))
    linhas = tb.ler_snapshot_json(args.snapshot_json)
    tb.verificar_snapshot(linhas, manifesto)
    corpus = tb.preparar_corpus(tb.registros_do_snapshot(linhas), tb.carregar_particoes_b())
    vec = ma.vetorizador_ngramas()
    X = vec.fit_transform(corpus["textos"])
    clf = LinearSVC(class_weight="balanced", random_state=42).fit(X, corpus["rotulos"])
    nomes = [n.split("__", 1)[-1] for n in vec.get_feature_names_out()]
    n_palavras = len(vec.transformer_list[0][1].vocabulary_)
    cont = Counter(corpus["rotulos"])
    classes = list(clf.classes_)
    paineis = []
    for cat, n in cont.most_common():
        pos, neg = termos_de_maior_peso(clf.coef_[classes.index(cat)], nomes, n_palavras)
        paineis.append({"titulo": cat, "n": n, "pos": pos, "neg": neg})
    if args.termos_txt:
        args.termos_txt.write_text("\n".join(
            f"{q['titulo']} | + {[t for t, _ in q['pos']]} | - {[t for t, _ in q['neg']]}"
            for q in paineis), encoding="utf-8")
    paginas = paginar(paineis, args.por_pagina)
    for k, pagina in enumerate(paginas, 1):
        desenhar(pagina, args.saida / f"figura_5_pesos_termos_{k:02d}.png",
                 linhas=(len(pagina) + 1) // 2 if len(pagina) < args.por_pagina else args.por_pagina // 2)
    print(f"ok: {len(paginas)} figuras, {len(paineis)} categorias")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
