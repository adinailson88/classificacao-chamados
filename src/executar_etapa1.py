#!/usr/bin/env python3
"""Etapa 1 do roteiro — classificação inicial PROGRESSIVA (turno a turno).

Cada execução processa só os chamados PENDENTES (coluna G vazia), em turnos de
15, até o limite --max-turnos por execução. Isso permite observar a evolução ao
longo do tempo (o workflow roda de tempos em tempos e a base vai sendo
classificada gradualmente). Segue o roteiro (etapas 3,4,6-16):

- classifica com LSTM primário + RF fallback (faixas: >=95% LSTM / <95% LSTM_BAIXA_CONF);
- grava G:J + fórmula de conferência K (=SE(G="";"";G=C), IA x original);
- APPEND nas abas LOG_TURNOS_CLASSIFICACAO, LOG_LINHA_A_LINHA, SNAPSHOT_ETAPA_1;
- atualiza EXPERIMENTO_CONFIG e METRICAS_EXPERIMENTO;
- todas as taxas/confianças são gravadas como FRAÇÃO 0-1 e formatadas como %.

Sem --aplicar = dry-run. Modelos no escopo: producao (LSTM+RF) ou baseline (TF-IDF).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planilha as pl  # noqa: E402
import classificador_producao as cp  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
DADOS = RAIZ / "dados"
FUSO_BAHIA = timezone(timedelta(hours=-3))

COL_G, COL_J = 7, 10  # Classificação IA ... Criticidade


def agora_bahia() -> str:
    return datetime.now(FUSO_BAHIA).strftime("%Y-%m-%dT%H:%M:%S-03:00")


def git_info(args_):
    def run(cmd, env):
        v = os.getenv(env)
        if v:
            return v
        try:
            return subprocess.check_output(cmd, cwd=str(RAIZ), text=True).strip()
        except Exception:  # noqa: BLE001
            return ""
    return (run(["git", "rev-parse", "--abbrev-ref", "HEAD"], "GITHUB_REF_NAME"),
            run(["git", "rev-parse", "--short", "HEAD"], "GITHUB_SHA"))


def carregar_config(caminho: Path) -> dict[str, Any]:
    with caminho.open("r", encoding="utf-8") as f:
        return json.load(f)


def gravar_json(caminho: Path, dados: Any) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
        f.write("\n")


def cel(linha, idx) -> str:
    return str(linha[idx] or "").strip() if (idx is not None and idx < len(linha)) else ""


def treinar_e_prever(modelo, textos_treino, cats_treino, textos_alvo):
    if modelo == "producao":
        clf, eh_lstm = cp.treinar_classificador(textos_treino, cats_treino)
        preds, confs = cp.predizer(clf, eh_lstm, textos_alvo)
        return preds, confs, eh_lstm
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    clf = Pipeline([
        ("tfidf", TfidfVectorizer(strip_accents="unicode", lowercase=True,
                                  ngram_range=(1, 2), min_df=1, max_features=30000)),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced", solver="lbfgs")),
    ])
    clf.fit(textos_treino, cats_treino)
    probs = clf.predict_proba(textos_alvo)
    idx = probs.argmax(axis=1)
    return clf.classes_[idx], probs[np.arange(len(idx)), idx], False


def ler_cumulativo_turnos(sh, nome) -> tuple[int, int, int]:
    """Retorna (turnos_existentes, soma_processados, soma_true) do LOG_TURNOS."""
    try:
        ws = sh.worksheet(nome)
        vals = ws.get_all_values()
    except Exception:  # noqa: BLE001
        return 0, 0, 0
    linhas = vals[1:] if len(vals) > 1 else []
    soma_proc = soma_true = 0
    for r in linhas:
        try:
            soma_proc += int(r[4]); soma_true += int(r[5])
        except (IndexError, ValueError):
            pass
    return len(linhas), soma_proc, soma_true


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Etapa 1 progressiva (turnos de 15).")
    p.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    p.add_argument("--credenciais", default=None)
    p.add_argument("--modelo", choices=["producao", "baseline"], default="producao")
    p.add_argument("--tamanho-turno", type=int, default=15)
    p.add_argument("--max-turnos", type=int, default=40, help="Turnos por execução (0=todos).")
    p.add_argument("--aplicar", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    config = carregar_config(args.config)
    aba = config["aba_principal"]
    abas = config["abas_experimento"]
    lim = config.get("classificacao", {})
    lim_baixa = float(lim.get("limiar_confianca_baixa", 0.7))
    lim_alta = float(lim.get("limiar_alta_confianca", 0.95))
    run_id = config.get("run_id", "")
    gerado = agora_bahia()
    tam = args.tamanho_turno

    try:
        sh = pl.abrir_planilha(config["spreadsheet_id"], args.credenciais)
        ws = sh.worksheet(aba)
        valores = pl.ler_valores(ws, config["range_leitura"])
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr); return 2
    except Exception as e:  # noqa: BLE001
        print(f"Falha ao acessar a planilha: {type(e).__name__}: {e}", file=sys.stderr); return 1

    cab = valores[0] if valores else []
    norm = lambda s: " ".join(str(s or "").split()).casefold()  # noqa: E731
    idx = {norm(n): i for i, n in enumerate(cab)}
    i_id, i_tit, i_cat = idx.get(norm("ID Chamado")), idx.get(norm("TÍTULO")), idx.get(norm("CATEGORIA COMPLETA"))
    i_dg, i_to, i_do = idx.get(norm("DESCRIÇÃO GLPI")), idx.get(norm("TÍTULO O.S.M.")), idx.get(norm("DESCRIÇÃO O.S.M."))
    i_cls, i_conf = idx.get(norm("Classificação IA")), idx.get(norm("CONFERÊNCIA"))

    elegiveis, pendentes = [], []
    for pos, linha in enumerate(valores[1:], start=2):
        cat = cel(linha, i_cat)
        texto = "\n".join(c for c in [cel(linha, i_tit), cel(linha, i_dg),
                                      cel(linha, i_to), cel(linha, i_do)] if c)
        if not (cat and texto):
            continue
        reg = {"linha": pos, "id": cel(linha, i_id), "titulo": cel(linha, i_tit),
               "categoria_original": cat, "texto": texto,
               "conferido": cel(linha, i_conf).upper() in {"TRUE", "VERDADEIRO", "SIM"}}
        elegiveis.append(reg)
        if not cel(linha, i_cls) and not reg["conferido"]:
            pendentes.append(reg)

    total = len(valores) - 1
    print(f"run_id={run_id} | total={total} | elegiveis={len(elegiveis)} | pendentes={len(pendentes)} | modelo={args.modelo}")

    if not pendentes:
        print("Etapa 1 concluída (0 pendentes).")
        return 0

    if len(elegiveis) < 2:
        print("Informação insuficiente para verificar."); return 1

    # Lote desta execução
    n_lote = len(pendentes) if args.max_turnos <= 0 else min(len(pendentes), args.max_turnos * tam)
    lote = pendentes[:n_lote]

    # Treina na base rotulada (todos elegíveis) e prediz só o lote
    print("treinando modelo...")
    preds, confs, eh_lstm = treinar_e_prever(
        args.modelo, [e["texto"] for e in elegiveis], [e["categoria_original"] for e in elegiveis],
        [e["texto"] for e in lote])
    nome_modelo = ("LSTM_Bidirecional" if eh_lstm else
                   ("RandomForest_Fallback" if args.modelo == "producao" else "Baseline_TFIDF_LogReg"))

    for e, p, c in zip(lote, preds, confs):
        conf = round(float(c), 4)
        e["categoria_ia"] = str(p)
        e["confianca"] = conf
        e["executor"] = cp.nome_executor(conf, eh_lstm)
        e["faixa"] = cp.faixa_confianca(conf)
        e["criticidade"] = cp.estimar_criticidade(e["texto"])
        e["conf_ia"] = (e["categoria_ia"] == e["categoria_original"])

    prev_turnos, acum_proc, acum_true = (0, 0, 0)
    if args.aplicar:
        prev_turnos, acum_proc, acum_true = ler_cumulativo_turnos(sh, abas["log_turnos_classificacao"])

    # Monta turnos (fração 0-1 nas taxas)
    turnos = []
    for k, ini in enumerate(range(0, len(lote), tam)):
        bloco = lote[ini:ini + tam]
        n = len(bloco)
        nt = sum(1 for e in bloco if e["conf_ia"])
        acum_proc += n; acum_true += nt
        cfs = [e["confianca"] for e in bloco]
        turnos.append([
            run_id, prev_turnos + k + 1, bloco[0]["linha"], bloco[-1]["linha"], n, nt, n - nt,
            round(nt / n, 4), round(acum_true / acum_proc, 4),
            round(float(np.mean(cfs)), 4), round(float(np.min(cfs)), 4), round(float(np.max(cfs)), 4),
            sum(1 for e in bloco if e["faixa"] == "abaixo_70"),
            sum(1 for e in bloco if e["faixa"] == "entre_70_95"),
            sum(1 for e in bloco if e["faixa"] == "acima_95"),
            "LSTM" if eh_lstm else "RF_Fallback", gerado,
        ])

    n_true_lote = sum(1 for e in lote if e["conf_ia"])
    print(f"lote={len(lote)} | turnos_neste_run={len(turnos)} | "
          f"concordancia_lote={round(100.0*n_true_lote/len(lote),2)}% | "
          f"concordancia_acumulada={round(100.0*acum_true/acum_proc,2)}%")

    gravar_json(DADOS / "etapa1_ultimo_lote.json",
                {"run_id": run_id, "gerado_em": gerado, "modelo": nome_modelo,
                 "lote": len(lote), "concordancia_acumulada": round(acum_true / acum_proc, 4)})

    if not args.aplicar:
        print("modo=dry-run (nada gravado na planilha)")
        return 0

    # G:J em lote (% em H)
    linhas_gj = [{"linha": e["linha"],
                  "valores": [e["categoria_ia"], e["confianca"], e["executor"], e["criticidade"]]}
                 for e in lote]
    pl.exportar_lote_gj(ws, linhas_gj, col_inicio=COL_G, col_fim=COL_J)

    # Fórmula de conferência K (uma vez)
    try:
        if not ws.acell("K2").value:
            formulas = [[f'=SE(G{r}="";"";G{r}=C{r})'] for r in range(2, total + 2)]
            ws.update(range_name=f"K2:K{total + 1}", values=formulas, value_input_option="USER_ENTERED")
            print("fórmula de conferência K aplicada.")
    except Exception as e:  # noqa: BLE001
        print(f"aviso: não consegui aplicar a fórmula K ({e})", file=sys.stderr)

    # APPEND LOG_TURNOS (taxas col 8,9 e confianças 10,11,12 como %)
    cab_t = ["run_id", "turno", "linha_inicial", "linha_final", "qtd_processados", "qtd_true",
             "qtd_false", "taxa_concordancia", "concordancia_acumulada", "confianca_media",
             "confianca_min", "confianca_max", "qtd_abaixo_70", "qtd_70_95", "qtd_acima_95",
             "executor", "data_hora"]
    pl.append_aba(sh, abas["log_turnos_classificacao"], cab_t, turnos,
                  colunas_percentuais=[8, 9, 10, 11, 12])

    # APPEND LOG_LINHA_A_LINHA (confianca col 11 como %)
    cab_l = ["run_id", "etapa", "turno", "linha_planilha", "id_chamado", "titulo", "data_abertura",
             "categoria_original", "categoria_ia", "conferencia", "confianca", "executor",
             "criticidade", "data_hora"]
    linhas_l = []
    for k, ini in enumerate(range(0, len(lote), tam)):
        for e in lote[ini:ini + tam]:
            linhas_l.append([run_id, 1, prev_turnos + k + 1, e["linha"], e["id"], e["titulo"][:200],
                             "", e["categoria_original"], e["categoria_ia"], str(e["conf_ia"]),
                             e["confianca"], e["executor"], e["criticidade"], gerado])
    pl.append_aba(sh, abas["log_linha_a_linha"], cab_l, linhas_l, colunas_percentuais=[11])

    # APPEND SNAPSHOT_ETAPA_1 (confianca col 6 como %)
    cab_s = ["run_id", "linha_planilha", "id_chamado", "categoria_original", "categoria_ia_etapa_1",
             "confianca_etapa_1", "executor_etapa_1", "criticidade_etapa_1", "conferencia_etapa_1", "data_snapshot"]
    linhas_s = [[run_id, e["linha"], e["id"], e["categoria_original"], e["categoria_ia"],
                 e["confianca"], e["executor"], e["criticidade"], str(e["conf_ia"]), gerado] for e in lote]
    pl.append_aba(sh, abas["snapshot_etapa_1"], cab_s, linhas_s, colunas_percentuais=[6])

    # EXPERIMENTO_CONFIG (uma vez)
    try:
        ws_cfg = sh.worksheet(abas["config"])
        cfg_vazia = not ws_cfg.acell("A1").value
    except Exception:  # noqa: BLE001
        cfg_vazia = True
    if cfg_vazia:
        branch, commit = git_info(args)
        pl.escrever_aba(sh, abas["config"], ["campo", "valor"], [
            ["run_id", run_id], ["data_inicio", gerado], ["spreadsheet_id", config["spreadsheet_id"]],
            ["aba_principal", aba], ["total_chamados", total], ["total_elegiveis", len(elegiveis)],
            ["tamanho_turno", tam], ["limiar_confianca_baixa", lim_baixa],
            ["limiar_alta_confianca", lim_alta], ["modelo", nome_modelo], ["branch", branch],
            ["commit", commit], ["observacoes", "Etapa 1 progressiva; concordancia = IA x original (col C)."],
            ["responsavel", "classificacao-bot (conta de servico)"]])

    # METRICAS_EXPERIMENTO (acumulada global + faixa/executor do último lote)
    met = [["concordancia_acumulada_global", round(acum_true / acum_proc, 4)],
           ["processados_acumulado", acum_proc],
           ["pendentes_restantes", len(pendentes) - len(lote)],
           ["modelo", nome_modelo], ["atualizado_em", gerado]]
    for fx in ("acima_95", "entre_70_95", "abaixo_70"):
        sub = [e for e in lote if e["faixa"] == fx]
        if sub:
            tt = sum(1 for e in sub if e["conf_ia"])
            met.append([f"ultimo_lote_faixa_{fx}_qtd", len(sub)])
            met.append([f"ultimo_lote_faixa_{fx}_concordancia", round(tt / len(sub), 4)])
    pl.escrever_aba(sh, abas["metricas"], ["metrica", "valor"], met)

    print(f"OK: {len(lote)} classificados | restam {len(pendentes) - len(lote)} pendentes | "
          "abas atualizadas (turnos/linha/snapshot/config/metricas).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
