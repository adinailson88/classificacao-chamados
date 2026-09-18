#!/usr/bin/env python3
"""Materializa por ID a fila privada de correcoes de categoria do GLPI.

A aba principal e somente lida. Sem ``--aplicar``, nenhuma aba e criada ou
alterada. A aprovacao e os campos de execucao pertencem a fila fixa, nunca a
uma linha dinamica da origem.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import gspread

sys.path.insert(0, str(Path(__file__).resolve().parent))
import decisao_validada as dv  # noqa: E402
import planilha as pl  # noqa: E402
from tempo import agora_bahia  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
ABA_FILA = "FILA_CORRECOES_GLPI"

COLUNAS_FILA = (
    "id_chamado", "titulo", "categoria_glpi_planilha", "categoria_correta",
    "situacao_validacao", "aprovado_glpi", "status_glpi",
    "categoria_api_antes", "categoria_api_depois", "data_candidato",
    "data_execucao", "erro",
)
COLUNAS_CANDIDATO = (
    "titulo", "categoria_glpi_planilha", "categoria_correta",
    "situacao_validacao",
)
COLUNAS_AUDITORIA = (
    "status_glpi", "categoria_api_antes", "categoria_api_depois",
    "data_execucao", "erro",
)


def _valor(linha: list[Any], indice: int) -> str:
    return str(linha[indice] or "").strip() if indice < len(linha) else ""


def _id(valor: Any) -> str:
    """Segue a chave normalizada da memoria validada, sem usar numero de linha."""
    return dv._normalizar_id(valor)


def _veredito(valor: Any) -> str | None:
    return dv._norm_veredito(valor)


def _indice(cabecalho: list[Any], *nomes: str) -> int:
    mapa = pl.mapa_cabecalhos(cabecalho)
    for nome in nomes:
        indice = mapa.get(pl.normalizar_cabecalho(nome))
        if indice is not None:
            return indice - 1
    raise ValueError(f"Cabecalho obrigatorio ausente: {nomes[0]}")


def selecionar_candidatos(bloco: list[list[Any]]) -> list[dict[str, Any]]:
    """Seleciona M=Errado, Q preenchida, C!=Q e ID; marca conflitos M/N/P/Q.

    Usa exclusivamente cabecalhos e ID. Categorias passam pelo mesmo mapa
    canonico usado em ``decisao_validada.carregar_decisoes`` antes de decidir.
    """
    if not bloco:
        raise ValueError("A aba principal esta vazia; cabecalhos indisponiveis.")
    cab = bloco[0]
    col = {
        "id": _indice(cab, "ID Chamado", "ID"),
        "titulo": _indice(cab, "TÍTULO", "TITULO"),
        "historico": _indice(cab, "CATEGORIA COMPLETA"),
        "ia": _indice(cab, "Classificação IA", "Classificacao IA"),
        "m": _indice(cab, "CONFERÊNCIA GLPI", "CONFERENCIA GLPI"),
        "n": _indice(cab, "CONFERÊNCIA IA", "CONFERENCIA IA"),
        "reclass": _indice(cab, "Classificação IA - 2", "Classificacao IA - 2"),
        "p": _indice(cab, "CONFERÊNCIA IA - 2", "CONFERENCIA IA - 2"),
        "q": _indice(cab, "CATEGORIA CORRETA MANUAL"),
    }
    candidatos: list[dict[str, Any]] = []
    vistos: set[str] = set()
    for linha in bloco[1:]:
        if not any(str(c or "").strip() for c in linha):
            continue
        ident = _id(linha[col["id"]]) if col["id"] < len(linha) else ""
        if ident:
            if ident in vistos:
                raise ValueError(f"ID Chamado duplicado na aba principal: {ident}")
            vistos.add(ident)
        origem = _valor(linha, col["historico"])
        destino = _valor(linha, col["q"])
        if not ident or _veredito(_valor(linha, col["m"])) != "Errado":
            continue
        if not origem or not destino or origem == destino:
            continue
        decisao = dv.decidir(
            pl.normalizar_categoria(origem),
            pl.normalizar_categoria(_valor(linha, col["ia"])),
            pl.normalizar_categoria(_valor(linha, col["reclass"])),
            _veredito(_valor(linha, col["m"])),
            _veredito(_valor(linha, col["n"])),
            _veredito(_valor(linha, col["p"])),
            pl.normalizar_categoria(destino),
        )
        elegivel = (not decisao["conflito"]
                    and decisao["status"] == dv.STATUS_DECIDIDO
                    and decisao["decidida"] == pl.normalizar_categoria(destino)
                    and pl.normalizar_categoria(origem) != pl.normalizar_categoria(destino))
        candidatos.append({
            "id_chamado": ident,
            "titulo": _valor(linha, col["titulo"]),
            "categoria_glpi_planilha": origem,
            "categoria_correta": destino,
            "situacao_validacao": "ELEGIVEL" if elegivel else "CONFLITO",
        })
    return candidatos


def _aprovado(valor: Any) -> bool:
    return valor is True


def upsert_fila(existentes: list[dict[str, Any]],
                candidatos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Mescla por ID, preservando aprovacoes e trilha de execucao.

    Uma linha aprovada e um snapshot imutavel do alvo autorizado. Se a origem
    mudar, o executor deve detectar divergencia na API, nao trocar o alvo sob
    uma aprovacao antiga. Linhas que somem da fonte tambem permanecem na fila.
    """
    por_id: dict[str, dict[str, Any]] = {}
    ordem: list[str] = []
    for atual in existentes:
        ident = _id(atual.get("id_chamado"))
        if not ident or ident in por_id:
            raise ValueError("Fila existente contem ID vazio ou duplicado.")
        por_id[ident] = {col: atual.get(col, "") for col in COLUNAS_FILA}
        por_id[ident]["id_chamado"] = ident
        ordem.append(ident)
    data = agora_bahia()
    vistos_candidatos: set[str] = set()
    for candidato in candidatos:
        ident = _id(candidato.get("id_chamado"))
        if not ident or ident in vistos_candidatos:
            raise ValueError("Candidatos contem ID vazio ou duplicado.")
        vistos_candidatos.add(ident)
        if ident not in por_id:
            por_id[ident] = {col: "" for col in COLUNAS_FILA}
            por_id[ident].update(candidato)
            por_id[ident]["id_chamado"] = ident
            por_id[ident]["aprovado_glpi"] = False
            por_id[ident]["status_glpi"] = "PENDENTE"
            por_id[ident]["data_candidato"] = data
            ordem.append(ident)
        elif _aprovado(por_id[ident]["aprovado_glpi"]):
            # A aprovacao autoriza o snapshot existente, nao um novo alvo.
            # Qualquer alteracao da origem ou novo conflito bloqueia a execucao
            # sem apagar a checkbox nem a trilha de auditoria.
            atual = por_id[ident]
            mudou = any(atual.get(col, "") != candidato.get(col, "")
                        for col in ("titulo", "categoria_glpi_planilha", "categoria_correta"))
            if mudou or candidato.get("situacao_validacao") != "ELEGIVEL":
                atual["situacao_validacao"] = "CONFLITO"
        else:
            atual = por_id[ident]
            mudou = any(atual.get(col, "") != candidato.get(col, "")
                        for col in COLUNAS_CANDIDATO)
            for col in COLUNAS_CANDIDATO:
                atual[col] = candidato.get(col, "")
            if mudou:
                atual["data_candidato"] = data
                if atual["status_glpi"] == "PENDENTE":
                    atual["erro"] = ""
    for ident in ordem:
        if ident not in vistos_candidatos:
            # M, Q ou C podem mudar na fonte apos uma aprovacao. Conserva a
            # linha por ID, mas nunca deixa um snapshot ausente como elegivel.
            por_id[ident]["situacao_validacao"] = "CONFLITO"
    return [por_id[ident] for ident in ordem]


def ler_fila(sh, nome: str = ABA_FILA) -> list[dict[str, Any]]:
    """Le a aba materializada; aba ausente representa fila vazia."""
    try:
        ws = sh.worksheet(nome)
    except gspread.WorksheetNotFound:
        return []
    bloco = pl.ler_valores(ws, f"A:{pl._coluna_letra(len(COLUNAS_FILA))}")
    if not bloco:
        return []
    if list(bloco[0][:len(COLUNAS_FILA)]) != list(COLUNAS_FILA):
        raise ValueError("Cabecalho da fila difere do esquema esperado.")
    saida: list[dict[str, Any]] = []
    vistos: set[str] = set()
    for valores in bloco[1:]:
        if not any(str(v or "").strip() for v in valores):
            continue
        ident = _id(valores[0] if valores else "")
        if not ident or ident in vistos:
            raise ValueError("Fila contem ID vazio ou duplicado.")
        vistos.add(ident)
        registro = {col: valores[i] if i < len(valores) else ""
                    for i, col in enumerate(COLUNAS_FILA)}
        registro["id_chamado"] = ident
        saida.append(registro)
    return saida


def escrever_fila(sh, linhas: list[dict[str, Any]], nome: str = ABA_FILA) -> int:
    """Grava por ID na aba fixa, sem escrever a checkbox de IDs existentes."""
    try:
        ws = sh.worksheet(nome)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=nome, rows=max(len(linhas) + 10, 100),
                              cols=len(COLUNAS_FILA))
    atuais = ler_fila(sh, nome)
    cab = ws.row_values(1)
    if not cab:
        ws.update(range_name="A1", values=[list(COLUNAS_FILA)], value_input_option="RAW")
        ws.freeze(rows=1)
    elif cab[:len(COLUNAS_FILA)] != list(COLUNAS_FILA):
        raise ValueError("Cabecalho da fila difere do esquema esperado.")
    # Rele as posicoes fisicas, pois uma linha vazia inserida manualmente nao
    # pode deslocar a aprovacao para outro ID.
    bloco_atual = pl.ler_valores(ws, "A:A")
    posicoes = {_id(valores[0]): pos for pos, valores in enumerate(bloco_atual[1:], start=2)
                if valores and _id(valores[0])}
    ids_atuais = {item["id_chamado"] for item in atuais}
    proxima_linha = max(len(bloco_atual) + 1, max(posicoes.values(), default=1) + 1)
    dados: list[dict[str, Any]] = []
    aprovacao = COLUNAS_FILA.index("aprovado_glpi")
    ids: set[str] = set()
    for item in linhas:
        ident = _id(item.get("id_chamado"))
        if not ident or ident in ids:
            raise ValueError("Saida contem ID vazio ou duplicado.")
        ids.add(ident)
        pos = posicoes.get(ident)
        if pos is None:
            pos = proxima_linha
            proxima_linha += 1
            posicoes[ident] = pos
        valores = [ident if col == "id_chamado" else item.get(col, "")
                   for col in COLUNAS_FILA]
        if ident in ids_atuais:
            # Nao reverte uma aprovacao/desaprovacao feita no Sheets apos a leitura.
            dados.extend([
                {"range": f"A{pos}:E{pos}", "values": [valores[:aprovacao]]},
                {"range": f"G{pos}:L{pos}", "values": [valores[aprovacao + 1:]]},
            ])
        else:
            dados.append({"range": f"A{pos}:L{pos}", "values": [valores]})
    if dados:
        ws.batch_update(dados, value_input_option="RAW")
    fim = max(posicoes.values(), default=1)
    if fim >= 2:
        ws.spreadsheet.batch_update({"requests": [{"setDataValidation": {
            "range": {"sheetId": ws.id, "startRowIndex": 1, "endRowIndex": fim,
                      "startColumnIndex": aprovacao, "endColumnIndex": aprovacao + 1},
            "rule": {"condition": {"type": "BOOLEAN"}, "strict": True,
                     "showCustomUi": True},
        }}]})
    return len(linhas)


def atualizar_resultado(sh, resultado: dict[str, Any], nome: str = ABA_FILA) -> None:
    """Atualiza somente G:L do ID aprovado, apos reler a fila fixa.

    O resultado precisa trazer o snapshot de origem, destino e validacao que
    foi aprovado. Uma mudanca durante a execucao bloqueia o registro da
    resposta, sem tocar na checkbox nem em outra aba.
    """
    ident = _id(resultado.get("id_chamado"))
    if not ident:
        raise ValueError("Resultado sem ID Chamado.")
    ws = sh.worksheet(nome)
    bloco = pl.ler_valores(ws, "A:L")
    if not bloco or list(bloco[0][:len(COLUNAS_FILA)]) != list(COLUNAS_FILA):
        raise ValueError("Cabecalho da fila difere do esquema esperado.")
    encontrados: list[tuple[int, dict[str, Any]]] = []
    for pos, valores in enumerate(bloco[1:], start=2):
        if valores and _id(valores[0]) == ident:
            atual = {col: valores[i] if i < len(valores) else ""
                     for i, col in enumerate(COLUNAS_FILA)}
            encontrados.append((pos, atual))
    if len(encontrados) != 1:
        raise ValueError(f"ID {ident} ausente ou duplicado na fila.")
    pos, atual = encontrados[0]
    if atual["aprovado_glpi"] is not True:
        raise ValueError(f"ID {ident} sem checkbox de aprovacao TRUE.")
    for campo in ("categoria_glpi_planilha", "categoria_correta", "situacao_validacao"):
        if campo not in resultado or str(atual[campo] or "") != str(resultado[campo] or ""):
            raise ValueError(f"Snapshot do ID {ident} divergiu no campo {campo}.")
    valores = [resultado.get(col, atual[col]) for col in COLUNAS_AUDITORIA]
    # G:L inclui data_candidato em J; conserva-a literalmente da fila.
    ws.batch_update([{"range": f"G{pos}:L{pos}",
                      "values": [[valores[0], valores[1], valores[2],
                                  atual["data_candidato"], valores[3], valores[4]]]}],
                    value_input_option="RAW")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    parser.add_argument("--credenciais", default=None)
    parser.add_argument("--aba-fila", default=ABA_FILA)
    parser.add_argument("--aplicar", action="store_true",
                        help="Materializa/atualiza a fila na planilha.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    with args.config.open(encoding="utf-8") as arquivo:
        config = json.load(arquivo)
    try:
        sh = pl.abrir_planilha(pl.id_planilha(config), args.credenciais)
        origem = pl.ler_valores(sh.worksheet(config["aba_principal"]), "A:Q")
        candidatos = selecionar_candidatos(origem)
        existentes = ler_fila(sh, args.aba_fila)
        fila = upsert_fila(existentes, candidatos)
        quantidades = {
            "candidatos": len(candidatos),
            "elegiveis": sum(c["situacao_validacao"] == "ELEGIVEL" for c in candidatos),
            "conflitos": sum(c["situacao_validacao"] == "CONFLITO" for c in candidatos),
            "fila_total": len(fila),
            "novos": len(fila) - len(existentes),
        }
        print(json.dumps(quantidades, ensure_ascii=False, sort_keys=True))
        if args.aplicar:
            escrever_fila(sh, fila, args.aba_fila)
            print("modo=aplicar; fila materializada.")
        else:
            print("modo=dry-run; nada gravado.")
        return 0
    except (ValueError, KeyError, FileNotFoundError, RuntimeError) as erro:
        print(f"Falha na geracao da fila: {erro}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
