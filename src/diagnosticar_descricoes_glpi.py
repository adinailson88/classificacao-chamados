"""Diagnóstico somente leitura das descrições dos 69 Tickets históricos.

Não faz PUT, não altera planilhas e não imprime conteúdo de chamados no terminal.
Os resultados completos são gravados apenas em arquivos locais ignorados pelo Git.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import glpi_client as gc


IDS_69 = (
    "2026050229",
    "2026070496", "2026070492", "2026070500", "2026070538", "2026070546",
    "2026070550", "2026070554", "2026070557", "2026070582", "2026070583",
    "2026080394", "2026080397", "2026080514", "2026080555", "2026080557",
    "2026080561", "2026080576", "2026080577", "2026080603", "2026080609",
    "2026080612", "2026080616", "2026080621", "2026080630", "2026080631",
    "2026080633", "2026080639", "2026080640", "2026080645", "2026080652",
    "2026080656", "2026080659", "2026080660", "2026080662", "2026080665",
    "2026080671", "2026080673", "2026080690", "2026080691", "2026080694",
    "2026090024", "2026090126", "2026090181", "2026090182", "2026090186",
    "2026090193", "2026090194", "2026090195", "2026090202", "2026090204",
    "2026090213", "2026090216", "2026090257", "2026090258", "2026090259",
    "2026090262", "2026090265", "2026090267", "2026090268", "2026090271",
    "2026090272", "2026090277", "2026090281", "2026090282", "2026090283",
    "2026090286", "2026090290", "2026090299",
)

DEFAULT_JSON = Path("diagnostico_descricoes_glpi.local.json")
DEFAULT_CSV = Path("diagnostico_descricoes_glpi.local.csv")


def _texto(valor) -> str:
    return "" if valor is None else str(valor)


def _solucoes_validas(solucoes):
    saida = []
    for solucao in solucoes:
        if not isinstance(solucao, dict):
            continue
        saida.append({
            "id": solucao.get("id"),
            "content": _texto(solucao.get("content")),
            "date_creation": _texto(solucao.get("date_creation")),
            "date_mod": _texto(solucao.get("date_mod")),
            "status": solucao.get("status"),
        })
    return saida


def diagnosticar_ticket(cliente, ticket_id: str):
    ticket = cliente.ticket(ticket_id)
    if ticket is None:
        return {
            "id_chamado": ticket_id,
            "existe": False,
            "status": "NAO_ENCONTRADO",
            "descricao": "",
            "solucoes": [],
            "solucao_selecionada": "",
            "descricao_composta": "",
        }

    if not isinstance(ticket, dict) or str(ticket.get("id")) != ticket_id:
        return {
            "id_chamado": ticket_id,
            "existe": True,
            "status": "RESPOSTA_TICKET_INVALIDA",
            "descricao": "",
            "solucoes": [],
            "solucao_selecionada": "",
            "descricao_composta": "",
        }

    descricao = _texto(ticket.get("content"))
    solucoes = _solucoes_validas(cliente.solucoes_ticket(ticket_id))

    if len(solucoes) == 0:
        selecionada = ""
        status = "RECUPERADO_SEM_SOLUCAO" if descricao.strip() else "SEM_DESCRICAO"
    elif len(solucoes) == 1:
        selecionada = solucoes[0]["content"]
        status = "RECUPERADO" if descricao.strip() else "SEM_DESCRICAO"
    else:
        # Não escolhe silenciosamente entre múltiplas soluções.
        selecionada = ""
        status = "MULTIPLAS_SOLUCOES"

    composta = ""
    if status in {"RECUPERADO", "RECUPERADO_SEM_SOLUCAO"}:
        composta = f"Descrição - {descricao}\n\nSolução - {selecionada}"

    return {
        "id_chamado": ticket_id,
        "existe": True,
        "status": status,
        "descricao": descricao,
        "solucoes": solucoes,
        "solucao_selecionada": selecionada,
        "descricao_composta": composta,
    }


def executar(cliente, ids=IDS_69):
    resultados = []
    for ticket_id in ids:
        try:
            resultados.append(diagnosticar_ticket(cliente, ticket_id))
        except gc.GLPIError as exc:
            resultados.append({
                "id_chamado": ticket_id,
                "existe": None,
                "status": "ERRO_API",
                "descricao": "",
                "solucoes": [],
                "solucao_selecionada": "",
                "descricao_composta": "",
                "erro": str(exc),
            })
    return resultados


def resumo(resultados):
    contagens = {}
    for item in resultados:
        status = item["status"]
        contagens[status] = contagens.get(status, 0) + 1
    return {
        "consultados": len(resultados),
        "encontrados": sum(1 for x in resultados if x.get("existe") is True),
        "nao_encontrados": sum(1 for x in resultados if x.get("existe") is False),
        "com_descricao": sum(1 for x in resultados if x.get("descricao", "").strip()),
        "com_uma_solucao": sum(1 for x in resultados if len(x.get("solucoes", [])) == 1),
        "com_multiplas_solucoes": sum(1 for x in resultados if len(x.get("solucoes", [])) > 1),
        "recuperaveis_para_coluna_d": sum(
            1 for x in resultados if x.get("descricao_composta", "").strip()
        ),
        "por_status": contagens,
    }


def salvar_json(path: Path, resultados):
    payload = {"resumo": resumo(resultados), "resultados": resultados}
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def salvar_csv(path: Path, resultados):
    campos = [
        "id_chamado", "existe", "status", "descricao",
        "quantidade_solucoes", "solucao_selecionada",
        "descricao_composta", "erro",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as arquivo:
        writer = csv.DictWriter(arquivo, fieldnames=campos)
        writer.writeheader()
        for item in resultados:
            writer.writerow({
                "id_chamado": item["id_chamado"],
                "existe": item.get("existe"),
                "status": item["status"],
                "descricao": item.get("descricao", ""),
                "quantidade_solucoes": len(item.get("solucoes", [])),
                "solucao_selecionada": item.get("solucao_selecionada", ""),
                "descricao_composta": item.get("descricao_composta", ""),
                "erro": item.get("erro", ""),
            })


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Consulta somente leitura dos 69 Tickets históricos no GLPI."
    )
    parser.add_argument("--saida-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--saida-csv", type=Path, default=DEFAULT_CSV)
    args = parser.parse_args(argv)

    if len(IDS_69) != 69 or len(set(IDS_69)) != 69:
        raise RuntimeError("Lista de IDs históricos inválida: esperado 69 IDs únicos")

    with gc.GLPIClient.from_env() as cliente:
        resultados = executar(cliente)

    salvar_json(args.saida_json, resultados)
    salvar_csv(args.saida_csv, resultados)

    info = resumo(resultados)
    # Não imprimir descrição, solução, URL nem tokens.
    print(json.dumps(info, ensure_ascii=False, sort_keys=True))
    print(f"JSON privado: {args.saida_json}")
    print(f"CSV privado: {args.saida_csv}")

    return 0 if info["por_status"].get("ERRO_API", 0) == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
