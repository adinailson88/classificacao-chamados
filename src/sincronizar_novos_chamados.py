#!/usr/bin/env python3
"""Traz para a aba principal os chamados novos que ja chegaram a planilha de origem do GLPI.

Contexto: a copia A:F da origem (aba `GLPI`, alimentada pelo export do GLPI) para a aba principal era feita
por um acionador do Apps Script. O log `LOG_COPIA_A_F` mostra que ele deixou de inserir chamados novos
(a ultima insercao foi em 22/10/2026), de modo que a aba principal ficou sem os chamados posteriores.

Regras:
    - Escreve SOMENTE em A:F de linhas novas, no fim dos dados. Nunca toca em G:Q (conferencias M, N, P e a
      categoria manual Q inclusive) nem em linhas existentes.
    - So entra chamado cujo ID nao esta na aba principal e cuja categoria ja existe na coluna C da aba
      principal. Isso deixa de fora projetos, memoriais e orcamentos, que nao pertencem a taxonomia de
      manutencao.
    - Sem --aplicar e dry-run: so relata. Cada insercao e registrada em LOG_COPIA_A_F (operacao NOVO).

O ID da planilha de origem vem de ORIGEM_GLPI_SPREADSHEET_ID (segredo no CI, arquivo origem_glpi.local no uso
local) e nao deve ser versionado.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planilha as pl  # noqa: E402
from datetime import datetime  # noqa: E402
from tempo import FUSO_BAHIA  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
ABA_ORIGEM = "GLPI"
ABA_LOG = "LOG_COPIA_A_F"
CABECALHO_LOG = ["data_hora", "operacao", "id_chamado", "linha_destino", "categoria_antes", "categoria_depois", "detalhe"]
ORIGEM_LOCAL = RAIZ / "origem_glpi.local"
TAMANHO_LOTE = 200  # trava por execucao, como o limite de atualizacoes do script original


def normalizar_id(valor: Any) -> str:
    bruto = str(valor or "").strip()
    return bruto[:-2] if bruto.endswith(".0") and bruto[:-2].isdigit() else bruto


def montar_descricao(descricao: str, solucao: str) -> str:
    """Mesmo formato das linhas ja existentes na coluna D."""
    texto = "Descrição - " + (descricao or "").strip()
    if (solucao or "").strip():
        texto += "\n\nHistórico / solução - " + solucao.strip()
    return texto


def selecionar_novos(origem: list[list[Any]], ids_existentes: set[str], taxonomia: set[str],
                     limite: int = TAMANHO_LOTE) -> tuple[list[list[str]], dict[str, int]]:
    """Linhas A:F dos chamados novos da origem, em ordem de ID, e a contagem do que ficou de fora."""
    if not origem:
        return [], {"ja_existentes": 0, "fora_da_taxonomia": 0, "sem_categoria": 0, "acima_do_limite": 0}
    cab = [str(c).strip().lower() for c in origem[0]]
    i = {nome: cab.index(nome) for nome in ("id", "titulo", "categoria", "descricao", "solucao")}
    novos: list[list[str]] = []
    resumo = {"ja_existentes": 0, "fora_da_taxonomia": 0, "sem_categoria": 0, "acima_do_limite": 0}
    vistos: set[str] = set()
    for lin in origem[1:]:
        lin = list(lin) + [""] * (len(cab) - len(lin))
        id_ = normalizar_id(lin[i["id"]])
        if not id_ or id_ in vistos:
            continue
        vistos.add(id_)
        if id_ in ids_existentes:
            resumo["ja_existentes"] += 1
            continue
        categoria = str(lin[i["categoria"]]).strip()
        if not categoria:
            resumo["sem_categoria"] += 1
            continue
        if categoria not in taxonomia:
            resumo["fora_da_taxonomia"] += 1
            continue
        novos.append([id_, str(lin[i["titulo"]]).strip(), categoria,
                      montar_descricao(str(lin[i["descricao"]]), str(lin[i["solucao"]])), "", ""])
    novos.sort(key=lambda r: (len(r[0]), r[0]))
    if len(novos) > limite:
        resumo["acima_do_limite"] = len(novos) - limite
        novos = novos[:limite]
    return novos, resumo


def id_origem() -> str:
    env = os.getenv("ORIGEM_GLPI_SPREADSHEET_ID")
    if env and env.strip():
        return env.strip()
    if ORIGEM_LOCAL.exists():
        valor = ORIGEM_LOCAL.read_text(encoding="utf-8").strip()
        if valor:
            return valor
    raise RuntimeError("ID da planilha de origem nao definido (ORIGEM_GLPI_SPREADSHEET_ID ou origem_glpi.local).")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", default=str(CONFIG_PADRAO))
    ap.add_argument("--aplicar", action="store_true", help="grava de verdade; sem isso e dry-run")
    a = ap.parse_args()

    config = json.loads(Path(a.config).read_text(encoding="utf-8"))
    aba_principal = config.get("aba_principal", "CHAMADOS_ESQUELETO_REDUZIDO")
    sh = pl.abrir_planilha(pl.id_planilha(config))
    ws = sh.worksheet(aba_principal)
    coluna_a = pl._com_retry(lambda: ws.col_values(1), rotulo="ler_ids")
    coluna_c = pl._com_retry(lambda: ws.col_values(3), rotulo="ler_categorias")
    ids_existentes = {normalizar_id(v) for v in coluna_a[1:] if str(v).strip()}
    taxonomia = {str(v).strip() for v in coluna_c[1:] if str(v).strip()}
    ultima = max((n for n, v in enumerate(coluna_a, 1) if str(v).strip()), default=1)

    origem_ws = pl.abrir_planilha(id_origem()).worksheet(ABA_ORIGEM)
    origem = pl._com_retry(lambda: origem_ws.get_all_values(), rotulo="ler_origem")

    novos, resumo = selecionar_novos(origem, ids_existentes, taxonomia)
    print(f"principal: {len(ids_existentes)} chamados, ultima linha com ID = {ultima}; origem: {len(origem) - 1} linhas")
    print(f"novos a inserir: {len(novos)} | descartados: {resumo}")
    for r in novos[:40]:
        print("  ", r[0], "|", r[1][:55], "|", r[2])
    if not novos:
        return 0
    if not a.aplicar:
        print("DRY-RUN: nada foi escrito. Use --aplicar para gravar.")
        return 0

    primeira = ultima + 1
    # linhas-alvo precisam estar vazias em A:Q, para nunca sobrescrever dado existente
    existente = pl._com_retry(lambda: ws.get(f"A{primeira}:Q{primeira + len(novos) - 1}"), rotulo="checar_destino")
    if any(any(str(c).strip() for c in lin) for lin in existente):
        print("ABORTADO: ha dados nas linhas de destino; nenhuma escrita feita.", file=sys.stderr)
        return 1
    if ws.row_count < primeira + len(novos) - 1:
        ws.add_rows(primeira + len(novos) - 1 - ws.row_count)
    pl._com_retry(lambda: ws.update(values=novos, range_name=f"A{primeira}:F{primeira + len(novos) - 1}",
                                    value_input_option="RAW"), rotulo="escrever_novos")
    agora = datetime.now(FUSO_BAHIA).strftime("%Y-%m-%d %H:%M:%S")
    log = sh.worksheet(ABA_LOG)
    pl._com_retry(lambda: log.append_rows(
        [[agora, "NOVO", r[0], primeira + k, "", r[2], "A:F inseridos por sincronizar_novos_chamados.py; G:Q permaneceram vazios"]
         for k, r in enumerate(novos)], value_input_option="RAW"), rotulo="log")
    print(f"GRAVADO: {len(novos)} linhas em A{primeira}:F{primeira + len(novos) - 1}; log em {ABA_LOG}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
