"""Aplica correções aprovadas, por ID, com leitura antes e depois do PUT."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import glpi_client as gc  # noqa: E402
import planilha as pl  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]


def aprovado(valor):
    return valor is True


def mapa_categorias(categorias):
    """Indexa nomes completos sem aproximar ou escolher duplicatas."""
    por_nome, por_id = {}, {}
    for item in categorias:
        if not isinstance(item, dict) or not str(item.get("id", "")).isdigit():
            raise ValueError("ITILCategory inválida")
        nome = str(item.get("completename") or "").strip()
        if not nome:
            raise ValueError("ITILCategory sem completename")
        por_nome.setdefault(nome, []).append(item)
        por_id[int(item["id"])] = item
    return por_nome, por_id


def _data():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def executar_linha(linha, cliente, por_nome, por_id, *, aplicar=False, fonte_valida=True):
    """Retorna cópia auditável. Nunca faz PUT sem aprovação e todos os gates."""
    saida = dict(linha)
    if saida.get("status_glpi") in ("APLICADO", "JA_APLICADO"):
        return saida
    if not aprovado(saida.get("aprovado_glpi")):
        return saida
    if saida.get("situacao_validacao") != "ELEGIVEL":
        saida.update(status_glpi="BLOQUEADO_VALIDACAO", erro="Validação humana conflitante")
        return saida
    ticket_id = str(saida.get("id_chamado") or "").strip()
    destino_nome = str(saida.get("categoria_correta") or "").strip()
    origem_nome = str(saida.get("categoria_glpi_planilha") or "").strip()
    if not ticket_id.isdigit() or not origem_nome or not destino_nome:
        saida.update(status_glpi="ERRO", erro="ID ou categorias ausentes")
        return saida
    try:
        destino_lista = por_nome.get(destino_nome, [])
        if len(destino_lista) != 1:
            situacao = "inexistente" if not destino_lista else "ambígua"
            saida.update(status_glpi="BLOQUEADO_CATEGORIA", erro=f"Categoria de destino {situacao}")
            return saida
        destino = destino_lista[0]
        destino_id = int(destino["id"])
        ticket = cliente.ticket(ticket_id)
        if not isinstance(ticket, dict):
            saida.update(status_glpi="ERRO", erro="Ticket inexistente")
            return saida
        if str(ticket.get("id")) != ticket_id:
            saida.update(status_glpi="ERRO", erro="ID da resposta divergente")
            return saida
        atual_id = int(ticket.get("itilcategories_id") or 0)
        atual = por_id.get(atual_id)
        saida["categoria_api_antes"] = str(atual.get("completename")) if atual else f"ID:{atual_id}"
        if atual_id == destino_id:
            saida.update(status_glpi="JA_APLICADO", categoria_api_depois=destino_nome,
                         data_execucao=_data(), erro="")
            return saida
        if not fonte_valida:
            saida.update(status_glpi="BLOQUEADO_VALIDACAO", erro="Fonte atual não confirma o snapshot aprovado")
            return saida
        if atual is None or str(atual.get("completename")) != origem_nome:
            saida.update(status_glpi="BLOQUEADO_DIVERGENCIA", erro="Categoria atual diverge da origem aprovada")
            return saida
        tipo = int(ticket.get("type") or 0)
        campo = {1: "is_incident", 2: "is_request"}.get(tipo)
        if not campo or str(destino.get(campo)) not in ("1", "True", "true"):
            saida.update(status_glpi="BLOQUEADO_TIPO", erro="Categoria incompatível ou tipo não verificável")
            return saida
        if not aplicar:
            saida.update(status_glpi="DRY_RUN", categoria_api_depois=destino_nome, erro="")
            return saida
        erro_put = ""
        try:
            resposta = cliente.corrigir_ticket(ticket_id, destino_id)
            if not isinstance(resposta, list) or not any(
                isinstance(item, dict) and str(item.get("id")) in (ticket_id, "True")
                for item in resposta
            ):
                erro_put = "PUT sem confirmação para o Ticket"
        except gc.GLPIError as exc:
            erro_put = str(exc)
        # Mesmo uma resposta de erro pode ocorrer depois de o servidor gravar.
        # A leitura posterior é obrigatória para toda tentativa de PUT.
        posterior = cliente.ticket(ticket_id)
        saida["categoria_api_depois"] = (
            str(por_id[int(posterior.get("itilcategories_id") or 0)].get("completename"))
            if isinstance(posterior, dict) and int(posterior.get("itilcategories_id") or 0) in por_id
            else ""
        )
        saida["data_execucao"] = _data()
        if erro_put or not isinstance(posterior, dict) or int(posterior.get("itilcategories_id") or 0) != destino_id:
            saida.update(status_glpi="ERRO", erro=erro_put or "GET posterior diferente do destino")
        else:
            saida.update(status_glpi="APLICADO", erro="")
    except (gc.GLPIError, ValueError, TypeError, KeyError) as exc:
        # A mensagem da exceção nunca inclui corpo HTTP, URL com token ou título.
        saida.update(status_glpi="ERRO", erro=str(exc)[:160], data_execucao=_data())
    return saida


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aplicar", action="store_true", help="Habilita PUT e grava resultados na fila")
    parser.add_argument("--teste", action="store_true", help="Autentica e lê API/planilha, sem PUT")
    parser.add_argument("--ids", help="IDs explicitamente selecionados, separados por vírgula")
    parser.add_argument("--limite", type=int, default=0, help="Máximo de aprovados neste lote")
    parser.add_argument("--credenciais")
    args = parser.parse_args(argv)
    if args.teste and args.aplicar:
        parser.error("--teste e --aplicar são mutuamente exclusivos")
    if args.limite < 0:
        parser.error("--limite deve ser não negativo")
    ids = None if not args.ids else {v.strip() for v in args.ids.split(",")}
    if ids is not None and (not ids or any(not v.isdigit() for v in ids)):
        parser.error("--ids exige IDs numéricos")
    if ids is not None and args.limite and len(ids) > args.limite:
        parser.error("--ids excede --limite")
    import gerar_fila_correcoes_glpi as fila
    config = json.loads((RAIZ / "config_experimento.json").read_text(encoding="utf-8"))
    sh = pl.abrir_planilha(pl.id_planilha(config), args.credenciais)
    linhas = fila.ler_fila(sh)
    bloco_fonte = pl.ler_valores(sh.worksheet(config["aba_principal"]), "A:Q")
    candidatos_atuais = {x["id_chamado"]: x for x in fila.selecionar_candidatos(bloco_fonte)}
    selecionadas = [x for x in linhas if aprovado(x.get("aprovado_glpi"))
                    and (ids is None or str(x.get("id_chamado")) in ids)]
    if ids is not None and {str(x["id_chamado"]) for x in selecionadas} != ids:
        parser.error("Um ou mais IDs solicitados não têm aprovação TRUE na fila")
    if args.limite:
        selecionadas = selecionadas[:args.limite]
    contagem = Counter()
    with gc.GLPIClient.from_env() as cliente:
        por_nome, por_id = mapa_categorias(cliente.categorias())
        for linha in selecionadas:
            atual = candidatos_atuais.get(str(linha["id_chamado"]))
            valida = (atual is not None and atual["situacao_validacao"] == "ELEGIVEL"
                      and atual["categoria_glpi_planilha"] == linha["categoria_glpi_planilha"]
                      and atual["categoria_correta"] == linha["categoria_correta"])
            resultado = executar_linha(linha, cliente, por_nome, por_id,
                                      aplicar=args.aplicar, fonte_valida=valida)
            contagem[resultado.get("status_glpi") or "SEM_STATUS"] += 1
            if args.aplicar and resultado != linha:
                fila.atualizar_resultado(sh, resultado)
    print(json.dumps({"selecionados": len(selecionadas), "status": dict(contagem)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
