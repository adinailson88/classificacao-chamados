#!/usr/bin/env python3
"""Prepara a aba VALIDACAO_HUMANA para revisão técnica (roteiro, etapas 24-27).

Monta, para cada chamado a validar, o contexto (título, descrições, categoria
original, categoria IA da etapa 1 e da etapa 2) + colunas VAZIAS para o humano
preencher: categoria_validada, decisão, justificativa, avaliador, data,
usar_para_treino e versão da taxonomia. Cria listas suspensas em `decisao` e
`usar_para_treino`.

Por padrão seleciona os DIVERGENTES (IA etapa 1 ≠ categoria original) — a prioridade
do roteiro (Etapa 25). Use --modo todos para validar toda a base (Etapa 26).

SEGURANÇA: se a aba já tiver validações preenchidas, ABORTA (use --forcar para
sobrescrever) — evita apagar trabalho humano. Sem --aplicar = dry-run.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planilha as pl  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
VERSAO_TAXONOMIA = "TAXONOMIA_MANUTENCAO_V1_2026_06"
DECISOES = ["IA_CERTA", "GLPI_CERTO", "AMBOS_ERRADOS", "AMBOS_CORRETOS", "CASO_AMBIGUO", "NAO_AVALIADO"]
USAR_TREINO = ["SIM", "NAO", "REVISAR"]
CABECALHO = ["linha_planilha", "id_chamado", "titulo", "descricao_glpi", "titulo_osm",
             "descricao_osm", "categoria_original", "categoria_ia_etapa1", "confianca_etapa1",
             "categoria_ia_etapa2", "categoria_validada", "decisao", "justificativa",
             "avaliador", "data_validacao", "usar_para_treino", "versao_taxonomia"]


def cel(linha, idx) -> str:
    return str(linha[idx] or "").strip() if (idx is not None and idx < len(linha)) else ""


def parse_conf(v) -> float:
    try:
        f = float(str(v).replace("%", "").replace(",", ".").strip())
        return f / 100.0 if f > 1 else f
    except (ValueError, TypeError):
        return 0.0


def carregar_snapshot(sh, nome):
    try:
        vals = sh.worksheet(nome).get_values("A:J", value_render_option="UNFORMATTED_VALUE")
    except Exception:  # noqa: BLE001
        return {}
    m = {}
    for r in vals[1:]:
        if len(r) < 6:
            continue
        try:
            m[int(r[1])] = (str(r[4]).strip(), parse_conf(r[5]))
        except (ValueError, TypeError):
            pass
    return m


def parse_args():
    p = argparse.ArgumentParser(description="Prepara a aba VALIDACAO_HUMANA.")
    p.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    p.add_argument("--credenciais", default=None)
    p.add_argument("--modo", choices=["divergentes", "todos"], default="divergentes")
    p.add_argument("--max", type=int, default=0, help="Limita o nº de casos (0 = todos os selecionados).")
    p.add_argument("--aplicar", action="store_true")
    p.add_argument("--forcar", action="store_true", help="Sobrescreve mesmo com validações preenchidas.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    with args.config.open(encoding="utf-8") as f:
        config = json.load(f)
    aba = config["aba_principal"]
    abas = config["abas_experimento"]

    try:
        sh = pl.abrir_planilha(pl.id_planilha(config), args.credenciais)
        ws = sh.worksheet(aba)
        valores = pl.ler_valores(ws, config["range_leitura"])
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr); return 2
    except Exception as e:  # noqa: BLE001
        print(f"Falha ao acessar a planilha: {type(e).__name__}: {e}", file=sys.stderr); return 1

    cab = valores[0] if valores else []
    norm = lambda s: " ".join(str(s or "").split()).casefold()  # noqa: E731
    idx = {norm(n): i for i, n in enumerate(cab)}
    i = {k: idx.get(norm(v)) for k, v in {
        "id": "ID Chamado", "tit": "TÍTULO", "cat": "CATEGORIA COMPLETA", "dg": "DESCRIÇÃO GLPI",
        "to": "TÍTULO O.S.M.", "do": "DESCRIÇÃO O.S.M.", "g": "Classificação IA", "exe": "Executor",
    }.items()}

    snap = carregar_snapshot(sh, abas["snapshot_etapa_1"])

    sel = []
    for pos, linha in enumerate(valores[1:], start=2):
        orig = cel(linha, i["cat"])
        if not orig or pos not in snap:
            continue
        cat_ia_1, conf_1 = snap[pos]
        exec_atual = cel(linha, i["exe"])
        cat_ia_2 = cel(linha, i["g"]) if exec_atual.startswith("Reclass") else ""
        divergente = cat_ia_1 != orig
        if args.modo == "divergentes" and not divergente:
            continue
        sel.append([
            pos, cel(linha, i["id"]), cel(linha, i["tit"])[:300], cel(linha, i["dg"])[:500],
            cel(linha, i["to"])[:300], cel(linha, i["do"])[:500], orig, cat_ia_1, round(conf_1, 4),
            cat_ia_2, "", "", "", "", "", "", VERSAO_TAXONOMIA,
        ])
        if args.max and len(sel) >= args.max:
            break

    print(f"aba_destino={abas['validacao_humana']} | modo={args.modo} | casos_selecionados={len(sel)}")
    if not sel:
        print("Nada a preparar (talvez a Etapa 1 ainda não tenha classificado / sem divergências).")
        return 0

    if not args.aplicar:
        print("modo=dry-run (nada gravado). Exemplo de 1 caso:")
        print(json.dumps(dict(zip(CABECALHO, sel[0])), ensure_ascii=False, indent=2))
        return 0

    # Segurança: não sobrescrever validações já feitas
    try:
        ws_v = sh.worksheet(abas["validacao_humana"])
        existentes = ws_v.get_all_values()
        col_dec = CABECALHO.index("decisao")
        ja_validado = any(len(r) > col_dec and str(r[col_dec]).strip() for r in existentes[1:])
        if ja_validado and not args.forcar:
            print("ABORTADO: VALIDACAO_HUMANA já tem decisões preenchidas. Use --forcar para sobrescrever.",
                  file=sys.stderr)
            return 3
    except Exception:  # noqa: BLE001
        pass

    pl.escrever_aba(sh, abas["validacao_humana"], CABECALHO, sel, colunas_percentuais=[9])
    # listas suspensas (decisao=col 12, usar_para_treino=col 16)
    ws_v = sh.worksheet(abas["validacao_humana"])
    pl.dropdown(ws_v, 12, 2, len(sel) + 1, DECISOES)
    pl.dropdown(ws_v, 16, 2, len(sel) + 1, USAR_TREINO)
    print(f"OK: {len(sel)} casos gravados em {abas['validacao_humana']} (com dropdowns).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
