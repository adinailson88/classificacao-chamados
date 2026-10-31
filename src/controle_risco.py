#!/usr/bin/env python3
"""Automacao seletiva com controle de risco de amostra finita.

Dado um escore de confianca por chamado e o indicador de acerto, escolhe o menor limiar
de confianca cujo erro entre os chamados automatizados fica abaixo de ``alfa`` com
probabilidade de pelo menos ``1 - delta``, sem supor calibracao nem distribuicao do escore.

O procedimento e o *Learn-then-Test* (Angelopoulos et al., 2021) com correcao de Bonferroni:
para cada limiar ``t`` de uma grade fixada so pelos escores, testa-se H0: risco(t) > alfa com
o teste binomial exato sobre os ``m`` chamados com escore >= ``t`` e os ``k`` erros
observados, a nivel ``delta`` dividido pelo tamanho da grade; fica o limiar de maior
cobertura entre os que rejeitam H0. O limiar
devolvido controla o risco condicional a automacao sob a hipotese de trocabilidade entre
a amostra de calibracao e a de uso. Quando ha chamados de texto repetido, a calibracao
deve usar um representante por grupo (``um_por_grupo``), porque linhas dependentes
tornariam o teste binomial otimista.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from scipy.stats import beta, binom


def um_por_grupo(grupos: Sequence[str]) -> list[int]:
    """Indices do primeiro registro de cada grupo, na ordem de aparicao."""
    vistos: set[str] = set()
    saida: list[int] = []
    for i, g in enumerate(grupos):
        if g not in vistos:
            vistos.add(g)
            saida.append(i)
    return saida


def escolher_limiar(escores: Sequence[float], acertos: Sequence[bool], alfa: float = 0.05,
                    delta: float = 0.05, passos: int = 20) -> float | None:
    """Limiar de maior cobertura cujo teste binomial passa, com correcao de Bonferroni.

    A grade de limiares e fixada so pelos escores (niveis de cobertura 1/passos, 2/passos,
    ..., 1), sem olhar os acertos; assim a uniao dos ``passos`` testes, cada um a nivel
    ``delta / passos``, controla a probabilidade de aceitar um limiar de risco maior que
    ``alfa``. Devolve ``None`` se nenhum limiar passa.
    """
    if len(escores) != len(acertos):
        raise ValueError("escores e acertos devem ter o mesmo tamanho")
    n = len(escores)
    if n == 0:
        return None
    pares = sorted(zip(escores, acertos), key=lambda p: -p[0])
    melhor: float | None = None
    for i in range(1, passos + 1):
        k_auto = max(1, math.ceil(n * i / passos))
        limiar = pares[k_auto - 1][0]
        auto = [a for e, a in pares if e >= limiar]
        erros = sum(1 for a in auto if not a)
        if float(binom.cdf(erros, len(auto), alfa)) <= delta / passos:
            if melhor is None or limiar < melhor:
                melhor = limiar
    return melhor


def risco_e_cobertura(escores: Sequence[float], acertos: Sequence[bool],
                      limiar: float | None) -> dict[str, float | int | None]:
    """Cobertura e erro entre os automatizados (escore >= limiar) em um conjunto de teste."""
    n = len(escores)
    if limiar is None or n == 0:
        return {"n": n, "automatizados": 0, "cobertura": 0.0, "erro": None}
    auto = [a for e, a in zip(escores, acertos) if e >= limiar]
    erros = sum(1 for a in auto if not a)
    return {"n": n, "automatizados": len(auto), "cobertura": round(len(auto) / n, 4),
            "erro": round(erros / len(auto), 4) if auto else None,
            "erros": erros}


def limite_superior_clopper_pearson(erros: int, n: int, confianca: float = 0.95) -> float:
    """Limite superior unilateral de Clopper-Pearson para a taxa de erro."""
    if n <= 0:
        return 1.0
    if erros >= n:
        return 1.0
    return float(beta.ppf(confianca, erros + 1, n - erros))


def confianca_minima_para_zero_erros(alfa: float, delta: float) -> int:
    """Numero minimo de automatizados sem erro para o teste rejeitar H0."""
    return math.ceil(math.log(delta) / math.log(1 - alfa))


def limiar_ingenuo(escores: Sequence[float], acertos: Sequence[bool], alfa: float = 0.05,
                   passos: int = 20) -> float | None:
    """Limiar de maior cobertura cujo erro EMPIRICO na calibracao e <= alfa (sem garantia).

    E a pratica corrente (fixar o limiar onde a acuracia observada atinge o alvo) e serve de
    comparacao: o erro observado na calibracao subestima o risco futuro por causa da selecao
    do limiar e da mudanca de distribuicao.
    """
    n = len(escores)
    if n == 0 or len(acertos) != n:
        return None
    pares = sorted(zip(escores, acertos), key=lambda p: -p[0])
    melhor: float | None = None
    for i in range(1, passos + 1):
        k_auto = max(1, math.ceil(n * i / passos))
        limiar = pares[k_auto - 1][0]
        auto = [a for e, a in pares if e >= limiar]
        if sum(1 for a in auto if not a) / len(auto) <= alfa:
            if melhor is None or limiar < melhor:
                melhor = limiar
    return melhor
