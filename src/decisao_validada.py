#!/usr/bin/env python3
"""Memoria de DECISAO a partir das conferencias humanas (M/N/P) da aba principal.

Regra definida pelo pesquisador (2026-06-10):
- se o humano conferiu uma categoria (do historico, da IA ou da reclassificacao)
  como ERRADA, essa categoria fica ELIMINADA para aquele chamado — nenhuma decisao
  automatica pode repeti-la;
- se o humano conferiu uma categoria como CERTA, a decisao fica TRAVADA — o fluxo
  reusa a categoria decidida e nao gasta tempo/memoria reprocessando o chamado.

Colunas na CHAMADOS_ESQUELETO_REDUZIDO (1-based):
- C (3)  CATEGORIA COMPLETA      <- conferida pela coluna M (13, CONFERENCIA GLPI)
- G (7)  Classificacao IA        <- conferida pela coluna N (14, CONFERENCIA IA)
- O (15) Classificacao IA - 2    <- conferida pela coluna P (16, CONFERENCIA IA - 2)
'Correto' = acerto; qualquer outro valor nao vazio = 'Errado'; vazio = nao conferido
(mesma convencao de planilha.ler_conferencias).

Este modulo e READ-ONLY: nao escreve na planilha e nao altera o historico.
"""

from __future__ import annotations

from typing import Any

STATUS_DECIDIDO = "decidido"
STATUS_RESTRITO = "restrito"
STATUS_SEM_VALIDACAO = "sem_validacao"


def _norm_veredito(valor: Any) -> str | None:
    s = str(valor or "").strip()
    if not s:
        return None
    return "Correto" if s.casefold() == "correto" else "Errado"


def decidir(historico: str, ia1: str, reclass: str,
            v_glpi: str | None, v_ia: str | None, v_reclass: str | None) -> dict[str, Any]:
    """Aplica a regra de memoria a UM chamado. Logica pura (testavel offline).

    Retorna:
    - decidida: categoria travada pela conferencia (ou None);
    - fonte_decisao: qual conferencia travou ('conferencia_ia' > 'conferencia_glpi'
      > 'conferencia_reclass', nesta ordem de precedencia quando ha mais de uma);
    - eliminadas: categorias ja conferidas como erradas (nao repetir);
    - conflito: True quando duas conferencias 'Correto' apontam categorias
      DIFERENTES (impossivel; devolvido para revisao humana, sem decisao);
    - status: decidido | restrito | sem_validacao.
    """
    historico = str(historico or "").strip()
    ia1 = str(ia1 or "").strip()
    reclass = str(reclass or "").strip()

    corretas: list[tuple[str, str]] = []   # (categoria, fonte)
    eliminadas: set[str] = set()
    if v_glpi == "Correto" and historico:
        corretas.append((historico, "conferencia_glpi"))
    elif v_glpi == "Errado" and historico:
        eliminadas.add(historico)
    if v_ia == "Correto" and ia1:
        corretas.append((ia1, "conferencia_ia"))
    elif v_ia == "Errado" and ia1:
        eliminadas.add(ia1)
    if v_reclass == "Correto" and reclass:
        corretas.append((reclass, "conferencia_reclass"))
    elif v_reclass == "Errado" and reclass:
        eliminadas.add(reclass)

    conflito = len({c for c, _ in corretas}) > 1
    decidida = fonte = None
    if corretas and not conflito:
        # Precedencia apenas para REGISTRO da fonte; as categorias sao iguais.
        ordem = {"conferencia_ia": 0, "conferencia_glpi": 1, "conferencia_reclass": 2}
        decidida, fonte = sorted(corretas, key=lambda cf: ordem[cf[1]])[0]
        # Categoria decidida nunca pode constar como eliminada (conferencias se
        # referem a colunas distintas; ex.: M=Errado e N=Correto com C != G).
        eliminadas.discard(decidida)

    if decidida:
        status = STATUS_DECIDIDO
    elif eliminadas or conflito:
        status = STATUS_RESTRITO
    else:
        status = STATUS_SEM_VALIDACAO

    return {"decidida": decidida, "fonte_decisao": fonte, "eliminadas": eliminadas,
            "conflito": conflito, "status": status,
            "historico": historico, "ia1": ia1, "reclass": reclass}


def carregar_decisoes(sh, aba_principal: str,
                      col_historico: int = 3, col_ia1: int = 7, col_reclass: int = 15,
                      col_conf_glpi: int = 13, col_conf_ia: int = 14,
                      col_conf_reclass: int = 16) -> dict[int, dict[str, Any]]:
    """Le a aba principal UMA vez (A:P) e monta a memoria de decisao por linha.

    Retorna {linha_planilha (int, 1-based): decisao} apenas para linhas com pelo
    menos uma conferencia preenchida. Linhas sem conferencia ficam fora do mapa
    (status implicitamente 'sem_validacao').
    """
    cols = [col_historico, col_ia1, col_reclass, col_conf_glpi, col_conf_ia, col_conf_reclass]
    hi = max(cols)

    def letra(n: int) -> str:
        s = ""
        while n > 0:
            n, r = divmod(n - 1, 26)
            s = chr(65 + r) + s
        return s

    try:
        ws = sh.worksheet(aba_principal)
        bloco = ws.get_values(f"A1:{letra(hi)}", value_render_option="UNFORMATTED_VALUE")
    except Exception:  # noqa: BLE001
        return {}

    def cel(linha: list[Any], c1: int) -> str:
        i = c1 - 1
        return str(linha[i] or "").strip() if len(linha) > i else ""

    out: dict[int, dict[str, Any]] = {}
    for pos, linha in enumerate(bloco[1:], start=2):
        v_glpi = _norm_veredito(cel(linha, col_conf_glpi))
        v_ia = _norm_veredito(cel(linha, col_conf_ia))
        v_reclass = _norm_veredito(cel(linha, col_conf_reclass))
        if v_glpi is None and v_ia is None and v_reclass is None:
            continue
        out[pos] = decidir(cel(linha, col_historico), cel(linha, col_ia1),
                           cel(linha, col_reclass), v_glpi, v_ia, v_reclass)
    return out


def verdade_validada(decisoes: dict[int, dict[str, Any]]) -> dict[int, str]:
    """{linha: categoria decidida} apenas dos chamados com decisao travada."""
    return {ln: d["decidida"] for ln, d in decisoes.items() if d.get("decidida")}


def resumo_decisoes(decisoes: dict[int, dict[str, Any]]) -> dict[str, Any]:
    dec = sum(1 for d in decisoes.values() if d["status"] == STATUS_DECIDIDO)
    res = sum(1 for d in decisoes.values() if d["status"] == STATUS_RESTRITO)
    conf = sum(1 for d in decisoes.values() if d.get("conflito"))
    return {"com_conferencia": len(decisoes), "decididos": dec,
            "restritos": res, "conflitos": conf}
