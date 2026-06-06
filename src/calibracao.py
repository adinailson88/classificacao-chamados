#!/usr/bin/env python3
"""Calibração da confiança (o critério central do OBJETIVO FINAL).

Mede a relação CONFIANÇA × ACERTO: quando o modelo diz ">=95%", ele realmente
acerta ~>=95%? (não basta softmax alto). Calcula, a partir do SNAPSHOT_ETAPA_1:
- acerto por FAIXA de confiança (bins), por EXECUTOR;
- acerto vs classificação HISTÓRICA (col C) — disponível já;
- acerto vs categoria VALIDADA (VALIDACAO_HUMANA) — quando houver revisão humana;
- ECE (erro de calibração esperado) e o destaque da faixa >=95%.

Read-only: não escreve na planilha. Gera docs/dados/calibracao.json (agregado,
sem texto de chamado) para o dashboard.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planilha as pl  # noqa: E402
from tempo import agora_bahia  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
SAIDA = RAIZ / "docs" / "dados" / "calibracao.json"

# (limite_inferior, limite_superior, rotulo)
FAIXAS = [
    (0.0, 0.5, "<50%"),
    (0.5, 0.7, "50-70%"),
    (0.7, 0.8, "70-80%"),
    (0.8, 0.9, "80-90%"),
    (0.9, 0.95, "90-95%"),
    (0.95, 1.01, ">=95%"),
]


def parse_conf(v) -> float:
    try:
        f = float(str(v).replace("%", "").replace(",", ".").strip())
        return f / 100.0 if f > 1 else f
    except (ValueError, TypeError):
        return 0.0


def faixa_de(conf: float) -> str:
    for lo, hi, rot in FAIXAS:
        if lo <= conf < hi:
            return rot
    return ">=95%"


def carregar_validados(sh, aba) -> dict:
    """linha_planilha -> categoria_validada (só onde preenchida)."""
    try:
        vals = sh.worksheet(aba).get_all_values()
    except Exception:  # noqa: BLE001
        return {}
    if len(vals) < 2:
        return {}
    cab = {(" ".join(str(c).split()).casefold()): i for i, c in enumerate(vals[0])}
    i_ln = cab.get("linha_planilha")
    i_cv = cab.get("categoria_validada")
    if i_ln is None or i_cv is None:
        return {}
    m = {}
    for r in vals[1:]:
        ln = str(r[i_ln]).strip() if i_ln < len(r) else ""
        cv = str(r[i_cv]).strip() if i_cv < len(r) else ""
        if ln and cv:
            m[ln] = cv
    return m


def _agrega():
    return {"n": 0, "ok_hist": 0, "soma_conf": 0.0, "n_val": 0, "ok_val": 0}


def _fechar(d):
    n, nv = d["n"], d["n_val"]
    return {
        "n": n,
        "concordancia_historico": round(d["ok_hist"] / n, 4) if n else 0.0,
        "confianca_media": round(d["soma_conf"] / n, 4) if n else 0.0,
        "n_validados": nv,
        "acerto_validado": round(d["ok_val"] / nv, 4) if nv else None,
    }


def calcular(sh, config: dict) -> dict:
    abas = config["abas_experimento"]
    try:
        vals = sh.worksheet(abas["snapshot_etapa_1"]).get_values(
            "A:J", value_render_option="UNFORMATTED_VALUE")
    except Exception:  # noqa: BLE001
        vals = []
    # Modo de validacao atual: conferencia humana DUPLA na aba principal.
    # M (CONFERENCIA GLPI): a classificacao historica esta "Correto"/"Errado";
    # N (CONFERENCIA IA): a classificacao da IA esta "Correto"/"Errado".
    conferencias = pl.ler_conferencias(sh, config["aba_principal"])

    por_faixa = {rot: _agrega() for _, _, rot in FAIXAS}
    por_exec = {}
    geral = _agrega()
    # Matriz 2x2 IA(M) x GLPI(N) sobre as linhas com AMBAS conferencias preenchidas.
    matriz = {"ia_ok_glpi_ok": 0, "ia_ok_glpi_erro": 0, "ia_erro_glpi_ok": 0, "ia_erro_glpi_erro": 0}
    glpi = {"n": 0, "ok": 0}      # acerto validado da classificacao historica (coluna M)
    reclass = {"n": 0, "ok": 0}   # acerto validado da reclassificacao IA-2 (coluna P)
    # SNAPSHOT cols: 1 linha, 3 cat_original, 4 cat_ia, 5 conf, 6 executor
    for r in vals[1:]:
        if len(r) < 6:
            continue
        ln = str(r[1]).strip()
        orig = str(r[3]).strip()
        cat_ia = str(r[4]).strip()
        if not cat_ia:
            continue
        conf = parse_conf(r[5])
        execu = str(r[6]).strip() if len(r) > 6 else ""
        ok_hist = int(cat_ia == orig)
        # Conferencia humana: M => acerto da IA; N => acerto do historico (GLPI).
        conf_row = conferencias.get(ln, {})
        v_ia = conf_row.get("ia")
        v_glpi = conf_row.get("glpi")
        v_reclass = conf_row.get("reclass")
        tem_val = v_ia is not None
        ok_val = int(v_ia == "Correto") if tem_val else 0
        if v_glpi is not None:
            glpi["n"] += 1
            glpi["ok"] += int(v_glpi == "Correto")
        if v_reclass is not None:
            reclass["n"] += 1
            reclass["ok"] += int(v_reclass == "Correto")
        if v_ia is not None and v_glpi is not None:
            chave = ("ia_ok" if v_ia == "Correto" else "ia_erro") + \
                    ("_glpi_ok" if v_glpi == "Correto" else "_glpi_erro")
            matriz[chave] += 1

        for alvo in (geral, por_faixa[faixa_de(conf)], por_exec.setdefault(execu or "(sem)", _agrega())):
            alvo["n"] += 1
            alvo["ok_hist"] += ok_hist
            alvo["soma_conf"] += conf
            if tem_val:
                alvo["n_val"] += 1
                alvo["ok_val"] += ok_val

    # ECE vs histórico (erro de calibração esperado)
    n_tot = geral["n"]
    ece = 0.0
    if n_tot:
        for rot in por_faixa:
            d = por_faixa[rot]
            if d["n"]:
                taxa = d["ok_hist"] / d["n"]
                cmed = d["soma_conf"] / d["n"]
                ece += (d["n"] / n_tot) * abs(cmed - taxa)

    faixa95 = _fechar(por_faixa[">=95%"])
    return {
        "gerado_em": agora_bahia(),
        "run_id": config.get("run_id", ""),
        "total": n_tot,
        "validados": geral["n_val"],
        "validacao_humana": {
            "modo": "conferencia dupla (M=CONFERENCIA GLPI, N=CONFERENCIA IA)",
            "n_conferencia_ia": geral["n_val"],
            "acerto_ia_validado": round(geral["ok_val"] / geral["n_val"], 4) if geral["n_val"] else None,
            "n_conferencia_glpi": glpi["n"],
            "acerto_glpi_validado": round(glpi["ok"] / glpi["n"], 4) if glpi["n"] else None,
            "n_conferencia_reclass": reclass["n"],
            "acerto_reclass_validado": round(reclass["ok"] / reclass["n"], 4) if reclass["n"] else None,
            # Matriz 2x2 (apenas linhas com M e N preenchidas). ia_ok_glpi_erro = IA
            # corrige o historico; ia_erro_glpi_ok = IA piora o historico.
            "matriz_ia_x_glpi": matriz,
        },
        "ece_historico": round(ece, 4),
        "alvo_confianca": float(config.get("objetivo_final", {}).get("confianca_minima_alvo", 0.95)),
        "faixa_alvo_95": faixa95,
        "por_faixa": [{"faixa": rot, **_fechar(por_faixa[rot])} for _, _, rot in FAIXAS],
        "por_executor": [{"executor": k, **_fechar(v)} for k, v in sorted(por_exec.items())],
        # A confiança aqui é a saída BRUTA do modelo (softmax/decision_function), NÃO um
        # calibrador ajustado. Ver PLANO_CALIBRACAO.md (CalibratedClassifierCV p/ lineares
        # TF-IDF; temperature scaling p/ o LSTM). Este JSON é diagnóstico, não calibração.
        "tipo_confianca": "bruta (softmax/decision_function) — NAO calibrada",
        "calibrador_ajustado": False,
        "plano_calibracao": "PLANO_CALIBRACAO.md",
        "observacao": ("Acerto vs histórico é preliminar (a classificação histórica pode "
                       "ter erros). A confiança é bruta (softmax alto NÃO é confiança calibrada). "
                       "A validação humana usa conferência dupla: coluna M (CONFERÊNCIA GLPI) e "
                       "coluna N (CONFERÊNCIA IA), permitindo medir acerto da IA, acerto do "
                       "histórico e a matriz IA×GLPI (falsos positivos/negativos)."),
    }


def main() -> int:
    with CONFIG_PADRAO.open(encoding="utf-8") as f:
        config = json.load(f)
    try:
        sh = pl.abrir_planilha(pl.id_planilha(config))
    except Exception as e:  # noqa: BLE001
        print(f"Falha ao acessar a planilha: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    dados = calcular(sh, config)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"total={dados['total']} | validados={dados['validados']} | ECE_historico={dados['ece_historico']}")
    a = dados["faixa_alvo_95"]
    print(f"faixa >=95%: n={a['n']} | concordancia_historico={a['concordancia_historico']} | "
          f"acerto_validado={a['acerto_validado']}")
    print(f"saida={SAIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
