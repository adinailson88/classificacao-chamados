#!/usr/bin/env python3
"""Congela o NOVO CORTE CIENTIFICO (Trilha B) da planilha viva.

A rodada canonica do artigo congelado foi aposentada porque a identidade do
corpus nao incluia o texto bruto entregue aos modelos. Este modulo e o primeiro
passo da Trilha B e corrige isso: le a aba principal e a fonte do GLPI UMA vez,
monta o corpus completo (A:Q, referencia humana, data de abertura e campus) e
fixa tres impressoes digitais:

- ``hash_entrada_modelo``: id e os quatro campos textuais, exatamente como lidos;
- ``hash_referencia``: id, categoria historica, referencia humana e fonte;
- ``hash_corte``: tudo o que ha no corte, inclusive data e campus.

Por padrao e DRY-RUN: nada e gravado. Com ``--aplicar`` grava o manifesto
sanitizado em ``docs/dados/trilha_b/`` e cria a aba imutavel de snapshot
``CORTE_B_<aaaammdd>`` na planilha (recusa-se a sobrescrever uma aba existente).
Titulos, descricoes e IDs nao entram em nenhum arquivo versionado; o snapshot
com texto vive apenas na planilha privada.

Nao toca nos artefatos de ``MANIFESTO_ARTIGO_CONGELADO.json`` nem nas colunas
M, N, P e Q da planilha.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import construir_grupos_textuais as cgt  # noqa: E402
import conferencia_derivada as cd  # noqa: E402
import planilha as pl  # noqa: E402
from tempo import agora_bahia  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
MANIFESTO_CONGELADO = RAIZ / "docs" / "dados" / "MANIFESTO_ARTIGO_CONGELADO.json"
DADOS_B = RAIZ / "docs" / "dados" / "trilha_b"
SAIDA_JSON_PADRAO = DADOS_B / "corte_b.json"
SAIDA_MD_PADRAO = RAIZ / "docs" / "trilha_b" / "CORTE_B.md"

# Os chamados abertos ate esta data formam o corte historico (equivalente ao
# corpus do artigo anterior); os posteriores formam o teste prospectivo.
CORTE_TEMPORAL_PADRAO = "2026-07-31"
ABA_FONTE_PADRAO = "CHAMADOS"
CABECALHO_SNAPSHOT = [
    "id_chamado", "titulo", "descricao_glpi", "titulo_osm", "descricao_osm",
    "categoria_historica", "conferencia_glpi", "categoria_manual",
    "referencia_humana", "fonte_referencia", "data_abertura", "campus",
    "periodo",
]
PERIODO_HISTORICO = "historico"
PERIODO_PROSPECTIVO = "prospectivo"


def _sha256_json(objeto: Any) -> str:
    bruto = json.dumps(objeto, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(bruto).hexdigest()


def garantir_fora_do_congelado(caminho: Path,
                               manifesto: Path = MANIFESTO_CONGELADO) -> None:
    """Recusa gravar sobre qualquer artefato protegido do artigo congelado."""
    if not manifesto.exists():
        return
    protegidos = {
        (RAIZ / item["path"]).resolve()
        for item in json.loads(manifesto.read_text(encoding="utf-8"))["arquivos"]
    }
    if Path(caminho).resolve() in protegidos:
        raise RuntimeError(
            f"{caminho} pertence ao ARTIGO_CONGELADO e nao pode ser sobrescrito "
            "pela Trilha B.")


def analisar_data(texto: str) -> datetime | None:
    texto = str(texto or "").strip()
    for formato in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, formato)
        except ValueError:
            continue
    return None


def ler_fonte_temporal(sh_fonte, aba: str = ABA_FONTE_PADRAO) -> dict[str, dict[str, str]]:
    """Mapa id -> data de abertura e campus, lido da fonte do GLPI por cabecalho."""
    bloco = sh_fonte.worksheet(aba).get_values(
        "A:Z", value_render_option="UNFORMATTED_VALUE")
    cab = bloco[0] if bloco else []
    c_id = pl.localizar_coluna(cab, ("ID Chamado", "ID"), 1)
    c_data = pl.localizar_coluna(cab, ("DATA E HORA ABERTURA",), 3)
    c_campus = pl.localizar_coluna(cab, ("CAMPUS",), 8)

    def cel(linha: list[Any], c1: int) -> str:
        i = c1 - 1
        return str(linha[i] or "").strip() if len(linha) > i else ""

    mapa: dict[str, dict[str, str]] = {}
    for linha in bloco[1:]:
        id_chamado = cd.normalizar_id(cel(linha, c_id))
        if not id_chamado:
            continue
        mapa[id_chamado] = {"data_abertura": cel(linha, c_data),
                            "campus": cel(linha, c_campus)}
    return mapa


def montar_corte(registros: list[dict[str, str]],
                 temporal: dict[str, dict[str, str]],
                 corte_temporal: str = CORTE_TEMPORAL_PADRAO) -> list[dict[str, str]]:
    """Junta registros, referencia humana, data e campus. Logica pura."""
    limite = analisar_data(corte_temporal)
    if limite is None:
        raise ValueError(f"corte temporal invalido: {corte_temporal!r}")
    limite = limite.replace(hour=23, minute=59)
    linhas = []
    for r in registros:
        id_chamado = r.get("id", "")
        extra = temporal.get(id_chamado, {})
        data_txt = extra.get("data_abertura", "")
        data = analisar_data(data_txt)
        referencia = cgt.referencia_humana(r)
        fonte = ""
        if referencia:
            fonte = ("conferencia_glpi"
                     if str(r.get("conferencia_glpi", "")).strip().casefold() == "correto"
                     else "manual")
        periodo = ""
        if data is not None:
            periodo = PERIODO_HISTORICO if data <= limite else PERIODO_PROSPECTIVO
        linhas.append({
            "id_chamado": id_chamado,
            "titulo": r.get("titulo", ""),
            "descricao_glpi": r.get("descricao_glpi", ""),
            "titulo_osm": r.get("titulo_osm", ""),
            "descricao_osm": r.get("descricao_osm", ""),
            "categoria_historica": r.get("categoria_historica", ""),
            "conferencia_glpi": r.get("conferencia_glpi", ""),
            "categoria_manual": r.get("categoria_manual", ""),
            "referencia_humana": referencia,
            "fonte_referencia": fonte,
            "data_abertura": data_txt,
            "campus": extra.get("campus", ""),
            "periodo": periodo,
        })
    linhas.sort(key=lambda x: x["id_chamado"])
    return linhas


def problemas_do_corte(corte: list[dict[str, str]]) -> dict[str, int]:
    ids = [r["id_chamado"] for r in corte]
    taxonomia = {r["categoria_historica"] for r in corte if r["categoria_historica"]}
    return {
        "linhas_sem_id": sum(1 for i in ids if not i),
        "ids_duplicados": sum(1 for _, n in Counter(i for i in ids if i).items() if n > 1),
        "linhas_sem_categoria_historica": sum(
            1 for r in corte if not r["categoria_historica"]),
        "linhas_sem_referencia": sum(1 for r in corte if not r["referencia_humana"]),
        "referencia_fora_da_taxonomia_historica": sum(
            1 for r in corte
            if r["referencia_humana"] and r["referencia_humana"] not in taxonomia),
        "linhas_sem_data_valida": sum(1 for r in corte if not r["periodo"]),
        "linhas_sem_campus": sum(1 for r in corte if not r["campus"]),
        "linhas_sem_texto": sum(
            1 for r in corte
            if not any(r[c].strip() for c in (
                "titulo", "descricao_glpi", "titulo_osm", "descricao_osm"))),
    }


def impressoes_digitais(corte: list[dict[str, str]]) -> dict[str, str]:
    entrada = [[r["id_chamado"], r["titulo"], r["descricao_glpi"],
                r["titulo_osm"], r["descricao_osm"]] for r in corte]
    referencia = [[r["id_chamado"], r["categoria_historica"],
                   r["referencia_humana"], r["fonte_referencia"]] for r in corte]
    completo = [[r[c] for c in CABECALHO_SNAPSHOT] for r in corte]
    return {
        "hash_entrada_modelo": _sha256_json(entrada),
        "hash_referencia": _sha256_json(referencia),
        "hash_corte": _sha256_json(completo),
    }


def montar_relatorio(corte: list[dict[str, str]], corte_temporal: str,
                     aba_snapshot: str) -> dict[str, Any]:
    problemas = problemas_do_corte(corte)
    bloqueios = [k for k, v in problemas.items() if v]
    ref = Counter(r["referencia_humana"] for r in corte if r["referencia_humana"])
    hist = Counter(r["categoria_historica"] for r in corte if r["categoria_historica"])
    por_ano = Counter(r["data_abertura"][:4] for r in corte if r["periodo"])
    por_campus = Counter(r["campus"] for r in corte if r["campus"])
    por_periodo = Counter(r["periodo"] for r in corte if r["periodo"])
    alteradas = sum(1 for r in corte if r["fonte_referencia"] == "manual")
    return {
        "schema_version": 1,
        "trilha": "B",
        "status": "apto_para_congelar" if not bloqueios else "bloqueado",
        "corpus": {
            "linhas": len(corte),
            "referencias_validas": sum(ref.values()),
            "alteracoes_do_rotulo_historico": alteradas,
            "taxa_de_alteracao": round(alteradas / len(corte), 4) if corte else 0.0,
            "categorias_historicas": len(hist),
            "categorias_na_referencia": len(ref),
            "categorias_com_menos_de_5": sorted(c for c, n in ref.items() if n < 5),
        },
        "temporal": {
            "corte_temporal": corte_temporal,
            "por_periodo": dict(sorted(por_periodo.items())),
            "por_ano": dict(sorted(por_ano.items())),
            "primeira_abertura": min((r["data_abertura"] for r in corte if r["periodo"]),
                                     default=""),
            "ultima_abertura": max((r["data_abertura"] for r in corte if r["periodo"]),
                                   default=""),
        },
        "campus": dict(sorted(por_campus.items())),
        "distribuicao_referencia": [
            {"categoria": c, "n": n}
            for c, n in sorted(ref.items(), key=lambda kv: (-kv[1], kv[0]))],
        "problemas": problemas,
        "bloqueios": bloqueios,
        "impressoes_digitais": impressoes_digitais(corte),
        "aba_snapshot": aba_snapshot,
        "regra_referencia": (
            "M='Correto' -> categoria historica; M='Errado' + Q preenchida -> "
            "categoria manual; demais casos sem referencia"),
    }


def renderizar_markdown(r: dict[str, Any]) -> str:
    c, t, h = r["corpus"], r["temporal"], r["impressoes_digitais"]
    linhas = [
        "# Corte B (novo corte científico)",
        "",
        "> Relatório sanitizado. Não contém títulos, descrições nem IDs de chamados.",
        "",
        f"**Estado:** `{r['status']}`  ",
        f"**Gerado em:** {r.get('gerado_em', 'não informado')}  ",
        f"**Hash do corte:** `{h['hash_corte']}`",
        "",
        "## Corpus",
        "",
        "| Item | Total |",
        "|---|---:|",
        f"| Chamados | {c['linhas']} |",
        f"| Referências humanas válidas | {c['referencias_validas']} |",
        f"| Alterações do rótulo histórico | {c['alteracoes_do_rotulo_historico']} |",
        f"| Categorias históricas | {c['categorias_historicas']} |",
        f"| Categorias na referência | {c['categorias_na_referencia']} |",
        "",
        "## Alcance temporal",
        "",
        f"- Primeira abertura: {t['primeira_abertura']}; última: {t['ultima_abertura']}.",
        f"- Corte temporal: {t['corte_temporal']}.",
        "",
        "| Período | Chamados |",
        "|---|---:|",
    ]
    linhas += [f"| {k} | {v} |" for k, v in t["por_periodo"].items()]
    linhas += ["", "## Campus", "", "| Campus | Chamados |", "|---|---:|"]
    linhas += [f"| {k} | {v} |" for k, v in r["campus"].items()]
    linhas += ["", "## Validações", "", "| Verificação | Ocorrências |", "|---|---:|"]
    linhas += [f"| {k.replace('_', ' ')} | {v} |" for k, v in r["problemas"].items()]
    linhas += [
        "",
        "## Identidade",
        "",
        f"- Entrada dos modelos: `{h['hash_entrada_modelo']}`.",
        f"- Referência: `{h['hash_referencia']}`.",
        f"- Snapshot imutável: aba `{r['aba_snapshot']}`.",
        "- Script: `src/corte_b.py`.",
        "",
    ]
    return "\n".join(linhas)


def gravar_snapshot(sh, aba: str, corte: list[dict[str, str]]) -> int:
    """Cria a aba de snapshot; recusa-se a sobrescrever uma aba existente."""
    existentes = {ws.title for ws in sh.worksheets()}
    if aba in existentes:
        raise RuntimeError(f"A aba {aba} ja existe; o snapshot e imutavel.")
    linhas = [[r[c] for c in CABECALHO_SNAPSHOT] for r in corte]
    return pl.escrever_aba(sh, aba, CABECALHO_SNAPSHOT, linhas)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    p.add_argument("--credenciais", default=None)
    p.add_argument("--fonte-id", default=os.getenv("FONTE_GLPI_SPREADSHEET_ID", ""),
                   help="id da planilha-fonte do GLPI (aba CHAMADOS)")
    p.add_argument("--aba-fonte", default=ABA_FONTE_PADRAO)
    p.add_argument("--corte-temporal", default=CORTE_TEMPORAL_PADRAO)
    p.add_argument("--json", type=Path, default=SAIDA_JSON_PADRAO)
    p.add_argument("--markdown", type=Path, default=SAIDA_MD_PADRAO)
    p.add_argument("--aplicar", action="store_true",
                   help="grava o manifesto e cria a aba de snapshot; sem isto e dry-run")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if not args.fonte_id:
        print("Informe --fonte-id ou FONTE_GLPI_SPREADSHEET_ID.", file=sys.stderr)
        return 2
    garantir_fora_do_congelado(args.json)
    garantir_fora_do_congelado(args.markdown)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    sh = pl.abrir_planilha(pl.id_planilha(config), args.credenciais)
    sh_fonte = pl.abrir_planilha(args.fonte_id, args.credenciais)
    registros = cgt.ler_registros(sh, config)
    temporal = ler_fonte_temporal(sh_fonte, args.aba_fonte)
    corte = montar_corte(registros, temporal, args.corte_temporal)
    aba = f"CORTE_B_{datetime.now().strftime('%Y%m%d')}"
    relatorio = montar_relatorio(corte, args.corte_temporal, aba)
    relatorio["gerado_em"] = agora_bahia()
    relatorio["fonte"] = config["aba_principal"]
    relatorio["script_origem"] = "src/corte_b.py"
    texto = renderizar_markdown(relatorio)
    print(texto)
    if relatorio["status"] != "apto_para_congelar":
        print("Corte bloqueado: nada foi gravado.", file=sys.stderr)
        return 2
    if not args.aplicar:
        print("DRY-RUN: nada foi gravado. Use --aplicar para congelar.")
        return 0
    n = gravar_snapshot(sh, aba, corte)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(relatorio, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    args.markdown.write_text(texto, encoding="utf-8")
    print(f"Snapshot {aba} criado com {n} linhas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
