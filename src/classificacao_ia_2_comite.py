#!/usr/bin/env python3
"""Comitê multimodelo para sugerir e aplicar Classificação IA - 2.

Este script implementa a etapa robusta da coluna O:
- lê candidatos priorizados pela aba VALIDACAO_NAO_SUPERVISIONADA, quando existir;
- lê votos das abas CLASSIF__<modelo>;
- opcionalmente roda MiniLM robusto local para os candidatos;
- calcula voto ponderado por desempenho histórico e confiança;
- grava COMITE_CLASSIFICACAO_2 e CLASSIFICACAO_2_DRYRUN;
- opcionalmente grava a coluna O (Classificacao IA - 2), sem tocar em G/M/N/P.

Sem --aplicar = dry-run. Para gravar O, é necessário usar simultaneamente:
--aplicar --gravar-coluna-o.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planilha as pl  # noqa: E402
from tempo import agora_bahia  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"

ABA_CANDIDATOS = "CANDIDATOS_CLASSIFICACAO_2"
ABA_COMITE = "COMITE_CLASSIFICACAO_2"
ABA_DRYRUN = "CLASSIFICACAO_2_DRYRUN"
ABA_AUDITORIA = "AUDITORIA_CLASSIFICACAO_2"
ABA_CONTROLE = "CONTROLE_CLASSIFICACAO_2"
ABA_VALIDACAO_NS = "VALIDACAO_NAO_SUPERVISIONADA"


def norm(s: Any) -> str:
    t = unicodedata.normalize("NFKD", str(s or ""))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return " ".join(t.split()).casefold()


def cel(linha: list[Any], idx: int | None) -> str:
    return str(linha[idx] or "").strip() if idx is not None and idx < len(linha) else ""


def parse_float(v: Any, default: float = 0.0) -> float:
    try:
        f = float(str(v).replace("%", "").replace(",", ".").strip())
        return f / 100.0 if f > 1 else f
    except (ValueError, TypeError):
        return default


def carregar_config(caminho: Path) -> dict[str, Any]:
    with caminho.open("r", encoding="utf-8") as f:
        return json.load(f)


def carregar_chamados(ws, range_a1: str = "A:P") -> dict[int, dict[str, Any]]:
    valores = pl.ler_valores(ws, range_a1)
    cab = valores[0] if valores else []
    idx = {norm(n): i for i, n in enumerate(cab)}
    campos_texto = ["TITULO", "DESCRICAO GLPI", "TITULO O.S.M.", "DESCRICAO O.S.M."]
    out = {}
    for pos, linha in enumerate(valores[1:], start=2):
        cat = cel(linha, idx.get(norm("CATEGORIA COMPLETA")))
        partes = [cel(linha, idx.get(norm(c))) for c in campos_texto]
        texto = "\n".join(p for p in partes if p)
        if not cat or not texto:
            continue
        out[pos] = {
            "linha": pos,
            "id": cel(linha, idx.get(norm("ID Chamado"))),
            "categoria_c": cat,
            "categoria_g": cel(linha, idx.get(norm("Classificacao IA"))),
            "confianca_g": parse_float(cel(linha, idx.get(norm("Avaliacao (%)")))),
            "categoria_o": cel(linha, idx.get(norm("Classificacao IA - 2"))),
            "texto": texto,
        }
    return out


def carregar_prioridades_ns(sh) -> dict[int, dict[str, Any]]:
    try:
        vals = sh.worksheet(ABA_VALIDACAO_NS).get_values("A:Q", value_render_option="UNFORMATTED_VALUE")
    except Exception:  # noqa: BLE001
        return {}
    if not vals:
        return {}
    idx = {norm(n): i for i, n in enumerate(vals[0])}
    out = {}
    for r in vals[1:]:
        try:
            linha = int(cel(r, idx.get(norm("linha"))))
        except (ValueError, TypeError):
            continue
        out[linha] = {
            "prioridade": cel(r, idx.get(norm("prioridade_revisao"))) or "Baixa",
            "motivo": cel(r, idx.get(norm("motivo_prioridade"))),
            "categoria_semantica": cel(r, idx.get(norm("categoria_semantica_mais_proxima"))),
            "margem": parse_float(cel(r, idx.get(norm("margem_semantica")))),
            "outlier": cel(r, idx.get(norm("outlier_semantico"))),
        }
    return out


def carregar_classificacoes_modelos(sh, config: dict[str, Any], modelos: list[str]) -> tuple[dict[int, list[dict[str, Any]]], dict[str, float]]:
    mm = config.get("multimodelo", {})
    template = mm.get("aba_classificacao", "CLASSIF__{modelo}")
    votos: dict[int, list[dict[str, Any]]] = defaultdict(list)
    pesos: dict[str, float] = {}

    for modelo in modelos:
        aba = template.replace("{modelo}", modelo)
        try:
            vals = sh.worksheet(aba).get_values("A:K", value_render_option="UNFORMATTED_VALUE")
        except Exception:  # noqa: BLE001
            continue
        if not vals:
            continue
        idx = {norm(n): i for i, n in enumerate(vals[0])}
        i_linha = idx.get(norm("linha_planilha"))
        i_pred = idx.get(norm("categoria_ia"))
        i_conf = idx.get(norm("confianca"))
        i_acc = idx.get(norm("acerto_historico"))
        acertos = total = 0
        for r in vals[1:]:
            try:
                linha = int(cel(r, i_linha))
            except (ValueError, TypeError):
                continue
            pred = cel(r, i_pred)
            if not pred:
                continue
            conf = parse_float(cel(r, i_conf), 0.0)
            votos[linha].append({"modelo": modelo, "pred": pred, "conf": conf})
            acc = cel(r, i_acc).casefold()
            if acc in {"true", "verdadeiro", "sim", "1"}:
                acertos += 1
                total += 1
            elif acc in {"false", "falso", "nao", "não", "0"}:
                total += 1
        pesos[modelo] = (acertos / total) if total else 0.5
    return votos, pesos


def selecionar_candidatos(
    chamados: dict[int, dict[str, Any]],
    prioridades: dict[int, dict[str, Any]],
    conferencias: dict[str, dict[str, str | None]],
    incluir_sem_mn: bool,
    limite: int,
) -> list[int]:
    candidatos = []
    for linha, d in chamados.items():
        if d.get("categoria_o"):
            continue
        conf = conferencias.get(str(linha), {})
        tem_mn = conf.get("glpi") is not None and conf.get("ia") is not None
        pr = prioridades.get(linha, {}).get("prioridade", "")
        if tem_mn or incluir_sem_mn or pr in {"Alta", "Media"}:
            candidatos.append(linha)

    def chave(ln: int):
        pr = prioridades.get(ln, {}).get("prioridade", "Baixa")
        return ({"Alta": 0, "Media": 1, "Baixa": 2}.get(pr, 3), ln)

    candidatos.sort(key=chave)
    return candidatos[:limite] if limite > 0 else candidatos


def treinar_minilm(chamados: dict[int, dict[str, Any]], candidatos: list[int], config: dict[str, Any]):
    import classificador_robusto as cr
    cand = set(candidatos)
    textos = [d["texto"] for ln, d in chamados.items() if ln not in cand]
    cats = [d["categoria_c"] for ln, d in chamados.items() if ln not in cand]
    if len(textos) < 2 or len(set(cats)) < 2:
        return None, "base_insuficiente"
    lstm_config = config.get("modelo_ia", {}).get("lstm", {})
    clf, tag = cr.treinar(textos, cats, lstm_config=lstm_config)
    return clf, tag


def entropia(cont: Counter) -> float:
    total = sum(cont.values())
    if total <= 0:
        return 0.0
    h = 0.0
    for n in cont.values():
        p = n / total
        h -= p * math.log(p, 2)
    return h


def decidir(votos: list[dict[str, Any]], pesos: dict[str, float], prioridade_ns: dict[str, Any]) -> dict[str, Any]:
    if not votos:
        return {
            "categoria": "",
            "confianca": 0.0,
            "qtd_consenso": 0,
            "n_categorias": 0,
            "entropia": 0.0,
            "risco": "alto",
            "aplicar": "NAO",
            "justificativa": "sem votos de modelos",
        }

    score = defaultdict(float)
    cont = Counter()
    confs = defaultdict(list)
    for v in votos:
        pred = v["pred"]
        modelo = v["modelo"]
        conf = max(0.01, min(1.0, float(v.get("conf") or 0.0)))
        w = max(0.1, pesos.get(modelo, 0.5))
        if modelo in {"minilm_robusto", "robusto"}:
            w *= 1.05
        if modelo in {"transformer_ft", "bertimbau"}:
            w *= 1.10
        score[pred] += w * conf
        cont[pred] += 1
        confs[pred].append(conf)

    categoria = max(score.items(), key=lambda kv: kv[1])[0]
    qtd = cont[categoria]
    ncat = len(cont)
    h = entropia(cont)
    conf_final = float(np.mean(confs[categoria])) if confs[categoria] else 0.0

    risco = "baixo"
    motivos = []
    if qtd < 5:
        risco = "medio"
        motivos.append("consenso inferior a 5 modelos")
    if ncat >= 4 or h > 1.5:
        risco = "alto"
        motivos.append("alta divergência entre modelos")
    if prioridade_ns.get("prioridade") == "Alta":
        motivos.append("prioridade alta na validação não supervisionada")
    if conf_final < 0.70:
        risco = "alto"
        motivos.append("confiança final baixa")

    aplicar = "SIM" if risco in {"baixo", "medio"} and qtd >= 5 and conf_final >= 0.70 else "NAO"
    return {
        "categoria": categoria,
        "confianca": round(conf_final, 4),
        "qtd_consenso": qtd,
        "n_categorias": ncat,
        "entropia": round(h, 4),
        "risco": risco,
        "aplicar": aplicar,
        "justificativa": "; ".join(motivos or ["consenso suficiente"]),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Comitê robusto para Classificação IA - 2.")
    p.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    p.add_argument("--credenciais", default=None)
    p.add_argument("--limite", type=int, default=200)
    p.add_argument("--incluir-sem-mn", action="store_true", help="Permite sugerir O mesmo sem M/N completas.")
    p.add_argument("--usar-minilm", action="store_true", help="Roda sentence-transformers MiniLM como voto adicional.")
    p.add_argument("--aplicar", action="store_true", help="Grava abas de auditoria/dry-run.")
    p.add_argument("--gravar-coluna-o", action="store_true", help="Com --aplicar, grava sugestões seguras na coluna O.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    config = carregar_config(args.config)
    gerado = agora_bahia()
    modelos = list(config.get("multimodelo", {}).get("modelos_leves", [])) + list(config.get("multimodelo", {}).get("modelos_pesados", []))

    try:
        sh = pl.abrir_planilha(pl.id_planilha(config), args.credenciais)
        ws = sh.worksheet(config["aba_principal"])
        chamados = carregar_chamados(ws, "A:P")
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001
        print(f"Falha ao acessar planilha: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    prioridades = carregar_prioridades_ns(sh)
    conferencias = pl.ler_conferencias(sh, config["aba_principal"])
    candidatos = selecionar_candidatos(chamados, prioridades, conferencias, args.incluir_sem_mn, args.limite)

    votos_modelos, pesos = carregar_classificacoes_modelos(sh, config, modelos)

    minilm = None
    minilm_tag = ""
    if args.usar_minilm and candidatos:
        minilm, minilm_tag = treinar_minilm(chamados, candidatos, config)

    minilm_preds = {}
    if minilm is not None:
        textos = [chamados[ln]["texto"] for ln in candidatos]
        preds, confs = minilm.predict_com_conf(textos)
        for ln, pred, conf in zip(candidatos, preds, confs):
            minilm_preds[ln] = {"modelo": "minilm_robusto", "pred": str(pred), "conf": float(conf)}
        pesos["minilm_robusto"] = 0.80

    linhas_comite = []
    linhas_dry = []
    linhas_cand = []
    mapa_o = {}
    for ln in candidatos:
        d = chamados[ln]
        votos = list(votos_modelos.get(ln, []))
        if ln in minilm_preds:
            votos.append(minilm_preds[ln])

        pr = prioridades.get(ln, {"prioridade": "Baixa", "motivo": "sem validação não supervisionada"})
        dec = decidir(votos, pesos, pr)
        conf = conferencias.get(str(ln), {})
        mn_completo = conf.get("glpi") is not None and conf.get("ia") is not None

        resultado_estimado = ""
        ganho_estimado = ""
        if conf.get("ia") == "Correto":
            verdade = d["categoria_g"]
        elif conf.get("glpi") == "Correto":
            verdade = d["categoria_c"]
        else:
            verdade = ""
        if verdade and dec["categoria"]:
            acertou_o = dec["categoria"] == verdade
            acertou_g = d["categoria_g"] == verdade
            resultado_estimado = "corrige" if acertou_o and not acertou_g else "prejudica" if (not acertou_o and acertou_g) else "mantem"
            ganho_estimado = 1 if acertou_o and not acertou_g else -1 if (not acertou_o and acertou_g) else 0

        aplicar_linha = dec["aplicar"] == "SIM" and mn_completo
        if aplicar_linha and dec["categoria"]:
            mapa_o[ln] = dec["categoria"]

        linhas_cand.append([
            ln, d["id"], d["categoria_c"], d["categoria_g"], conf.get("glpi") or "",
            conf.get("ia") or "", d["confianca_g"], pr.get("motivo", ""), pr.get("prioridade", "Baixa"), gerado,
        ])
        linhas_comite.append([
            ln, d["id"], d["categoria_c"], d["categoria_g"],
            " | ".join(f"{v['modelo']}={v['pred']}({round(float(v.get('conf') or 0), 4)})" for v in votos),
            dec["categoria"], dec["qtd_consenso"], dec["n_categorias"], dec["entropia"],
            dec["confianca"], dec["risco"], dec["aplicar"], "MiniLM" if ln in minilm_preds else "Multimodelo",
            pr.get("prioridade", "Baixa"), pr.get("motivo", ""), dec["justificativa"], gerado,
        ])
        linhas_dry.append([
            ln, d["id"], d["categoria_c"], d["categoria_g"], dec["categoria"],
            conf.get("glpi") or "", conf.get("ia") or "", resultado_estimado, ganho_estimado,
            dec["risco"], "SIM" if aplicar_linha else "NAO", dec["justificativa"], gerado,
        ])

    print(json.dumps({
        "gerado_em": gerado,
        "candidatos": len(candidatos),
        "usar_minilm": bool(args.usar_minilm),
        "minilm_tag": minilm_tag,
        "sugestoes_seguras_para_o": len(mapa_o),
        "modo": "aplicar" if args.aplicar else "dry-run",
        "gravar_coluna_o": bool(args.gravar_coluna_o),
    }, ensure_ascii=False, indent=2))

    if not args.aplicar:
        print("modo=dry-run (nada gravado na planilha).")
        return 0

    pl.escrever_aba(sh, ABA_CANDIDATOS, [
        "linha", "id_chamado", "categoria_historica_C", "classificacao_ia_G",
        "conferencia_glpi_M", "conferencia_ia_N", "confianca_G",
        "motivo_candidatura", "prioridade_revalidacao", "data_execucao",
    ], linhas_cand, colunas_percentuais=[7])
    pl.escrever_aba(sh, ABA_COMITE, [
        "linha", "id_chamado", "categoria_C", "categoria_G", "votos_modelos",
        "categoria_sugerida_O", "qtd_votos_categoria_sugerida", "n_categorias_sugeridas",
        "entropia_votos", "confianca_final", "risco", "aplicar_sugerido",
        "modelo_decisor", "prioridade_ns", "motivo_ns", "justificativa", "data_execucao",
    ], linhas_comite, colunas_percentuais=[10])
    pl.escrever_aba(sh, ABA_DRYRUN, [
        "linha", "id_chamado", "categoria_C", "categoria_G", "categoria_O_sugerida",
        "conferencia_M", "conferencia_N", "resultado_estimado", "ganho_estimado",
        "risco", "aplicar", "motivo", "data_execucao",
    ], linhas_dry)

    gravou_o = 0
    if args.gravar_coluna_o and mapa_o:
        col_o = pl.indice_coluna_por_cabecalho(ws, "Classificacao IA - 2", 15)
        gravou_o = pl.escrever_coluna_por_linha(ws, col_o, mapa_o)
        pl.append_aba(sh, ABA_AUDITORIA, [
            "data_execucao", "linha", "id_chamado", "categoria_C", "categoria_G",
            "categoria_O_gravada", "modelo_decisor", "observacao",
        ], [[gerado, ln, chamados[ln]["id"], chamados[ln]["categoria_c"], chamados[ln]["categoria_g"],
             cat, "comite_multimodelo", "gravado por classificacao_ia_2_comite.py"] for ln, cat in mapa_o.items()])

    pl.append_aba(
        sh,
        ABA_CONTROLE,
        ["data_execucao", "etapa", "status", "qtd_candidatos", "qtd_processados", "modelo_usado", "aplicou_na_coluna_O", "observacao_tecnica"],
        [[gerado, "2-comite-classificacao-ia-2", "OK", len(candidatos), len(linhas_comite),
          "multimodelo+minilm" if args.usar_minilm else "multimodelo", "SIM" if gravou_o else "NAO",
          f"gravou_o={gravou_o}; incluir_sem_mn={args.incluir_sem_mn}"]],
    )
    print(f"OK: comitê gravado; coluna O gravada em {gravou_o} linhas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
