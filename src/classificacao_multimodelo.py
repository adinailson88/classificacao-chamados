#!/usr/bin/env python3
"""Classificacao COMPLETA por modelo — materializa cada IA do zoo numa aba propria.

Ao contrario da Etapa 1 (um unico modelo de producao na aba base G:M), aqui CADA
modelo do `modelos_zoo` recebe o ciclo completo: classifica TODA a base, com sua
propria confianca, gravando numa aba dedicada `CLASSIF__<modelo>`.

ROBUSTEZ (out-of-fold): a IA que rotula a linha i NUNCA treinou na linha i. Assim a
confianca medida e honesta (essencial para o criterio dos >=95%). Duas situacoes,
resolvidas automaticamente:
- materializacao inicial (a base ainda nao foi classificada para este modelo):
  validacao cruzada K-fold sobre o lote — cada fold e previsto por um modelo
  treinado nos outros folds (+ base ja classificada + memoria validada);
- top-up incremental (chegaram poucos chamados novos): treina na base ja
  classificada e preve so os novos (que nao entraram no treino).

LOTE DINAMICO: processa o que estiver PENDENTE para o modelo (linhas ainda nao
gravadas em CLASSIF__<modelo>), mesmo que seja < lote ou 1 unico chamado. Nunca
espera "fechar" um lote.

Sem --aplicar = dry-run. Acesso via conta de servico (gspread). 100% local.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planilha as pl  # noqa: E402
import modelos_zoo as zoo  # noqa: E402
import memoria_validada as mv  # noqa: E402
import classificador_producao as cp  # noqa: E402
from tempo import agora_bahia  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
DADOS = RAIZ / "dados"


def cel(linha, idx) -> str:
    return str(linha[idx] or "").strip() if (idx is not None and idx < len(linha)) else ""


def carregar_config(caminho: Path) -> dict[str, Any]:
    with caminho.open("r", encoding="utf-8") as f:
        return json.load(f)


def nome_aba(template: str, modelo: str) -> str:
    return template.replace("{modelo}", modelo)


def carregar_elegiveis(ws, config) -> list[dict[str, Any]]:
    """Linhas com categoria historica (C) e texto — base do experimento."""
    valores = pl.ler_valores(ws, config["range_leitura"])
    cab = valores[0] if valores else []
    norm = lambda s: " ".join(str(s or "").split()).casefold()  # noqa: E731
    idx = {norm(n): i for i, n in enumerate(cab)}
    i_id, i_tit, i_cat = idx.get(norm("ID Chamado")), idx.get(norm("TÍTULO")), idx.get(norm("CATEGORIA COMPLETA"))
    i_dg, i_to, i_do = idx.get(norm("DESCRIÇÃO GLPI")), idx.get(norm("TÍTULO O.S.M.")), idx.get(norm("DESCRIÇÃO O.S.M."))
    elig = []
    for pos, linha in enumerate(valores[1:], start=2):
        cat = cel(linha, i_cat)
        texto = "\n".join(c for c in [cel(linha, i_tit), cel(linha, i_dg),
                                      cel(linha, i_to), cel(linha, i_do)] if c)
        if cat and texto:
            elig.append({"linha": pos, "id": cel(linha, i_id), "titulo": cel(linha, i_tit),
                         "categoria_original": cat, "texto": texto})
    return elig


def linhas_ja_classificadas(sh, aba: str) -> set[int]:
    """Le a coluna linha_planilha (B) de CLASSIF__<modelo>; vazio se a aba nao existe."""
    try:
        vals = sh.worksheet(aba).get_values("B:B", value_render_option="UNFORMATTED_VALUE")
    except Exception:  # noqa: BLE001
        return set()
    feitas = set()
    for r in vals[1:]:
        try:
            feitas.add(int(r[0]))
        except (IndexError, ValueError, TypeError):
            continue
    return feitas


def _prever_com_veto(m, textos, vetos):
    """Predicao escolhendo a melhor classe FORA do conjunto vetado de cada item.

    `vetos`: lista (alinhada a `textos`) de conjuntos de categorias que a
    conferencia humana ja marcou como ERRADAS para aquele chamado — a regra de
    memoria exige nao repeti-las. Sem vetos, cai no predict_score normal.
    A confianca apos o veto e a probabilidade RENORMALIZADA entre as classes
    permitidas: P(classe | nao esta entre as vetadas).
    """
    if not vetos or not any(vetos):
        preds, scores = m.predict_score(textos)
        return [str(p) for p in preds], [float(s) for s in scores]
    classes, prob = m.predict_dist(textos)
    classes = [str(c) for c in classes]
    preds, scores = [], []
    for i, veto in enumerate(vetos):
        p = np.asarray(prob[i], dtype=float).copy()
        if veto:
            mask = np.array([c in veto for c in classes])
            if not mask.all():  # se TODAS as classes fossem vetadas, ignora o veto
                p[mask] = 0.0
        tot = float(p.sum())
        if tot <= 0:
            preds.append(None)
            scores.append(0.0)
            continue
        p = p / tot
        j = int(p.argmax())
        preds.append(classes[j])
        scores.append(float(p[j]))
    return preds, scores


def prever_out_of_fold(nome, lote, base_textos, base_cats, k_folds, min_base, fracao_topup,
                       vetos=None):
    """Predicao honesta (sem vazamento) das linhas do `lote`.

    base_* = linhas ja classificadas (rotulo historico) + memoria validada, que
    entram SEMPRE no treino. Retorna (preds, scores) alinhados ao `lote`.

    - Top-up: se a base e grande e o lote e pequeno em relacao a ela, treina 1 vez
      na base e preve o lote (lote fora do treino -> out-of-fold).
    - Inicial/grande: K-fold sobre o lote (a base apenas reforca o treino de cada
      fold), garantindo que cada linha do lote seja prevista sem ter sido treinada.
    - `vetos` (opcional): lista alinhada ao lote com o conjunto de categorias que a
      conferencia humana marcou como erradas para cada chamado; a predicao escolhe
      a melhor classe fora do veto (regra: nao repetir erro ja conferido).
    """
    textos_lote = [e["texto"] for e in lote]
    cats_lote = [e["categoria_original"] for e in lote]
    n = len(lote)
    vetos = list(vetos) if vetos else [set()] * n

    base_n = len(base_textos)
    if base_n >= min_base and n <= max(50, int(fracao_topup * base_n)):
        m = zoo.criar_modelo(nome)
        m.fit(base_textos, base_cats)
        preds, scores = _prever_com_veto(m, textos_lote, vetos)
        return preds, scores, "topup"

    # K-fold OOF sobre o lote.
    from sklearn.model_selection import KFold
    kk = min(int(k_folds), n)
    if kk < 2:
        # 1 linha so: precisa de alguma base para treinar.
        if base_n == 0:
            return [None], [0.0], "sem_base"
        m = zoo.criar_modelo(nome)
        m.fit(base_textos, base_cats)
        preds, scores = _prever_com_veto(m, textos_lote, vetos)
        return preds, scores, "base_unica"

    preds = [None] * n
    scores = [0.0] * n
    kf = KFold(n_splits=kk, shuffle=True, random_state=42)
    for tr_idx, te_idx in kf.split(range(n)):
        x_tr = [textos_lote[i] for i in tr_idx] + list(base_textos)
        y_tr = [cats_lote[i] for i in tr_idx] + list(base_cats)
        m = zoo.criar_modelo(nome)
        m.fit(x_tr, y_tr)
        p, s = _prever_com_veto(m, [textos_lote[i] for i in te_idx], [vetos[i] for i in te_idx])
        for j, i in enumerate(te_idx):
            preds[i] = None if p[j] is None else str(p[j])
            scores[i] = float(s[j])
    return preds, scores, f"kfold_{kk}"


def gravar_classificacao(sh, aba, run_id, lote, gerado) -> int:
    cab = ["run_id", "linha_planilha", "id_chamado", "categoria_original", "categoria_ia",
           "confianca", "faixa", "executor", "acerto_historico", "etapa", "data"]
    linhas = [[run_id, e["linha"], e["id"], e["categoria_original"], e["categoria_ia"],
               e["confianca"], e["faixa"], e["executor"], str(e["acerto"]), 1, gerado] for e in lote]
    return pl.append_aba(sh, aba, cab, linhas, colunas_percentuais=[6])


def montar_turnos(modelo, run_id, lote, tam, gerado, prev_turnos, acum_proc, acum_true):
    turnos = []
    for k, ini in enumerate(range(0, len(lote), tam)):
        bloco = lote[ini:ini + tam]
        n = len(bloco)
        nt = sum(1 for e in bloco if e["acerto"])
        acum_proc += n
        acum_true += nt
        cfs = [e["confianca"] for e in bloco]
        turnos.append([
            modelo, run_id, prev_turnos + k + 1, bloco[0]["linha"], bloco[-1]["linha"], n, nt,
            round(nt / n, 4), round(acum_true / acum_proc, 4),
            round(float(np.mean(cfs)), 4), round(float(np.min(cfs)), 4), round(float(np.max(cfs)), 4),
            sum(1 for e in bloco if e["faixa"] == "abaixo_70"),
            sum(1 for e in bloco if e["faixa"] == "entre_70_95"),
            sum(1 for e in bloco if e["faixa"] == "acima_95"),
            gerado,
        ])
    return turnos, acum_proc, acum_true


def cumulativo_turnos(sh, aba, modelo) -> tuple[int, int, int]:
    """(turnos_existentes, soma_processados, soma_acertos) do modelo em MULTIMODELO_TURNOS."""
    try:
        vals = sh.worksheet(aba).get_values("A:I", value_render_option="UNFORMATTED_VALUE")
    except Exception:  # noqa: BLE001
        return 0, 0, 0
    t = proc = true = 0
    for r in vals[1:]:
        if len(r) < 7 or str(r[0]).strip() != modelo:
            continue
        try:
            proc += int(r[5]); true += int(r[6]); t += 1
        except (ValueError, TypeError):
            pass
    return t, proc, true


def classificar_modelo(sh, config, modelo, elegiveis, cap, base_extra, args) -> dict[str, Any]:
    mm = config["multimodelo"]
    run_id = config.get("run_id", "")
    gerado = agora_bahia()
    tam = int(mm.get("tamanho_turno", 15))
    aba_classif = nome_aba(mm["aba_classificacao"], modelo)

    feitas = linhas_ja_classificadas(sh, aba_classif)
    pendentes = [e for e in elegiveis if e["linha"] not in feitas]
    classificados = [e for e in elegiveis if e["linha"] in feitas]
    if not pendentes:
        print(f"[{modelo}] 0 pendentes (ja classificou {len(feitas)}).")
        return {"modelo": modelo, "processados": 0, "pendentes": 0, "feitos_total": len(feitas)}

    n_lote = len(pendentes) if cap <= 0 else min(len(pendentes), cap)
    lote = pendentes[:n_lote]

    # Base SEMPRE-no-treino: linhas ja classificadas (rotulo historico) + memoria validada.
    base_textos = [e["texto"] for e in classificados]
    base_cats = [e["categoria_original"] for e in classificados]
    base_textos += list(base_extra[0])
    base_cats += list(base_extra[1])

    print(f"[{modelo}] elegiveis={len(elegiveis)} | ja_feitos={len(feitas)} | "
          f"pendentes={len(pendentes)} | lote_agora={len(lote)} | base_treino_fixa={len(base_textos)}")

    preds, scores, metodo = prever_out_of_fold(
        modelo, lote, base_textos, base_cats,
        k_folds=int(mm.get("k_folds", 5)), min_base=int(mm.get("min_base_treino", 200)),
        fracao_topup=float(mm.get("fracao_topup", 0.25)))

    aproveitados = []
    for e, p, s in zip(lote, preds, scores):
        if p is None:
            continue
        conf = round(float(s), 4)
        e["categoria_ia"] = str(p)
        e["confianca"] = conf
        e["faixa"] = cp.faixa_confianca(conf)
        e["executor"] = modelo if conf >= cp.LIMIAR_ALTA else f"{modelo}_BAIXA_CONF"
        e["acerto"] = (e["categoria_ia"] == e["categoria_original"])
        aproveitados.append(e)

    if not aproveitados:
        print(f"[{modelo}] nada previsto (metodo={metodo}; base insuficiente).")
        return {"modelo": modelo, "processados": 0, "pendentes": len(pendentes), "feitos_total": len(feitas)}

    n_true = sum(1 for e in aproveitados if e["acerto"])
    concord = round(n_true / len(aproveitados), 4)
    print(f"[{modelo}] previstos={len(aproveitados)} | metodo={metodo} | "
          f"concordancia_lote={round(100*concord,2)}%")

    if not args.aplicar:
        return {"modelo": modelo, "processados": len(aproveitados), "concordancia_lote": concord,
                "metodo": metodo, "pendentes": len(pendentes) - len(aproveitados),
                "feitos_total": len(feitas), "dry_run": True}

    gravar_classificacao(sh, aba_classif, run_id, aproveitados, gerado)

    prev_t, acum_proc, acum_true = cumulativo_turnos(sh, mm["aba_turnos"], modelo)
    turnos, acum_proc, acum_true = montar_turnos(
        modelo, run_id, aproveitados, tam, gerado, prev_t, acum_proc, acum_true)
    cab_t = ["modelo", "run_id", "turno", "linha_inicial", "linha_final", "qtd", "qtd_acerto",
             "taxa_concordancia", "concordancia_acumulada", "confianca_media", "confianca_min",
             "confianca_max", "qtd_abaixo_70", "qtd_70_95", "qtd_acima_95", "data"]
    pl.append_aba(sh, mm["aba_turnos"], cab_t, turnos, colunas_percentuais=[8, 9, 10, 11, 12])

    return {"modelo": modelo, "processados": len(aproveitados), "concordancia_lote": concord,
            "metodo": metodo, "concordancia_acumulada": round(acum_true / acum_proc, 4),
            "feitos_total": len(feitas) + len(aproveitados),
            "pendentes": len(pendentes) - len(aproveitados)}


def atualizar_metricas(sh, config, resumos, gerado) -> None:
    mm = config["multimodelo"]
    cab = ["modelo", "feitos_total", "pendentes_restantes", "concordancia_acumulada",
           "concordancia_ultimo_lote", "metodo_ultimo", "processados_ultimo", "atualizado_em"]
    # Mescla com o que ja existe (modelos nao tocados neste run continuam na tabela).
    existentes = {}
    try:
        vals = sh.worksheet(mm["aba_metricas"]).get_values("A:H", value_render_option="UNFORMATTED_VALUE")
        for r in vals[1:]:
            if r and str(r[0]).strip():
                existentes[str(r[0]).strip()] = r
    except Exception:  # noqa: BLE001
        pass
    for s in resumos:
        existentes[s["modelo"]] = [
            s["modelo"], s.get("feitos_total", ""), s.get("pendentes", ""),
            s.get("concordancia_acumulada", ""), s.get("concordancia_lote", ""),
            s.get("metodo", ""), s.get("processados", 0), gerado]
    linhas = [existentes[m] for m in sorted(existentes)]
    pl.escrever_aba(sh, mm["aba_metricas"], cab, linhas, colunas_percentuais=[4, 5])


def resolver_modelos(config, escolha: str) -> list[str]:
    mm = config["multimodelo"]
    leves = mm["modelos_leves"]
    pesados = mm.get("modelos_pesados", [])
    e = (escolha or "leves").strip().lower()
    if e in ("leves", "todos_leves"):
        return list(leves)
    if e == "todos":
        return list(leves) + list(pesados)
    if e == "pesados":
        return list(pesados)
    return [m.strip() for m in e.split(",") if m.strip()]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Classificacao completa por modelo (out-of-fold).")
    p.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    p.add_argument("--credenciais", default=None)
    p.add_argument("--modelos", default="leves",
                   help="'leves' (6), 'todos' (7), 'pesados' (lstm) ou lista: 'naive_bayes,sgd'.")
    p.add_argument("--max-turnos", type=int, default=0,
                   help="Cap de turnos de 15 por execucao e por modelo (0 = todos os pendentes).")
    p.add_argument("--aplicar", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    config = carregar_config(args.config)
    if not config.get("multimodelo", {}).get("habilitado", False):
        print("multimodelo desabilitado no config."); return 0
    mm = config["multimodelo"]
    tam = int(mm.get("tamanho_turno", 15))
    cap = 0 if args.max_turnos <= 0 else args.max_turnos * tam
    modelos = resolver_modelos(config, args.modelos)
    gerado = agora_bahia()

    try:
        sh = pl.abrir_planilha(pl.id_planilha(config), args.credenciais)
        ws = sh.worksheet(config["aba_principal"])
        elegiveis = carregar_elegiveis(ws, config)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr); return 2
    except Exception as e:  # noqa: BLE001
        print(f"Falha ao acessar a planilha: {type(e).__name__}: {e}", file=sys.stderr); return 1

    if len(elegiveis) < 2:
        print("Informacao insuficiente para verificar."); return 1

    # Memoria validada (entra sempre no treino, com peso).
    memoria_cfg = config.get("memoria_validada", {})
    memoria = []
    if memoria_cfg.get("habilitada", True):
        memoria = mv.carregar_memoria_validada(sh, config["abas_experimento"]["validacao_humana"])
    peso_mem = int(memoria_cfg.get("peso_treino", 3))
    mem_textos, mem_cats = mv.expandir_treino_com_memoria([], [], memoria, peso=peso_mem)
    print(f"modelos={modelos} | elegiveis={len(elegiveis)} | cap_por_run={cap or 'todos'} | "
          f"memoria_validada={len(memoria)} (peso {peso_mem})")

    resumos = []
    for modelo in modelos:
        try:
            r = classificar_modelo(sh, config, modelo, elegiveis, cap, (mem_textos, mem_cats), args)
        except Exception as e:  # noqa: BLE001
            print(f"[{modelo}] FALHOU: {type(e).__name__}: {e}", file=sys.stderr)
            continue
        resumos.append(r)

    if args.aplicar and resumos:
        atualizar_metricas(sh, config, resumos, gerado)

    DADOS.mkdir(parents=True, exist_ok=True)
    (DADOS / "multimodelo_ultimo.json").write_text(
        json.dumps({"gerado_em": gerado, "modelos": resumos}, ensure_ascii=False, indent=2),
        encoding="utf-8")

    total_proc = sum(r.get("processados", 0) for r in resumos)
    total_pend = sum(r.get("pendentes", 0) for r in resumos)
    print(f"OK: processados={total_proc} | pendentes_restantes={total_pend} | "
          f"modelos={len(resumos)}{' (dry-run)' if not args.aplicar else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
