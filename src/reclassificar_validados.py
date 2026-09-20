#!/usr/bin/env python3
"""Reclassifica chamados com verdade humana decidida e coluna O vazia.

A verdade e obtida pela regra unica de ``decisao_validada`` sobre M/N/P/Q. O
script grava somente a coluna O, preservando G e todas as conferencias humanas.
Sem ``--aplicar`` opera em dry-run.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import decisao_validada as dv  # noqa: E402
import memoria_validada as mv  # noqa: E402
import planilha as pl  # noqa: E402
from modelos_reclassificacao import cel, treinar_reclass  # noqa: E402
from tempo import agora_bahia  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
ABA_AUDITORIA = "RECLASS_VALIDADOS"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reclassifica chamados com verdade M/N/P/Q na coluna O."
    )
    parser.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    parser.add_argument("--credenciais", default=None)
    parser.add_argument(
        "--modelo",
        choices=["transformer_ft", "robusto", "producao", "baseline"],
        default="transformer_ft",
    )
    parser.add_argument("--tamanho-turno", type=int, default=15)
    parser.add_argument(
        "--max-turnos",
        type=int,
        default=1,
        help="Turnos por execucao; 0 processa todos os candidatos.",
    )
    parser.add_argument("--aplicar", action="store_true")
    return parser.parse_args()


def _normalizar_cabecalho(valor: str) -> str:
    return pl.normalizar_cabecalho(valor)


def main() -> int:
    args = parse_args()
    with args.config.open(encoding="utf-8") as arquivo:
        config = json.load(arquivo)

    aba = config["aba_principal"]
    run_id = config.get("run_id", "")
    gerado = agora_bahia()
    tamanho_turno = max(1, int(args.tamanho_turno))

    try:
        sh = pl.abrir_planilha(pl.id_planilha(config), args.credenciais)
        ws = sh.worksheet(aba)
        valores = pl.ler_valores(ws, "A:Q")
    except FileNotFoundError as erro:
        print(str(erro), file=sys.stderr)
        return 2
    except Exception as erro:  # noqa: BLE001
        print(f"Falha ao acessar a planilha: {type(erro).__name__}: {erro}", file=sys.stderr)
        return 1

    cabecalho = valores[0] if valores else []
    indices = {_normalizar_cabecalho(nome): i for i, nome in enumerate(cabecalho)}

    def idx(*nomes: str) -> int | None:
        for nome in nomes:
            encontrado = indices.get(_normalizar_cabecalho(nome))
            if encontrado is not None:
                return encontrado
        return None

    i_id = idx("ID Chamado", "ID")
    i_titulo = idx("TITULO", "TÍTULO")
    i_categoria = idx("CATEGORIA COMPLETA")
    i_desc_glpi = idx("DESCRICAO GLPI", "DESCRIÇÃO GLPI")
    i_titulo_osm = idx("TITULO O.S.M.", "TÍTULO O.S.M.")
    i_desc_osm = idx("DESCRICAO O.S.M.", "DESCRIÇÃO O.S.M.")
    i_ia = idx("Classificacao IA", "Classificação IA")

    col_o = pl.indice_coluna_por_cabecalho(ws, "Classificacao IA - 2", 15)
    i_o = col_o - 1

    elegiveis: list[tuple[int, str, str]] = []
    info: dict[int, dict[str, str | bool]] = {}
    for posicao, linha in enumerate(valores[1:], start=2):
        categoria = pl.normalizar_categoria(cel(linha, i_categoria))
        texto = "\n".join(
            parte
            for parte in [
                cel(linha, i_titulo),
                cel(linha, i_desc_glpi),
                cel(linha, i_titulo_osm),
                cel(linha, i_desc_osm),
            ]
            if parte
        )
        if not categoria or not texto:
            continue
        elegiveis.append((posicao, texto, categoria))
        info[posicao] = {
            "id": cel(linha, i_id),
            "cat_C": categoria,
            "cat_G": cel(linha, i_ia),
            "texto": texto,
            "o_preenchido": bool(cel(linha, i_o)),
        }

    decisoes = dv.carregar_decisoes(sh, aba)
    conferencias = pl.ler_conferencias(sh, aba)

    candidatos = [
        linha
        for linha, dados in info.items()
        if not dados["o_preenchido"]
        and linha in decisoes
        and decisoes[linha].get("status") == dv.STATUS_DECIDIDO
        and not decisoes[linha].get("conflito")
        and decisoes[linha].get("decidida")
    ]
    candidatos.sort()

    total = len(candidatos)
    print(
        f"run_id={run_id} | elegiveis={len(elegiveis)} | "
        f"validados_pendentes={total} | modelo={args.modelo}"
    )
    if total == 0:
        print("0 chamados com verdade decidida e coluna O pendente.")
        return 0

    quantidade = total if args.max_turnos <= 0 else min(
        total,
        args.max_turnos * tamanho_turno,
    )
    selecionados = candidatos[:quantidade]
    selecionados_set = set(selecionados)

    base_textos = [texto for linha, texto, _ in elegiveis if linha not in selecionados_set]
    base_categorias = [categoria for linha, _, categoria in elegiveis if linha not in selecionados_set]

    memoria_cfg = config.get("memoria_validada", {})
    if memoria_cfg.get("habilitada", True):
        aba_memoria = memoria_cfg.get("aba_origem") or aba
        memoria = mv.carregar_memoria_validada(sh, aba_memoria)
        memoria = [
            item
            for item in memoria
            if int(item.get("linha_planilha") or 0) not in selecionados_set
        ]
    else:
        memoria = []

    base_textos, base_categorias = mv.expandir_treino_com_memoria(
        base_textos,
        base_categorias,
        memoria,
        peso=int(memoria_cfg.get("peso_treino", 3)),
    )

    print(
        f"lote={len(selecionados)} | base_treino={len(base_textos)} | "
        f"memoria_validada={len(memoria)} | treinando"
    )
    predict_fn, tag = treinar_reclass(
        args.modelo,
        base_textos,
        base_categorias,
        config=config,
    )
    predicoes, confiancas = predict_fn([str(info[linha]["texto"]) for linha in selecionados])

    registros = []
    for linha, predicao, confianca in zip(selecionados, predicoes, confiancas):
        dados = info[linha]
        decisao = decisoes[linha]
        verdade = str(decisao.get("decidida") or "")
        cat_o = str(predicao)
        conferencia = conferencias.get(str(linha), {})
        registros.append({
            "linha": linha,
            "id": dados["id"],
            "cat_C": dados["cat_C"],
            "cat_G": dados["cat_G"],
            "conf_ia_N": conferencia.get("ia"),
            "conf_glpi_M": conferencia.get("glpi"),
            "verdade": verdade,
            "fonte_verdade": decisao.get("fonte_decisao", ""),
            "cat_o": cat_o,
            "acertou": cat_o == verdade,
            "conf_o": round(float(confianca), 4),
        })

    acertos = sum(1 for registro in registros if registro["acertou"])
    acertos_g = sum(1 for registro in registros if registro["cat_G"] == registro["verdade"])
    ganho_vs_g = acertos - acertos_g
    print(
        f"reclassificados={len(registros)} | acertos_reclass={acertos}/{len(registros)} | "
        f"acertos_ia_original={acertos_g}/{len(registros)} | ganho_vs_g={ganho_vs_g} | "
        f"executor=Reclass_{tag}"
    )

    if not args.aplicar:
        print("modo=dry-run (nada gravado).")
        return 0

    if ganho_vs_g < 0:
        print(
            "ABORTADO: a reclassificacao pioraria a IA original nas linhas com verdade decidida. "
            "A coluna O nao foi alterada.",
            file=sys.stderr,
        )
        # Codigo 3 (nao 1): guarda de qualidade intencional, nao falha de execucao —
        # permite ao workflow distinguir "nada gravado por decisao" de erro real.
        return 3

    mapa_o = {registro["linha"]: registro["cat_o"] for registro in registros}
    for tentativa in range(1, 4):
        try:
            pl.escrever_coluna_por_linha(ws, col_o, mapa_o)
            break
        except Exception as erro:  # noqa: BLE001
            if tentativa >= 3:
                print(
                    f"FALHA ao gravar coluna O: {type(erro).__name__}: {erro}",
                    file=sys.stderr,
                )
                return 1
            print(
                f"coluna O: falha transitoria ({type(erro).__name__}); "
                f"retry {tentativa}/3 em {10 * tentativa}s",
                file=sys.stderr,
            )
            time.sleep(10 * tentativa)

    cab_auditoria = [
        "run_id",
        "linha_planilha",
        "id_chamado",
        "categoria_C",
        "categoria_G",
        "conferencia_ia_N",
        "conferencia_glpi_M",
        "verdade_derivada",
        "categoria_reclass_O",
        "reclass_correto",
        "confianca_reclass",
        "modelo",
        "data",
    ]
    linhas_auditoria = [
        [
            run_id,
            registro["linha"],
            registro["id"],
            registro["cat_C"],
            registro["cat_G"],
            registro["conf_ia_N"],
            registro["conf_glpi_M"],
            registro["verdade"],
            registro["cat_o"],
            str(registro["acertou"]),
            registro["conf_o"],
            f"Reclass_{tag}",
            gerado,
        ]
        for registro in registros
    ]
    try:
        pl.append_aba(sh, ABA_AUDITORIA, cab_auditoria, linhas_auditoria)
    except Exception as erro:  # noqa: BLE001
        print(
            f"[aviso] coluna O gravada, mas auditoria falhou: {type(erro).__name__}: {erro}",
            file=sys.stderr,
        )

    aba_historico = config.get("multimodelo", {}).get(
        "aba_historico_reclassificacao",
        "RECLASS_HISTORICO",
    )
    cab_historico = [
        "data",
        "run_id",
        "modelo",
        "tipo_rodada",
        "linha_planilha",
        "id_chamado",
        "categoria_referencia",
        "categoria_antes",
        "confianca_antes",
        "acerto_antes",
        "categoria_depois",
        "confianca_depois",
        "acerto_depois",
        "mudou",
        "delta_confianca",
        "resultado",
        "base_comparacao",
        "metodo_reclassificacao",
        "limiar_alta_confianca",
        "usar_calibrado",
        "so_validados",
        "max_turnos",
        "tamanho_turno",
        "gravou_coluna_2",
    ]
    linhas_historico = []
    for registro in registros:
        antes_ok = registro["cat_G"] == registro["verdade"]
        depois_ok = bool(registro["acertou"])
        if not antes_ok and depois_ok:
            resultado = "corrigido"
        elif antes_ok and not depois_ok:
            resultado = "prejudicado"
        elif antes_ok and depois_ok:
            resultado = "mantido_correto"
        else:
            resultado = "mantido_errado"
        linhas_historico.append([
            gerado,
            run_id,
            f"Reclass_{tag}",
            "validados_coluna_o",
            registro["linha"],
            registro["id"],
            registro["verdade"],
            registro["cat_G"],
            "",
            str(antes_ok),
            registro["cat_o"],
            registro["conf_o"],
            str(depois_ok),
            str(registro["cat_o"] != registro["cat_G"]),
            "",
            resultado,
            "validada",
            f"Reclass_{tag}",
            "",
            "False",
            "True",
            int(args.max_turnos),
            tamanho_turno,
            "True",
        ])
    try:
        pl.append_aba(sh, aba_historico, cab_historico, linhas_historico)
    except Exception as erro:  # noqa: BLE001
        print(
            f"[aviso] coluna O gravada, mas historico consolidado falhou: "
            f"{type(erro).__name__}: {erro}",
            file=sys.stderr,
        )

    print(
        f"OK: {len(registros)} reclassificados na coluna O | "
        f"acertos={acertos}/{len(registros)} | restam {total - len(selecionados)} pendentes."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
