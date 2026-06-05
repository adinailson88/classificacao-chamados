#!/usr/bin/env python3
"""Memoria de treino validada a partir da aba VALIDACAO_HUMANA.

A memoria so usa linhas revisadas manualmente com:
- categoria_validada preenchida;
- usar_para_treino = SIM.

Enquanto nao houver validacao humana, retorna lista vazia. Assim o fluxo fica
pronto para aprender com a revisao sem inventar rotulos ou misturar dados
incertos no treino.
"""

from __future__ import annotations

from collections import Counter
from typing import Any


def _norm(valor: Any) -> str:
    return " ".join(str(valor or "").split()).casefold()


def _cel(linha: list[Any], idx: int | None) -> str:
    return str(linha[idx] or "").strip() if idx is not None and idx < len(linha) else ""


def montar_texto_validacao(linha: list[Any], idx: dict[str, int | None]) -> str:
    partes = [
        _cel(linha, idx.get("titulo")),
        _cel(linha, idx.get("descricao_glpi")),
        _cel(linha, idx.get("titulo_osm")),
        _cel(linha, idx.get("descricao_osm")),
    ]
    return "\n".join(p for p in partes if p)


def carregar_memoria_validada(sh, aba_validacao: str) -> list[dict[str, str]]:
    """Le a aba VALIDACAO_HUMANA e retorna exemplos confiaveis de treino."""
    try:
        vals = sh.worksheet(aba_validacao).get_all_values()
    except Exception:  # noqa: BLE001
        return []
    if len(vals) < 2:
        return []

    cab = vals[0]
    mapa = {_norm(nome): i for i, nome in enumerate(cab)}
    idx = {
        "linha_planilha": mapa.get(_norm("linha_planilha")),
        "id_chamado": mapa.get(_norm("id_chamado")),
        "titulo": mapa.get(_norm("titulo")),
        "descricao_glpi": mapa.get(_norm("descricao_glpi")),
        "titulo_osm": mapa.get(_norm("titulo_osm")),
        "descricao_osm": mapa.get(_norm("descricao_osm")),
        "categoria_validada": mapa.get(_norm("categoria_validada")),
        "decisao": mapa.get(_norm("decisao")),
        "usar_para_treino": mapa.get(_norm("usar_para_treino")),
    }

    memoria = []
    vistos = set()
    for linha in vals[1:]:
        usar = _cel(linha, idx["usar_para_treino"]).upper()
        categoria = _cel(linha, idx["categoria_validada"])
        texto = montar_texto_validacao(linha, idx)
        if usar != "SIM" or not categoria or not texto:
            continue
        chave = (_cel(linha, idx["linha_planilha"]), _cel(linha, idx["id_chamado"]), categoria)
        if chave in vistos:
            continue
        vistos.add(chave)
        memoria.append({
            "linha_planilha": chave[0],
            "id_chamado": chave[1],
            "texto": texto,
            "categoria": categoria,
            "decisao": _cel(linha, idx["decisao"]),
            "origem": "VALIDACAO_HUMANA",
        })
    return memoria


def expandir_treino_com_memoria(
    textos: list[str],
    categorias: list[str],
    memoria: list[dict[str, str]],
    peso: int = 3,
) -> tuple[list[str], list[str]]:
    """Duplica exemplos validados para dar mais peso aos rotulos revisados."""
    peso = max(1, int(peso or 1))
    if not memoria:
        return list(textos), list(categorias)
    textos_out = list(textos)
    cats_out = list(categorias)
    for item in memoria:
        for _ in range(peso):
            textos_out.append(item["texto"])
            cats_out.append(item["categoria"])
    return textos_out, cats_out


def resumir_memoria(memoria: list[dict[str, str]]) -> dict[str, Any]:
    contagem = Counter(item["categoria"] for item in memoria)
    return {
        "exemplos_validados": len(memoria),
        "categorias_validadas": len(contagem),
        "top_categorias": contagem.most_common(10),
    }
