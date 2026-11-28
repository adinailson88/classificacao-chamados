#!/usr/bin/env python3
"""Tamanho de amostra e sorteio aleatorio de IDs para a avaliacao manual da Trilha B.

O tamanho por estrato vem da margem de erro desejada para uma proporcao, com correcao
para populacao finita:

    n0 = z^2 * p * (1 - p) / e^2        n = n0 / (1 + (n0 - 1) / N)

com p = 0,5 (pior caso) e z = 1,96 (95%). O sorteio e aleatorio simples dentro de cada
estrato, sobre IDs, com semente registrada. Uma amostra ja sorteada pode ser estendida:
os IDs novos saem do restante do estrato, de modo que a uniao continua sendo uma amostra
aleatoria simples.
"""

from __future__ import annotations

import math
import random
from collections.abc import Iterable, Mapping, Sequence

Z95 = 1.96


def tamanho_amostra(populacao: int, margem: float, p: float = 0.5, z: float = Z95) -> int:
    """Menor n que garante a margem de erro (meia largura do IC) em uma populacao finita."""
    if populacao <= 0:
        return 0
    if not 0 < margem < 1:
        raise ValueError("a margem deve estar entre 0 e 1")
    n0 = z * z * p * (1 - p) / margem ** 2
    return min(populacao, math.ceil(n0 / (1 + (n0 - 1) / populacao)))


def margem_estrato(populacao: int, n: int, p: float = 0.5, z: float = Z95) -> float:
    """Meia largura do IC de uma proporcao em um estrato, com correcao finita."""
    if n <= 0 or populacao <= 0:
        return 1.0
    return z * math.sqrt(p * (1 - p) / n * max(0.0, 1 - n / populacao))


def margem_global(populacoes: Mapping[str, int], tamanhos: Mapping[str, int],
                  p: float = 0.5, z: float = Z95) -> float:
    """Meia largura do IC da proporcao global, ponderando cada estrato pelo seu peso real."""
    total = sum(populacoes.values())
    variancia = 0.0
    for estrato, populacao in populacoes.items():
        n = tamanhos.get(estrato, 0)
        if n <= 0:
            return 1.0
        peso = populacao / total
        variancia += peso ** 2 * p * (1 - p) / n * max(0.0, 1 - n / populacao)
    return z * math.sqrt(variancia)


def tamanhos_por_estrato(populacoes: Mapping[str, int], margem: float) -> dict[str, int]:
    return {k: tamanho_amostra(n, margem) for k, n in populacoes.items()}


def sortear_ids(ids_por_estrato: Mapping[str, Sequence[str]], tamanhos: Mapping[str, int],
                semente: int, ja_sorteados: Iterable[str] = ()) -> dict[str, list[str]]:
    """Sorteia IDs aleatoriamente em cada estrato, sem repor os ja sorteados.

    Devolve apenas os IDs NOVOS de cada estrato: os que faltam para chegar ao tamanho
    pedido, contando os `ja_sorteados` que pertencem ao estrato. A ordem de processamento
    dos estratos e a ordenacao dos candidatos sao fixas, entao a semente reproduz o sorteio.
    """
    anteriores = set(ja_sorteados)
    rng = random.Random(semente)
    novos: dict[str, list[str]] = {}
    for estrato in sorted(ids_por_estrato):
        ids = ids_por_estrato[estrato]
        tem = sum(1 for i in ids if i in anteriores)
        faltam = max(0, min(tamanhos.get(estrato, 0), len(ids)) - tem)
        restantes = sorted(i for i in ids if i not in anteriores)
        novos[estrato] = sorted(rng.sample(restantes, min(faltam, len(restantes))))
    return novos
