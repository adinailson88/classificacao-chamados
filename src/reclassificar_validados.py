#!/usr/bin/env python3
"""Reclassificacao dos chamados JA VALIDADOS (conferencia dupla M e N preenchidas).

Seleciona os chamados com a CONFERENCIA HUMANA completa — coluna M (CONFERENCIA GLPI)
e coluna N (CONFERENCIA IA) preenchidas — e ainda SEM reclassificacao (coluna O,
"Classificacao IA - 2", vazia). Reclassifica com o modelo MAIS ROBUSTO disponivel
(transformer multilingue + memoria validada; fallback LSTM/RF) e grava o resultado na
coluna O, SEM tocar em G (classificacao original), M ou N. Progressivo, em turnos de 15
(pensado para cron */15: no maximo 15 chamados a cada execucao).

Quando a verdade e derivavel das conferencias, mede o acerto da reclassificacao robusta:
- N (CONFERENCIA IA) = "Correto"  -> a categoria certa e a da IA original (coluna G);
- senao, M (CONFERENCIA GLPI) = "Correto" -> a categoria certa e a historica (coluna C);
- ambas "Errado" -> verdade desconhecida (nao entra no acerto).

Auditoria por chamado em RECLASS_VALIDADOS. Sem --aplicar = dry-run (nada gravado).
Acesso via conta de servico (gspread).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planilha as pl  # noqa: E402
import memoria_validada as mv  # noqa: E402
from executar_etapa2 import treinar_reclass, cel  # noqa: E402
from tempo import agora_bahia  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
DADOS = RAIZ / "dados"
ABA_AUDITORIA = "RECLASS_VALIDADOS"


def parse_args():
    p = argparse.ArgumentParser(description="Reclassifica chamados validados (M e N) na coluna O.")
    p.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    p.add_argument("--credenciais", default=None)
    p.add_argument("--modelo", choices=["transformer_ft", "robusto", "producao", "baseline"],
                   default="transformer_ft",
                   help="Modelo de reclassificacao. Padrao: transformer_ft = BERTimbau com "
                        "fine-tuning (contextual). 'robusto' = embeddings MiniLM + LogReg.")
    p.add_argument("--tamanho-turno", type=int, default=15)
    p.add_argument("--max-turnos", type=int, default=1, help="Turnos de 15 por execucao (0=todos).")
    p.add_argument("--aplicar", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    with args.config.open(encoding="utf-8") as f:
        config = json.load(f)
    aba = config["aba_principal"]
    run_id = config.get("run_id", "")
    gerado = agora_bahia()
    tam = max(1, args.tamanho_turno)

    try:
        sh = pl.abrir_planilha(pl.id_planilha(config), args.credenciais)
        ws = sh.worksheet(aba)
        valores = pl.ler_valores(ws, "A:O")
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr); return 2
    except Exception as e:  # noqa: BLE001
        print(f"Falha ao acessar a planilha: {type(e).__name__}: {e}", file=sys.stderr); return 1

    cab = valores[0] if valores else []
    import unicodedata
    def norm(s):  # casefold + remove acentos (cabecalhos da planilha tem acento)
        t = unicodedata.normalize("NFKD", str(s or ""))
        t = "".join(c for c in t if not unicodedata.combining(c))
        return " ".join(t.split()).casefold()
    idx = {norm(n): i for i, n in enumerate(cab)}
    i_id, i_tit, i_cat = idx.get(norm("ID Chamado")), idx.get(norm("TITULO")), idx.get(norm("CATEGORIA COMPLETA"))
    i_dg, i_to, i_do = idx.get(norm("DESCRICAO GLPI")), idx.get(norm("TITULO O.S.M.")), idx.get(norm("DESCRICAO O.S.M."))
    i_g = idx.get(norm("Classificacao IA"))
    col_o = pl.indice_coluna_por_cabecalho(ws, "Classificacao IA - 2", 15)
    i_o = col_o - 1

    # Base rotulada (texto + categoria historica) e indice por linha.
    elegiveis = []   # (linha, texto, cat_C)
    info = {}
    for pos, linha in enumerate(valores[1:], start=2):
        cat = cel(linha, i_cat)
        texto = "\n".join(c for c in [cel(linha, i_tit), cel(linha, i_dg),
                                      cel(linha, i_to), cel(linha, i_do)] if c)
        if not (cat and texto):
            continue
        elegiveis.append((pos, texto, cat))
        info[pos] = {"id": cel(linha, i_id), "cat_C": cat, "cat_G": cel(linha, i_g), "texto": texto,
                     "o_preenchido": bool(cel(linha, i_o))}

    # Conferencias: M=GLPI, N=IA. Validado = ambas preenchidas.
    conferencias = pl.ler_conferencias(sh, aba)

    candidatos = []
    for ln, d in info.items():
        c = conferencias.get(str(ln))
        if not c or c.get("ia") is None or c.get("glpi") is None:
            continue          # precisa de M e N preenchidas
        if d["o_preenchido"]:
            continue          # ja reclassificado (coluna O preenchida)
        candidatos.append(ln)
    candidatos.sort()
    total = len(candidatos)
    print(f"run_id={run_id} | elegiveis={len(elegiveis)} | validados_pendentes={total} | modelo={args.modelo}")
    if total == 0:
        print("0 chamados validados pendentes de reclassificacao.")
        return 0

    n_lote = total if args.max_turnos <= 0 else min(total, args.max_turnos * tam)
    sel = candidatos[:n_lote]
    sel_set = set(sel)

    # Treino: base historica MENOS o lote (evita prever na propria linha) + memoria validada.
    base_textos = [t for (ln, t, _) in elegiveis if ln not in sel_set]
    base_cats = [c for (ln, _, c) in elegiveis if ln not in sel_set]
    memoria_cfg = config.get("memoria_validada", {})
    memoria = mv.carregar_memoria_validada(sh, config["abas_experimento"]["validacao_humana"]) \
        if memoria_cfg.get("habilitada", True) else []
    base_textos, base_cats = mv.expandir_treino_com_memoria(
        base_textos, base_cats, memoria, peso=int(memoria_cfg.get("peso_treino", 3)))

    print(f"lote={len(sel)} | base_treino={len(base_textos)} | memoria_validada={len(memoria)} | treinando (robusto)...")
    predict_fn, tag = treinar_reclass(args.modelo, base_textos, base_cats, config=config)
    preds, confs = predict_fn([info[ln]["texto"] for ln in sel])

    registros = []
    for ln, pred, conf in zip(sel, preds, confs):
        d = info[ln]
        c = conferencias[str(ln)]
        v_ia, v_glpi = c.get("ia"), c.get("glpi")           # N, M
        if v_ia == "Correto":
            verdade = d["cat_G"]
        elif v_glpi == "Correto":
            verdade = d["cat_C"]
        else:
            verdade = None
        cat_o = str(pred)
        acertou = None if not verdade else (cat_o == verdade)
        registros.append({"linha": ln, "id": d["id"], "cat_C": d["cat_C"], "cat_G": d["cat_G"],
                          "conf_ia_N": v_ia, "conf_glpi_M": v_glpi, "verdade": verdade or "",
                          "cat_o": cat_o, "acertou": acertou, "conf_o": round(float(conf), 4)})

    com_verdade = [r for r in registros if r["acertou"] is not None]
    acertos = sum(1 for r in com_verdade if r["acertou"])
    print(f"reclassificados={len(registros)} | com_verdade={len(com_verdade)} | "
          f"acertos_robusto={acertos}/{len(com_verdade)} | executor=Reclass_{tag}")

    if not args.aplicar:
        print("modo=dry-run (nada gravado).")
        return 0

    # 1) Grava a reclassificacao na coluna O (Classificacao IA - 2), sem tocar em G/M/N.
    mapa_o = {r["linha"]: r["cat_o"] for r in registros}
    for tentativa in range(1, 4):
        try:
            pl.escrever_coluna_por_linha(ws, col_o, mapa_o)
            break
        except Exception as e:  # noqa: BLE001
            if tentativa >= 3:
                print(f"FALHA ao gravar coluna O: {type(e).__name__}: {e}", file=sys.stderr); return 1
            print(f"coluna O: falha transitoria ({type(e).__name__}); retry {tentativa}/3 em {10*tentativa}s",
                  file=sys.stderr)
            time.sleep(10 * tentativa)

    # 2) Auditoria por chamado em RECLASS_VALIDADOS.
    cab_a = ["run_id", "linha_planilha", "id_chamado", "categoria_C", "categoria_G",
             "conferencia_ia_N", "conferencia_glpi_M", "verdade_derivada",
             "categoria_reclass_O", "reclass_correto", "confianca_reclass", "modelo", "data"]
    linhas_a = [[run_id, r["linha"], r["id"], r["cat_C"], r["cat_G"], r["conf_ia_N"],
                 r["conf_glpi_M"], r["verdade"], r["cat_o"],
                 ("" if r["acertou"] is None else str(r["acertou"])), r["conf_o"],
                 f"Reclass_{tag}", gerado] for r in registros]
    for tentativa in range(1, 4):
        try:
            pl.append_aba(sh, ABA_AUDITORIA, cab_a, linhas_a)
            break
        except Exception as e:  # noqa: BLE001
            if tentativa >= 3:
                print(f"[aviso] coluna O gravada, mas auditoria falhou: {type(e).__name__}: {e}", file=sys.stderr)
                break
            time.sleep(10 * tentativa)

    print(f"OK: {len(registros)} reclassificados na coluna O | acertos_robusto={acertos}/{len(com_verdade)} | "
          f"restam {total - len(sel)} validados pendentes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
