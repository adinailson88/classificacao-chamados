"""Cliente mínimo da API REST V1 do GLPI. Nunca registra tokens ou respostas brutas."""

from __future__ import annotations

import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class GLPIError(RuntimeError):
    pass


class GLPIClient:
    def __init__(self, base_url: str, user_token: str, app_token: str):
        if not base_url.startswith("https://") or not base_url.rstrip("/").endswith("/apirest.php") or not user_token or not app_token:
            raise ValueError("GLPI_URL HTTPS com /apirest.php, GLPI_USER_TOKEN e GLPI_APP_TOKEN são obrigatórios")
        self.base_url = base_url.rstrip("/")
        self.user_token = user_token
        self.app_token = app_token
        self.session_token = None

    @classmethod
    def from_env(cls):
        return cls(os.getenv("GLPI_URL", ""), os.getenv("GLPI_USER_TOKEN", ""),
                   os.getenv("GLPI_APP_TOKEN", ""))

    def _request(self, method: str, path: str, payload=None, *, auth=True):
        headers = {"App-Token": self.app_token, "Accept": "application/json"}
        if auth:
            if not self.session_token:
                raise GLPIError("Sessão GLPI não inicializada")
            headers["Session-Token"] = self.session_token
        else:
            headers["Authorization"] = f"user_token {self.user_token}"
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = Request(f"{self.base_url}/{path.lstrip('/')}", data=data,
                      headers=headers, method=method)
        try:
            with urlopen(req, timeout=30) as response:
                body = response.read()
                return json.loads(body) if body else None, response.headers
        except HTTPError as exc:
            if exc.code == 404:
                return None, {}
            raise GLPIError(f"GLPI HTTP {exc.code} em {method} {path.split('?')[0]}") from None
        except (URLError, TimeoutError, ValueError) as exc:
            raise GLPIError(f"Falha de comunicação GLPI em {method} {path.split('?')[0]}") from None

    def __enter__(self):
        data, _ = self._request("GET", "initSession", auth=False)
        if not isinstance(data, dict) or not data.get("session_token"):
            raise GLPIError("initSession sem session_token")
        self.session_token = data["session_token"]
        return self

    def __exit__(self, *_):
        try:
            if self.session_token:
                self._request("GET", "killSession")
        finally:
            self.session_token = None

    def ticket(self, ticket_id: str):
        data, _ = self._request("GET", f"Ticket/{quote(str(ticket_id), safe='')}")
        return data

    def categorias(self):
        """Pagina até esgotar; resultado incompleto não pode produzir um mapa seguro."""
        todas = []
        inicio = 0
        while True:
            data, headers = self._request("GET", f"ITILCategory?range={inicio}-{inicio + 99}")
            if not isinstance(data, list):
                raise GLPIError("Resposta inválida da lista ITILCategory")
            todas.extend(data)
            faixa = re.search(r"(\d+)-(\d+)/(\d+)", str(headers.get("Content-Range", "")))
            if faixa:
                fim, total = int(faixa.group(2)), int(faixa.group(3))
                if fim + 1 >= total:
                    break
                if not data or fim + 1 <= inicio:
                    raise GLPIError("Paginação ITILCategory não avançou")
                inicio = fim + 1
            else:
                if len(data) < 100:
                    break
                inicio += len(data)
            if inicio > 100000:
                raise GLPIError("Paginação ITILCategory excedeu limite de segurança")
        return todas

    def corrigir_ticket(self, ticket_id: str, categoria_id: int):
        data, _ = self._request("PUT", f"Ticket/{quote(str(ticket_id), safe='')}",
                                {"input": {"itilcategories_id": categoria_id}})
        return data
