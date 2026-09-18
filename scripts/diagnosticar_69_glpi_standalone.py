"""Consulta somente leitura dos 69 Tickets históricos no GLPI 9.1.1.

Uso:
  1) defina GLPI_URL, GLPI_USER_TOKEN e GLPI_APP_TOKEN
  2) python diagnosticar_69_glpi_standalone.py

Não faz PUT. Não altera Ticket nem planilha.
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


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

OUT_JSON = Path("diagnostico_descricoes_glpi.local.json")
OUT_CSV = Path("diagnostico_descricoes_glpi.local.csv")


class GLPIError(RuntimeError):
    pass


class GLPIClient:
    def __init__(self):
        self.base_url = os.getenv("GLPI_URL", "").rstrip("/")
        self.user_token = os.getenv("GLPI_USER_TOKEN", "")
        self.app_token = os.getenv("GLPI_APP_TOKEN", "")
        self.session_token = None

        if not self.base_url.startswith("https://") or not self.base_url.endswith("/apirest.php"):
            raise ValueError("GLPI_URL deve começar com https:// e terminar em /apirest.php")
        if not self.user_token or not self.app_token:
            raise ValueError("GLPI_USER_TOKEN e GLPI_APP_TOKEN são obrigatórios")

    def _request(self, path, *, auth=True):
        headers = {"App-Token": self.app_token, "Accept": "application/json"}
        if auth:
            if not self.session_token:
                raise GLPIError("Sessão GLPI não inicializada")
            headers["Session-Token"] = self.session_token
        else:
            headers["Authorization"] = f"user_token {self.user_token}"

        req = Request(f"{self.base_url}/{path.lstrip('/')}", headers=headers, method="GET")
        try:
            with urlopen(req, timeout=30) as response:
                body = response.read()
                return json.loads(body) if body else None
        except HTTPError as exc:
            if exc.code == 404:
                return None
            raise GLPIError(f"GLPI HTTP {exc.code} em GET {path.split('?')[0]}") from None
        except (URLError, TimeoutError, ValueError):
            raise GLPIError(f"Falha de comunicação GLPI em GET {path.split('?')[0]}") from None

    def __enter__(self):
        data = self._request("initSession", auth=False)
        if not isinstance(data, dict) or not data.get("session_token"):
            raise GLPIError("initSession sem session_token")
        self.session_token = data["session_token"]
        return self

    def __exit__(self, *_):
        try:
            if self.session_token:
                self._request("killSession")
        finally:
            self.session_token = None

    def ticket(self, ticket_id):
        return self._request(f"Ticket/{quote(str(ticket_id), safe='')}")


def diagnosticar_ticket(cliente, ticket_id):
    ticket = cliente.ticket(ticket_id)

    if ticket is None:
        return {
            "id_chamado": ticket_id,
            "existe": False,
            "status": "NAO_ENCONTRADO",
            "descricao": "",
            "solucao": "",
            "descricao_composta": "",
            "erro": "",
        }

    if not isinstance(ticket, dict) or str(ticket.get("id")) != ticket_id:
        return {
            "id_chamado": ticket_id,
            "existe": True,
            "status": "RESPOSTA_TICKET_INVALIDA",
            "descricao": "",
            "solucao": "",
            "descricao_composta": "",
            "erro": "",
        }

    descricao = "" if ticket.get("content") is None else str(ticket.get("content"))
    solucao = "" if ticket.get("solution") is None else str(ticket.get("solution"))

    if descricao.strip():
        status = "RECUPERADO"
        composta = f"Descrição - {descricao}\n\nSolução - {solucao}"
    else:
        status = "SEM_DESCRICAO"
        composta = ""

    return {
        "id_chamado": ticket_id,
        "existe": True,
        "status": status,
        "descricao": descricao,
        "solucao": solucao,
        "descricao_composta": composta,
        "erro": "",
    }


def main():
    if len(IDS_69) != 69 or len(set(IDS_69)) != 69:
        raise RuntimeError("Lista inválida: esperado 69 IDs únicos")

    resultados = []
    with GLPIClient() as cliente:
        for ticket_id in IDS_69:
            try:
                resultados.append(diagnosticar_ticket(cliente, ticket_id))
            except GLPIError as exc:
                resultados.append({
                    "id_chamado": ticket_id,
                    "existe": None,
                    "status": "ERRO_API",
                    "descricao": "",
                    "solucao": "",
                    "descricao_composta": "",
                    "erro": str(exc),
                })

    por_status = {}
    for item in resultados:
        por_status[item["status"]] = por_status.get(item["status"], 0) + 1

    resumo = {
        "consultados": len(resultados),
        "encontrados": sum(1 for x in resultados if x.get("existe") is True),
        "nao_encontrados": sum(1 for x in resultados if x.get("existe") is False),
        "com_descricao": sum(1 for x in resultados if x["descricao"].strip()),
        "com_solucao": sum(1 for x in resultados if x["solucao"].strip()),
        "recuperaveis_para_coluna_d": sum(1 for x in resultados if x["descricao_composta"].strip()),
        "por_status": por_status,
    }

    OUT_JSON.write_text(
        json.dumps({"resumo": resumo, "resultados": resultados}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as arq:
        campos = ["id_chamado", "existe", "status", "descricao", "solucao", "descricao_composta", "erro"]
        writer = csv.DictWriter(arq, fieldnames=campos)
        writer.writeheader()
        writer.writerows(resultados)

    print(json.dumps(resumo, ensure_ascii=False, sort_keys=True))
    print(f"JSON privado: {OUT_JSON.resolve()}")
    print(f"CSV privado: {OUT_CSV.resolve()}")


if __name__ == "__main__":
    main()
