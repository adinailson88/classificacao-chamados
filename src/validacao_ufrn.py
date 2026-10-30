#!/usr/bin/env python3
"""Leitura, amostragem e resumo da base publica de requisicoes de manutencao da UFRN.

A base (dados abertos, licenca aberta) tem uma categoria grossa por requisicao
(`divisao`, seis valores) e a descricao livre do servico. Serve como validacao
em outra instituicao: o modelo treinado no corpus da Trilha B preve a categoria
de uma amostra, o autor avalia a previsao e o resultado e comparado com a
`divisao` da UFRN.

Nenhuma coluna de identificacao de pessoa (`usuario`) e lida para a saida, e o
texto da amostra nunca vai para os artefatos versionados.
"""

from __future__ import annotations

import csv
import io
import random
import unicodedata
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

URL_PADRAO = ("https://dados.ufrn.br/dataset/a163b02e-dd02-4c40-bf2e-79b4858c1c80/"
              "resource/1ec4e5c7-d3d4-4741-a58e-d66ce49c04d2/download/"
              "requisicaomaterialservico.csv")
COLUNAS_USADAS = ("numero", "ano", "divisao", "descricao", "local")

# Hipotese de correspondencia entre o primeiro nivel da taxonomia do corpus e a
# `divisao` da UFRN. E proposta, nao verificada: a UFRN nao publica a definicao
# de cada divisao. Niveis sem correspondencia clara ficam de fora da concordancia.
CORRESPONDENCIA_PROPOSTA = {
    "eletrica": "instalacoes eletricas e telecomunicacoes",
    "ti / dados / rede": "instalacoes eletricas e telecomunicacoes",
    "hidrossanitaria": "instalacoes hidraulicas e sanitarias",
    "climatizacao": "ar condicionado",
    "estrutura predial": "servicos gerais",
    "instalacao de acessorios e mobiliario": "servicos gerais",
    "posto de trabalho": "servicos gerais",
    "projetos e reformas": "servicos gerais",
    "area externa e ambiental": "viario",
    "outros": "outros",
    "suprimentos / apoio tecnico": "outros",
    "seguranca contra incendio": "outros",
    "equipamentos de transporte": "outros",
}


def chave(texto: str) -> str:
    sem = unicodedata.normalize("NFKD", str(texto or ""))
    return "".join(c for c in sem if not unicodedata.combining(c)).strip().lower()


def ler_ufrn(origem: str | Path, tempo_limite: int = 600) -> list[dict[str, str]]:
    """Le o CSV (URL ou arquivo) mantendo so as colunas necessarias."""
    if str(origem).startswith("http"):
        with urllib.request.urlopen(str(origem), timeout=tempo_limite) as resposta:
            conteudo = resposta.read().decode("utf-8-sig")
    else:
        conteudo = Path(origem).read_text(encoding="utf-8-sig")
    csv.field_size_limit(10 ** 8)
    leitor = csv.DictReader(io.StringIO(conteudo, newline=""), delimiter=";")
    faltando = [c for c in COLUNAS_USADAS if c not in (leitor.fieldnames or [])]
    if faltando:
        raise RuntimeError(f"CSV da UFRN sem as colunas: {faltando}")
    return [{c: (linha.get(c) or "").strip() for c in COLUNAS_USADAS} for linha in leitor]


def amostrar(linhas: list[dict[str, str]], por_divisao: int = 300, ano_minimo: int = 2022,
             palavras_minimas: int = 4, semente: int = 42) -> list[dict[str, str]]:
    """Amostra estratificada por `divisao`, sem texto repetido e sem descricao curta."""
    vistos: set[str] = set()
    por_classe: dict[str, list[dict[str, str]]] = defaultdict(list)
    for linha in sorted(linhas, key=lambda r: (r["ano"], r["numero"])):
        if not linha["divisao"] or not linha["ano"].isdigit() or int(linha["ano"]) < ano_minimo:
            continue
        if len(linha["descricao"].split()) < palavras_minimas:
            continue
        k = chave(linha["descricao"])
        if k in vistos:
            continue
        vistos.add(k)
        por_classe[linha["divisao"]].append(linha)
    rng = random.Random(semente)
    amostra: list[dict[str, str]] = []
    for classe in sorted(por_classe):
        itens = por_classe[classe]
        amostra.extend(rng.sample(itens, min(por_divisao, len(itens))))
    rng.shuffle(amostra)
    for linha in amostra:
        linha["id_ufrn"] = f"{linha['ano']}-{linha['numero']}"
    return amostra


def nivel_um(categoria: str) -> str:
    return chave(str(categoria).split(">")[0])


def resumir(amostra: list[dict[str, str]], previsoes: dict[str, list[str]]) -> dict[str, Any]:
    """Concordancia sob a correspondencia proposta e matriz nivel 1 x `divisao`.

    `previsoes` mapeia o nome do modelo a uma lista de categorias na ordem da amostra.
    """
    divisoes = [chave(a["divisao"]) for a in amostra]
    saida: dict[str, Any] = {
        "n_amostra": len(amostra),
        "por_divisao": dict(sorted(Counter(a["divisao"] for a in amostra).items())),
        "correspondencia_proposta": CORRESPONDENCIA_PROPOSTA, "modelos": {}}
    for nome, prev in previsoes.items():
        niveis = [nivel_um(p) for p in prev]
        com_mapa = [(n, d) for n, d in zip(niveis, divisoes) if n in CORRESPONDENCIA_PROPOSTA]
        acertos = sum(1 for n, d in com_mapa if CORRESPONDENCIA_PROPOSTA[n] == d)
        por_classe: dict[str, dict[str, Any]] = {}
        for classe in sorted(set(divisoes)):
            itens = [(n, d) for n, d in com_mapa if d == classe]
            ok = sum(1 for n, d in itens if CORRESPONDENCIA_PROPOSTA[n] == d)
            por_classe[classe] = {"n": len(itens),
                                  "concordancia": round(ok / len(itens), 4) if itens else None}
        matriz: dict[str, dict[str, int]] = defaultdict(dict)
        for n, d in zip(niveis, divisoes):
            matriz[d][n] = matriz[d].get(n, 0) + 1
        saida["modelos"][nome] = {
            "previsoes_sem_correspondencia": len(niveis) - len(com_mapa),
            "concordancia_com_correspondencia": (round(acertos / len(com_mapa), 4)
                                                 if com_mapa else None),
            "n_com_correspondencia": len(com_mapa),
            "por_divisao": por_classe,
            "matriz_nivel1_por_divisao": {d: dict(sorted(v.items(), key=lambda kv: -kv[1]))
                                          for d, v in sorted(matriz.items())},
        }
    return saida


def concorda(categoria: str, divisao: str) -> str:
    """'S', 'N' ou '' (sem correspondencia) para uma previsao contra a `divisao`."""
    alvo = CORRESPONDENCIA_PROPOSTA.get(nivel_um(categoria))
    if alvo is None:
        return ""
    return "S" if alvo == chave(divisao) else "N"
