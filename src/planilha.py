#!/usr/bin/env python3
"""Acesso à planilha experimental via conta de serviço (gspread).

Substitui a ponte por Apps Script Web App: em vez de URL + token (que exigia
reimplantar a cada rotação), a planilha é compartilhada com o e-mail da conta
de serviço e os scripts a abrem direto pela Google Sheets API.

A chave JSON da conta de serviço NUNCA é versionada (ver .gitignore). O caminho
padrão é credenciais_sa.json na raiz do repositório; pode ser sobrescrito por
--credenciais ou pela variável de ambiente GOOGLE_APPLICATION_CREDENTIALS.
"""

from __future__ import annotations

import json
import os
import time
import unicodedata
from pathlib import Path
from typing import Any

import gspread


RAIZ = Path(__file__).resolve().parents[1]
CREDENCIAIS_PADRAO = RAIZ / "credenciais_sa.json"
ID_LOCAL = RAIZ / "spreadsheet_id.local"  # arquivo gitignored (uso local)


def id_planilha(config: dict) -> str:
    """ID da planilha SEM expor no repo público.

    Ordem: variável de ambiente SPREADSHEET_ID (GitHub Secret no CI) ->
    arquivo local `spreadsheet_id.local` (gitignored) -> config (se preenchido).
    """
    env = os.getenv("SPREADSHEET_ID")
    if env and env.strip():
        return env.strip()
    if ID_LOCAL.exists():
        valor = ID_LOCAL.read_text(encoding="utf-8").strip()
        if valor:
            return valor
    valor = str((config or {}).get("spreadsheet_id") or "").strip()
    if not valor:
        raise RuntimeError(
            "ID da planilha não definido. Configure o Secret/variável SPREADSHEET_ID "
            "(CI) ou crie o arquivo spreadsheet_id.local na raiz (uso local)."
        )
    return valor


def resolver_credenciais(caminho: str | Path | None = None) -> Path:
    if caminho:
        return Path(caminho)
    env = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("GCP_SA_KEY_FILE")
    if env:
        return Path(env)
    return CREDENCIAIS_PADRAO


def _cliente(credenciais: str | Path | None = None):
    cred = resolver_credenciais(credenciais)
    if not cred.exists():
        raise FileNotFoundError(
            f"Credenciais da conta de serviço não encontradas em {cred}. "
            "Salve a chave JSON como credenciais_sa.json na raiz do repo, ou "
            "defina GOOGLE_APPLICATION_CREDENTIALS."
        )
    # utf-8-sig tolera BOM (que pode ser inserido ao gravar a chave a partir de secret).
    with cred.open("r", encoding="utf-8-sig") as arquivo:
        info = json.load(arquivo)
    return gspread.service_account_from_dict(info)


def abrir_planilha(spreadsheet_id: str, credenciais: str | Path | None = None):
    """Abre o workbook (Spreadsheet) inteiro, para acessar várias abas."""
    return _cliente(credenciais).open_by_key(spreadsheet_id)


def abrir_worksheet(spreadsheet_id: str, aba: str, credenciais: str | Path | None = None):
    """Abre uma aba específica usando a conta de serviço."""
    return abrir_planilha(spreadsheet_id, credenciais).worksheet(aba)


def aba_por_nome(sh, nome: str, linhas: int = 1000, colunas: int = 26):
    """Retorna a aba; cria se não existir."""
    try:
        return sh.worksheet(nome)
    except gspread.WorksheetNotFound:
        return sh.add_worksheet(title=nome, rows=max(linhas, 100), cols=max(colunas, 1))


def append_aba(sh, nome: str, cabecalho: list[str], linhas: list[list[Any]],
               colunas_percentuais: list[int] | None = None) -> int:
    """Acrescenta linhas ao fim da aba (cria + cabeçalho + formato % na 1ª vez).

    colunas_percentuais: índices 1-based de colunas a formatar como porcentagem
    (os valores devem ser frações 0-1).
    """
    ws = aba_por_nome(sh, nome, linhas=20000, colunas=max(len(cabecalho), 1))
    try:
        tem_header = bool(ws.acell("A1").value)
    except Exception:  # noqa: BLE001
        tem_header = False
    if not tem_header:
        ws.update(range_name="A1", values=[cabecalho], value_input_option="RAW")
        try:
            ws.freeze(rows=1)
        except Exception:  # noqa: BLE001
            pass
        for c in (colunas_percentuais or []):
            letra = _coluna_letra(c)
            try:
                ws.format(f"{letra}2:{letra}20000",
                          {"numberFormat": {"type": "PERCENT", "pattern": "0.00%"}})
            except Exception:  # noqa: BLE001
                pass
    if linhas:
        ws.append_rows([list(r) for r in linhas], value_input_option="RAW")
    return len(linhas)


def escrever_aba(sh, nome: str, cabecalho: list[str], linhas: list[list[Any]],
                 colunas_percentuais: list[int] | None = None) -> int:
    """Limpa e grava cabeçalho + linhas em UMA escrita em lote (1 chamada).

    colunas_percentuais: índices 1-based formatados como % (valores em fração 0-1).
    """
    ws = aba_por_nome(sh, nome, linhas=len(linhas) + 10, colunas=len(cabecalho))
    ws.clear()
    ws.update(range_name="A1", values=[cabecalho] + linhas, value_input_option="RAW")
    try:
        ws.freeze(rows=1)
    except Exception:  # noqa: BLE001
        pass
    for c in (colunas_percentuais or []):
        letra = _coluna_letra(c)
        try:
            ws.format(f"{letra}2:{letra}{len(linhas) + 1}",
                      {"numberFormat": {"type": "PERCENT", "pattern": "0.00%"}})
        except Exception:  # noqa: BLE001
            pass
    return len(linhas)


def dropdown(ws, col_1based: int, linha_ini: int, linha_fim: int, opcoes: list[str]) -> None:
    """Aplica validação de dados (lista suspensa) numa coluna."""
    req = {"setDataValidation": {
        "range": {"sheetId": ws.id, "startRowIndex": linha_ini - 1, "endRowIndex": linha_fim,
                  "startColumnIndex": col_1based - 1, "endColumnIndex": col_1based},
        "rule": {"condition": {"type": "ONE_OF_LIST",
                               "values": [{"userEnteredValue": o} for o in opcoes]},
                 "showCustomUi": True, "strict": False}}}
    try:
        ws.spreadsheet.batch_update({"requests": [req]})
    except Exception:  # noqa: BLE001
        pass


def ler_valores(ws, range_a1: str = "A:M") -> list[list[Any]]:
    """Lê os valores do intervalo (1 chamada de API), sem formatação.

    UNFORMATTED_VALUE retorna números crus (ex.: 0.8887 em vez de "88,87%"),
    o que permite comparar confiança numericamente na reclassificação.
    """
    for tentativa in range(1, 6):
        try:
            return ws.get_values(range_a1, value_render_option="UNFORMATTED_VALUE")
        except gspread.exceptions.APIError as e:
            msg = str(e).lower()
            if "429" not in msg and "quota" not in msg:
                raise
            if tentativa >= 5:
                raise
            espera = 30 * tentativa
            print(f"[ler_valores] quota de leitura atingida; retry {tentativa}/5 em {espera}s")
            time.sleep(espera)


def _norm_veredito(valor) -> str | None:
    """Normaliza uma celula de conferencia: 'Correto' (qualquer caixa) -> 'Correto';
    qualquer outro valor nao vazio -> 'Errado'; vazio -> None (nao validado)."""
    s = str(valor or "").strip()
    if not s:
        return None
    return "Correto" if s.casefold() == "correto" else "Errado"


def normalizar_cabecalho(valor: Any) -> str:
    """Normaliza cabecalho: sem acento, caixa, espacos duplicados e espacos nas pontas."""
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.split()).casefold()


def mapa_cabecalhos(cabecalho: list[Any]) -> dict[str, int]:
    """Mapa normalizado -> indice 1-based."""
    return {normalizar_cabecalho(nome): i for i, nome in enumerate(cabecalho, start=1)}


def localizar_coluna(cabecalho: list[Any], nomes: list[str] | tuple[str, ...],
                     default_1based: int) -> int:
    """Localiza a primeira coluna por cabecalho normalizado; usa fallback posicional."""
    mapa = mapa_cabecalhos(cabecalho)
    for nome in nomes:
        idx = mapa.get(normalizar_cabecalho(nome))
        if idx:
            return idx
    return default_1based


def ler_conferencias(sh, aba_principal: str, col_glpi_1based: int = 13,
                     col_ia_1based: int = 14, col_reclass_1based: int = 16) -> dict:
    """Le as CONFERENCIAS HUMANAS da aba principal (modo de validacao atual).

    Convencao definida pelo usuario, em CHAMADOS_ESQUELETO_REDUZIDO:
    - coluna M (CONFERENCIA GLPI):   a classificacao historica (col C) esta 'Correto'/'Errado';
    - coluna N (CONFERENCIA IA):     a classificacao da IA (col G) esta 'Correto'/'Errado';
    - coluna P (CONFERENCIA IA - 2): a RECLASSIFICACAO (col O) esta 'Correto'/'Errado'.
    'Correto' (qualquer caixa) = acerto; outro valor nao vazio = 'Errado'; vazio = nao validado.

    Retorna {linha_planilha (str): {'ia': ..., 'glpi': ..., 'reclass': ...}} (cada um
    'Correto'|'Errado'|None) apenas para linhas com ao menos uma das colunas preenchida.
    A linha_planilha e a propria posicao na planilha (cabecalho na linha 1).
    Independente da ordem das colunas. Read-only.
    """
    try:
        ws = sh.worksheet(aba_principal)
        bloco = ws.get_values("A:P", value_render_option="UNFORMATTED_VALUE")
    except Exception:  # noqa: BLE001
        return {}
    cab = bloco[0] if bloco else []
    col_glpi_1based = localizar_coluna(
        cab, ("CONFERENCIA GLPI", "CONFERÊNCIA GLPI"), col_glpi_1based)
    col_ia_1based = localizar_coluna(
        cab, ("CONFERENCIA IA", "CONFERÊNCIA IA"), col_ia_1based)
    col_reclass_1based = localizar_coluna(
        cab, ("CONFERENCIA IA - 2", "CONFERÊNCIA IA - 2"), col_reclass_1based)

    out = {}
    for pos, linha in enumerate(bloco[1:], start=2):
        def _cel(c1):
            idx = c1 - 1
            return _norm_veredito(linha[idx]) if len(linha) > idx else None
        v_glpi = _cel(col_glpi_1based)
        v_ia = _cel(col_ia_1based)
        v_reclass = _cel(col_reclass_1based)
        if v_ia is None and v_glpi is None and v_reclass is None:
            continue
        out[str(pos)] = {"ia": v_ia, "glpi": v_glpi, "reclass": v_reclass}
    return out


def indice_coluna_por_cabecalho(ws, nome: str, default_1based: int) -> int:
    """Indice (1-based) da coluna cujo cabecalho (linha 1) casa com `nome`
    (normalizado: sem caixa, sem espacos extras e SEM acentos). Se nao encontrar,
    retorna default_1based."""
    try:
        cab = ws.row_values(1)
    except Exception:  # noqa: BLE001
        return default_1based
    alvo = normalizar_cabecalho(nome)
    for i, c in enumerate(cab, start=1):
        if normalizar_cabecalho(c) == alvo:
            return i
    return default_1based


def escrever_coluna_por_linha(ws, col_1based: int, mapa: dict,
                              value_input_option: str = "RAW") -> int:
    """Escreve valores em celulas especificas de UMA coluna, em 1 chamada (batch_update).

    mapa: {linha_1based: valor}. Nao toca em nenhuma outra celula/coluna — preserva
    G (classificacao original), M/N (conferencias) e demais campos.
    """
    if not mapa:
        return 0
    letra = _coluna_letra(col_1based)
    data = [{"range": f"{letra}{int(ln)}", "values": [[mapa[ln]]]} for ln in sorted(mapa)]
    ws.batch_update(data, value_input_option=value_input_option)
    return len(data)


def _coluna_letra(indice_1based: int) -> str:
    """Converte índice de coluna (1=A) para letra(s) A1."""
    letras = ""
    n = indice_1based
    while n > 0:
        n, resto = divmod(n - 1, 26)
        letras = chr(65 + resto) + letras
    return letras


def _normalizar(bloco: list[list[Any]], n_linhas: int, n_cols: int) -> list[list[Any]]:
    """Garante matriz n_linhas x n_cols preenchendo com '' (get_values corta vazios)."""
    saida = []
    for i in range(n_linhas):
        linha = list(bloco[i]) if i < len(bloco) else []
        linha = linha[:n_cols] + [""] * (n_cols - len(linha))
        saida.append(linha)
    return saida


def exportar_lote_gj(
    ws,
    linhas: list[dict[str, Any]],
    col_inicio: int = 7,   # G
    col_fim: int = 10,     # J
    col_conferencia: int = 13,  # M
    respeitar_conferencia: bool = True,
    ignorar_vazios: bool = True,
) -> dict[str, Any]:
    """Grava G:J em UMA escrita em lote (read-modify-write em bloco).

    - Pula linhas com CONFERÊNCIA (col M) verdadeira.
    - Não sobrescreve célula com valor vazio (preserva o que já está na planilha).
    Faz 2 leituras (bloco G:J + coluna M, em 1 batch_get) e 1 escrita.
    """
    alvos = {
        int(item["linha"]): (item.get("valores") or [])
        for item in linhas
        if int(item.get("linha", 0)) >= 2
    }
    if not alvos:
        return {"ok": False, "erro": "linhas_sem_numero_valido"}

    min_l, max_l = min(alvos), max(alvos)
    n_linhas = max_l - min_l + 1
    n_cols = col_fim - col_inicio + 1

    rng_bloco = f"{_coluna_letra(col_inicio)}{min_l}:{_coluna_letra(col_fim)}{max_l}"
    rng_conf = f"{_coluna_letra(col_conferencia)}{min_l}:{_coluna_letra(col_conferencia)}{max_l}"

    bloco_raw, conf_raw = ws.batch_get([rng_bloco, rng_conf])
    bloco = _normalizar(bloco_raw, n_linhas, n_cols)
    conf = _normalizar(conf_raw, n_linhas, 1)

    def eh_verdadeiro(valor: Any) -> bool:
        return str(valor or "").strip().upper() in {"TRUE", "VERDADEIRO", "SIM"}

    gravadas = 0
    puladas_conf = 0
    for linha_num, valores in alvos.items():
        off = linha_num - min_l
        if respeitar_conferencia and eh_verdadeiro(conf[off][0]):
            puladas_conf += 1
            continue
        for c in range(n_cols):
            novo = valores[c] if c < len(valores) else ""
            if ignorar_vazios and (novo == "" or novo is None):
                continue
            bloco[off][c] = novo
        gravadas += 1

    ws.update(range_name=rng_bloco, values=bloco, value_input_option="RAW")

    # Coluna H (Avaliação) = 2ª coluna do bloco (G+1): formatar como porcentagem.
    col_pct = col_inicio + 1
    rng_pct = f"{_coluna_letra(col_pct)}{min_l}:{_coluna_letra(col_pct)}{max_l}"
    try:
        ws.format(rng_pct, {"numberFormat": {"type": "PERCENT", "pattern": "0.00%"}})
    except Exception:  # noqa: BLE001
        pass  # formatação é cosmética; não falhar a exportação por causa dela

    return {
        "ok": True,
        "intervalo_linhas": [min_l, max_l],
        "range": rng_bloco,
        "range_percentual": rng_pct,
        "linhas_recebidas": len(alvos),
        "linhas_gravadas": gravadas,
        "linhas_puladas_conferencia": puladas_conf,
    }
