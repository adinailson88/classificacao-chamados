#!/usr/bin/env python3
"""Sincroniza correcoes humanas de categoria com a API REST V1 do GLPI 9.1.1.

O modo padrao e ``dry-run``: le a fila, a planilha principal e o GLPI, mas nao
altera nenhum deles. A escrita exige simultaneamente ``--aplicar``, confirmacao
literal e aprovacao ``SIM`` na fila. Toda associacao e feita por ID Chamado.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import planilha as pl


ABA_FILA = "CORRECOES_GLPI_POR_ID"
ABA_ORIGINAL = "CHAMADOS_ESQUELETO_REDUZIDO"
ABA_LOG = "LOG_SINCRONIZACAO_GLPI"
CONFIRMACAO_APLICAR = "APLICAR_GLPI"
FUSO_AUDITORIA = ZoneInfo("America/Bahia")


class ErroSincronizacao(RuntimeError):
    """Falha de contrato, configuracao ou comunicacao da sincronizacao."""


@dataclass(frozen=True)
class Correcao:
    linha: int
    id_chamado: str
    categoria_anterior: str
    categoria_correta: str
    validado_em: str
    aprovado: str
    workflow_executado_em: str
    sincronizado_em: str
    resultado: str
    run_url: str


@dataclass
class Resultado:
    id_chamado: str
    linha_fila: int
    categoria_anterior: str
    categoria_correta: str
    categoria_glpi_antes: str = ""
    categoria_glpi_depois: str = ""
    resultado: str = ""
    detalhe: str = ""
    executado_em: str = ""
    sincronizado_em: str = ""
    run_url: str = ""
    registro_fila: str = "NAO APLICAVEL"


def normalizar_id(valor: Any) -> str:
    texto = str(valor or "").strip()
    if not texto:
        return ""
    if re.fullmatch(r"\d+(?:\.0+)?", texto):
        return str(int(float(texto)))
    return texto


def normalizar_aprovacao(valor: Any) -> str:
    return str(valor or "").strip().casefold()


def nome_categoria(valor: Any) -> str:
    """Normaliza apenas espacos; nao faz aproximacao semantica ou por caixa."""
    partes = [" ".join(p.strip().split()) for p in str(valor or "").split(">")]
    return " > ".join(p for p in partes if p)


def agora_bahia() -> str:
    return datetime.now(FUSO_AUDITORIA).strftime("%d/%m/%Y %H:%M:%S")


def valor(linha: list[Any], indice: int) -> str:
    return str(linha[indice] if indice < len(linha) else "").strip()


def indices_obrigatorios(cabecalho: list[Any], nomes: Iterable[str]) -> dict[str, int]:
    mapa = {pl.normalizar_cabecalho(v): i for i, v in enumerate(cabecalho)}
    saida: dict[str, int] = {}
    ausentes = []
    for nome in nomes:
        idx = mapa.get(pl.normalizar_cabecalho(nome))
        if idx is None:
            ausentes.append(nome)
        else:
            saida[nome] = idx
    if ausentes:
        raise ErroSincronizacao("Cabecalhos ausentes: " + ", ".join(ausentes))
    return saida


def ler_fila(ws) -> list[Correcao]:
    bloco = pl.ler_valores(ws, "A:I")
    if not bloco:
        raise ErroSincronizacao(f"Aba {ABA_FILA} vazia.")
    nomes = (
        "ID Chamado", "Categoria anterior", "Categoria correta", "Validado em",
        "Aprovado para GLPI", "Workflow executado em", "Sincronizado em",
        "Resultado", "Run ID/URL",
    )
    idx = indices_obrigatorios(bloco[0], nomes)
    correcoes: list[Correcao] = []
    vistos: dict[str, int] = {}
    for numero, linha in enumerate(bloco[1:], start=2):
        chamado = normalizar_id(valor(linha, idx["ID Chamado"]))
        if not chamado:
            continue
        if chamado in vistos:
            raise ErroSincronizacao(
                f"ID duplicado na fila: {chamado} (linhas {vistos[chamado]} e {numero}).")
        vistos[chamado] = numero
        correcoes.append(Correcao(
            linha=numero,
            id_chamado=chamado,
            categoria_anterior=nome_categoria(valor(linha, idx["Categoria anterior"])),
            categoria_correta=nome_categoria(valor(linha, idx["Categoria correta"])),
            validado_em=valor(linha, idx["Validado em"]),
            aprovado=valor(linha, idx["Aprovado para GLPI"]),
            workflow_executado_em=valor(linha, idx["Workflow executado em"]),
            sincronizado_em=valor(linha, idx["Sincronizado em"]),
            resultado=valor(linha, idx["Resultado"]),
            run_url=valor(linha, idx["Run ID/URL"]),
        ))
    return correcoes


def ler_fonte_original(ws) -> dict[str, dict[str, str]]:
    bloco = pl.ler_valores(ws, "A:Q")
    if not bloco:
        raise ErroSincronizacao(f"Aba {ABA_ORIGINAL} vazia.")
    nomes = ("ID Chamado", "CATEGORIA COMPLETA", "CONFERÊNCIA GLPI",
             "CATEGORIA CORRETA MANUAL")
    idx = indices_obrigatorios(bloco[0], nomes)
    saida: dict[str, dict[str, str]] = {}
    for numero, linha in enumerate(bloco[1:], start=2):
        chamado = normalizar_id(valor(linha, idx["ID Chamado"]))
        if not chamado:
            continue
        if chamado in saida:
            raise ErroSincronizacao(
                f"ID duplicado na aba principal: {chamado} (inclui linha {numero}).")
        saida[chamado] = {
            "linha": str(numero),
            "categoria_anterior": nome_categoria(valor(linha, idx["CATEGORIA COMPLETA"])),
            "conferencia_glpi": valor(linha, idx["CONFERÊNCIA GLPI"]),
            "categoria_correta": nome_categoria(valor(linha, idx["CATEGORIA CORRETA MANUAL"])),
        }
    return saida


def validar_fonte(correcao: Correcao, fonte: dict[str, dict[str, str]]) -> str | None:
    atual = fonte.get(correcao.id_chamado)
    if atual is None:
        return "ID NAO ENCONTRADO NA PLANILHA ORIGINAL"
    if atual["conferencia_glpi"].strip().casefold() != "errado":
        return "M NAO ESTA COMO ERRADO"
    if atual["categoria_anterior"] != correcao.categoria_anterior:
        return "CATEGORIA ANTERIOR DIVERGIU DA FONTE"
    if atual["categoria_correta"] != correcao.categoria_correta:
        return "CATEGORIA CORRETA DIVERGIU DA FONTE"
    if not correcao.categoria_correta:
        return "CATEGORIA CORRETA VAZIA"
    return None


def url_api(base: str) -> str:
    base = str(base or "").strip().rstrip("/")
    if not base:
        raise ErroSincronizacao("GLPI_BASE_URL ausente.")
    if not base.lower().startswith("https://"):
        raise ErroSincronizacao("GLPI_BASE_URL deve usar HTTPS.")
    if base.endswith("/apirest.php"):
        return base
    return base + "/apirest.php"


class GlpiClient:
    def __init__(self, base_url: str, app_token: str, user_token: str,
                 timeout: int = 30):
        self.base_url = url_api(base_url)
        self.app_token = str(app_token or "").strip()
        self.user_token = str(user_token or "").strip()
        self.timeout = timeout
        self.session_token = ""
        if not self.app_token or not self.user_token:
            raise ErroSincronizacao("GLPI_APP_TOKEN ou GLPI_USER_TOKEN ausente.")

    def _request(self, method: str, caminho: str, *, corpo: dict | None = None,
                 query: dict[str, Any] | None = None, sessao: bool = True):
        url = self.base_url + "/" + caminho.lstrip("/")
        if query:
            url += "?" + urllib.parse.urlencode(query)
        headers = {"App-Token": self.app_token, "Accept": "application/json"}
        if sessao:
            if not self.session_token:
                raise ErroSincronizacao("Sessao GLPI nao inicializada.")
            headers["Session-Token"] = self.session_token
        else:
            headers["Authorization"] = "user_token " + self.user_token
        dados = None
        if corpo is not None:
            dados = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=dados, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                bruto = resp.read().decode("utf-8-sig")
                payload = json.loads(bruto) if bruto.strip() else None
                return resp.status, dict(resp.headers.items()), payload
        except urllib.error.HTTPError as exc:
            corpo_erro = exc.read().decode("utf-8", errors="replace")[:1000]
            raise ErroSincronizacao(
                f"GLPI HTTP {exc.code} em {method} {caminho}: {corpo_erro}") from exc
        except urllib.error.URLError as exc:
            raise ErroSincronizacao(
                f"Falha de comunicacao com o GLPI em {method} {caminho}: {exc.reason}") from exc

    def abrir_sessao(self) -> None:
        _, _, payload = self._request("GET", "initSession", sessao=False)
        token = str((payload or {}).get("session_token") or "").strip()
        if not token:
            raise ErroSincronizacao("initSession nao retornou session_token.")
        self.session_token = token

    def fechar_sessao(self) -> None:
        if not self.session_token:
            return
        try:
            self._request("GET", "killSession")
        finally:
            self.session_token = ""

    def obter_chamado(self, chamado: str) -> dict[str, Any]:
        _, _, payload = self._request(
            "GET", f"Ticket/{urllib.parse.quote(chamado, safe='')}",
            query={"get_hateoas": "false"})
        if not isinstance(payload, dict):
            raise ErroSincronizacao(f"Resposta invalida para Ticket/{chamado}.")
        return payload

    def listar_categorias(self) -> list[dict[str, Any]]:
        itens: list[dict[str, Any]] = []
        inicio = 0
        tamanho = 500
        for _ in range(100):
            status, headers, payload = self._request(
                "GET", "ITILCategory",
                query={"range": f"{inicio}-{inicio + tamanho - 1}", "get_hateoas": "false"})
            if not isinstance(payload, list):
                raise ErroSincronizacao("Catalogo ITILCategory retornou formato invalido.")
            itens.extend(x for x in payload if isinstance(x, dict))
            if status != 206:
                break
            faixa = headers.get("Content-Range") or headers.get("content-range") or ""
            m = re.search(r"/(\d+)$", faixa)
            total = int(m.group(1)) if m else None
            inicio += len(payload)
            if not payload or (total is not None and inicio >= total):
                break
        else:
            raise ErroSincronizacao("Catalogo ITILCategory excedeu 100 paginas.")
        return itens

    def atualizar_categoria(self, chamado: str, categoria_id: int) -> Any:
        _, _, payload = self._request(
            "PUT", f"Ticket/{urllib.parse.quote(chamado, safe='')}",
            corpo={"input": {"id": int(chamado), "itilcategories_id": int(categoria_id)}})
        return payload


def indexar_categorias(itens: list[dict[str, Any]]) -> tuple[dict[str, int], dict[int, str]]:
    por_nome: dict[str, int] = {}
    por_id: dict[int, str] = {}
    duplicadas: set[str] = set()
    for item in itens:
        try:
            categoria_id = int(item.get("id"))
        except (TypeError, ValueError):
            continue
        nome = nome_categoria(item.get("completename") or item.get("name"))
        if not nome:
            continue
        por_id[categoria_id] = nome
        ativa = str(item.get("is_active", "1")).strip().casefold() not in {"0", "false", "nao", "não"}
        if not ativa:
            continue
        if nome in por_nome and por_nome[nome] != categoria_id:
            duplicadas.add(nome)
        else:
            por_nome[nome] = categoria_id
    for nome in duplicadas:
        por_nome.pop(nome, None)
    return por_nome, por_id


def run_url_ambiente() -> str:
    servidor = os.getenv("GITHUB_SERVER_URL", "").rstrip("/")
    repositorio = os.getenv("GITHUB_REPOSITORY", "").strip("/")
    run_id = os.getenv("GITHUB_RUN_ID", "").strip()
    if servidor and repositorio and run_id:
        return f"{servidor}/{repositorio}/actions/runs/{run_id}"
    return ""


def selecionar(correcoes: list[Correcao], ids: set[str], aplicar: bool,
               limite: int) -> list[Correcao]:
    candidatas = [c for c in correcoes if not c.sincronizado_em]
    if ids:
        candidatas = [c for c in candidatas if c.id_chamado in ids]
        ausentes = ids - {c.id_chamado for c in candidatas}
        if ausentes:
            raise ErroSincronizacao("IDs solicitados ausentes ou ja sincronizados: " +
                                    ", ".join(sorted(ausentes)))
    if aplicar:
        candidatas = [c for c in candidatas if normalizar_aprovacao(c.aprovado) == "sim"]
    if limite > 0:
        candidatas = candidatas[:limite]
    return candidatas


def conferir_linha_fila(ws, correcao: Correcao) -> None:
    linha = pl._com_retry(lambda: ws.row_values(correcao.linha), rotulo="reler_fila")
    if normalizar_id(valor(linha, 0)) != correcao.id_chamado:
        raise ErroSincronizacao(f"ID mudou na linha {correcao.linha} da fila.")
    if nome_categoria(valor(linha, 1)) != correcao.categoria_anterior:
        raise ErroSincronizacao(f"Categoria anterior mudou para {correcao.id_chamado}.")
    if nome_categoria(valor(linha, 2)) != correcao.categoria_correta:
        raise ErroSincronizacao(f"Categoria correta mudou para {correcao.id_chamado}.")
    if normalizar_aprovacao(valor(linha, 4)) != "sim":
        raise ErroSincronizacao(f"Aprovacao retirada para {correcao.id_chamado}.")
    if valor(linha, 6):
        raise ErroSincronizacao(f"ID {correcao.id_chamado} ja foi sincronizado.")


def registrar_resultado(ws, resultado: Resultado) -> None:
    ws.update(
        range_name=f"F{resultado.linha_fila}:I{resultado.linha_fila}",
        values=[[
            resultado.executado_em,
            resultado.sincronizado_em,
            resultado.resultado,
            resultado.run_url,
        ]],
        value_input_option="USER_ENTERED",
    )


def registrar_log(sh, resultados: list[Resultado]) -> None:
    if not resultados:
        return
    cabecalho = [
        "Execucao", "ID Chamado", "Categoria anterior", "Categoria pretendida",
        "Categoria encontrada depois", "Resultado", "Detalhe", "Run ID/URL",
    ]
    linhas = [[
        r.executado_em, r.id_chamado, r.categoria_glpi_antes or r.categoria_anterior,
        r.categoria_correta, r.categoria_glpi_depois, r.resultado, r.detalhe, r.run_url,
    ] for r in resultados]
    pl.append_aba(sh, ABA_LOG, cabecalho, linhas)


def processar(correcao: Correcao, fonte: dict[str, dict[str, str]], cliente: GlpiClient,
              por_nome: dict[str, int], por_id: dict[int, str], aplicar: bool,
              ws_fila, run_url: str) -> Resultado:
    executado = agora_bahia()
    r = Resultado(
        id_chamado=correcao.id_chamado,
        linha_fila=correcao.linha,
        categoria_anterior=correcao.categoria_anterior,
        categoria_correta=correcao.categoria_correta,
        executado_em=executado,
        run_url=run_url,
    )
    falha_fonte = validar_fonte(correcao, fonte)
    if falha_fonte:
        r.resultado = "FONTE DIVERGENTE"
        r.detalhe = falha_fonte
        return r
    categoria_id = por_nome.get(correcao.categoria_correta)
    if categoria_id is None:
        r.resultado = "CATEGORIA NAO ENCONTRADA"
        r.detalhe = "Correspondencia exata e ativa nao encontrada no catalogo GLPI."
        return r
    ticket = cliente.obter_chamado(correcao.id_chamado)
    try:
        atual_id = int(ticket.get("itilcategories_id"))
    except (TypeError, ValueError):
        r.resultado = "ERRO DE VERIFICACAO"
        r.detalhe = "Ticket sem itilcategories_id valido."
        return r
    atual_nome = por_id.get(atual_id, "")
    r.categoria_glpi_antes = atual_nome
    if atual_nome == correcao.categoria_correta:
        r.categoria_glpi_depois = atual_nome
        r.resultado = "JA ESTAVA CORRETO"
        if aplicar:
            r.sincronizado_em = agora_bahia()
        return r
    if atual_nome != correcao.categoria_anterior:
        r.resultado = "CONFLITO - GLPI ALTERADO APOS VALIDACAO"
        r.detalhe = f"Categoria atual id={atual_id}; nome={atual_nome or 'nao resolvido'}"
        return r
    if not aplicar:
        r.resultado = "DRY-RUN OK"
        return r
    conferir_linha_fila(ws_fila, correcao)
    # Releitura imediatamente antes do PUT para controle de concorrencia no GLPI.
    ticket = cliente.obter_chamado(correcao.id_chamado)
    if int(ticket.get("itilcategories_id")) != atual_id:
        r.resultado = "CONFLITO - GLPI ALTERADO APOS VALIDACAO"
        r.detalhe = "Categoria mudou entre o preflight e a escrita."
        return r
    cliente.atualizar_categoria(correcao.id_chamado, categoria_id)
    depois = cliente.obter_chamado(correcao.id_chamado)
    try:
        depois_id = int(depois.get("itilcategories_id"))
    except (TypeError, ValueError):
        depois_id = -1
    r.categoria_glpi_depois = por_id.get(depois_id, "")
    if depois_id != categoria_id:
        r.resultado = "ERRO DE VERIFICACAO"
        r.detalhe = f"PUT executado, mas releitura retornou categoria id={depois_id}."
        return r
    r.resultado = "ATUALIZADO"
    r.sincronizado_em = agora_bahia()
    return r


def argumentos(argv: list[str] | None = None):
    p = argparse.ArgumentParser()
    p.add_argument("--aplicar", action="store_true",
                   help="Autoriza escrita no GLPI e na fila, sujeita aos demais gates.")
    p.add_argument("--confirmacao", default="")
    p.add_argument("--ids", default="", help="IDs separados por virgula; vazio seleciona a fila.")
    p.add_argument("--limite", type=int, default=0, help="0 = sem limite.")
    p.add_argument("--saida-json", default="outputs/glpi/relatorio_sincronizacao_glpi.json")
    p.add_argument("--credenciais", default=None)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = argumentos(argv)
    if args.limite < 0:
        raise ErroSincronizacao("--limite nao pode ser negativo.")
    if args.aplicar and args.confirmacao != CONFIRMACAO_APLICAR:
        raise ErroSincronizacao(
            f"Aplicacao exige --confirmacao {CONFIRMACAO_APLICAR}.")
    id_original = os.getenv("SPREADSHEET_ID", "").strip()
    id_fila = os.getenv("GLPI_CORRECOES_SPREADSHEET_ID", "").strip()
    if not id_original or not id_fila:
        raise ErroSincronizacao(
            "SPREADSHEET_ID ou GLPI_CORRECOES_SPREADSHEET_ID ausente.")

    sh_original = pl.abrir_planilha(id_original, args.credenciais)
    sh_fila = pl.abrir_planilha(id_fila, args.credenciais)
    ws_original = sh_original.worksheet(ABA_ORIGINAL)
    ws_fila = sh_fila.worksheet(ABA_FILA)
    fila = ler_fila(ws_fila)
    fonte = ler_fonte_original(ws_original)
    ids = {normalizar_id(x) for x in args.ids.split(",") if normalizar_id(x)}
    selecionadas = selecionar(fila, ids, args.aplicar, args.limite)

    cliente = GlpiClient(
        os.getenv("GLPI_BASE_URL", ""),
        os.getenv("GLPI_APP_TOKEN", ""),
        os.getenv("GLPI_USER_TOKEN", ""),
    )
    resultados: list[Resultado] = []
    run_url = run_url_ambiente()
    erro_encerramento_sessao = ""
    try:
        cliente.abrir_sessao()
        por_nome, por_id = indexar_categorias(cliente.listar_categorias())
        for correcao in selecionadas:
            try:
                resultado = processar(
                    correcao, fonte, cliente, por_nome, por_id, args.aplicar,
                    ws_fila, run_url)
            except Exception as exc:  # registra falha individual sem expor credenciais
                resultado = Resultado(
                    id_chamado=correcao.id_chamado,
                    linha_fila=correcao.linha,
                    categoria_anterior=correcao.categoria_anterior,
                    categoria_correta=correcao.categoria_correta,
                    resultado="ERRO DE COMUNICACAO",
                    detalhe=str(exc)[:1000],
                    executado_em=agora_bahia(),
                    run_url=run_url,
                )
            resultados.append(resultado)
            if args.aplicar:
                try:
                    registrar_resultado(ws_fila, resultado)
                    resultado.registro_fila = "OK"
                except Exception as exc:  # GLPI pode ter sido atualizado; preserve o fato no JSON
                    resultado.registro_fila = "ERRO"
                    sufixo = f"Falha ao registrar resultado na fila: {str(exc)[:500]}"
                    resultado.detalhe = "; ".join(x for x in (resultado.detalhe, sufixo) if x)
    finally:
        try:
            cliente.fechar_sessao()
        except Exception as exc:  # encerramento nao pode apagar o relatorio da execucao
            erro_encerramento_sessao = str(exc)[:1000]

    erro_log = ""
    if args.aplicar:
        try:
            registrar_log(sh_fila, resultados)
        except Exception as exc:
            erro_log = str(exc)[:1000]
    saida = Path(args.saida_json)
    saida.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "modo": "aplicar" if args.aplicar else "dry-run",
        "gerado_em": agora_bahia(),
        "total_fila": len(fila),
        "selecionados": len(selecionadas),
        "erro_encerramento_sessao": erro_encerramento_sessao,
        "erro_log": erro_log,
        "contagens": {},
        "resultados": [asdict(r) for r in resultados],
    }
    for r in resultados:
        payload["contagens"][r.resultado] = payload["contagens"].get(r.resultado, 0) + 1
    saida.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("modo", "total_fila", "selecionados", "contagens")},
                     ensure_ascii=False))
    falhas = {"FONTE DIVERGENTE", "CATEGORIA NAO ENCONTRADA", "ID NAO ENCONTRADO",
              "ERRO DE COMUNICACAO", "ERRO DE VERIFICACAO"}
    houve_falha = (
        any(r.resultado in falhas or r.registro_fila == "ERRO" for r in resultados)
        or bool(erro_log)
    )
    return 1 if houve_falha else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ErroSincronizacao as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        sys.exit(2)
