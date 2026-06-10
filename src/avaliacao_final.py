#!/usr/bin/env python3
"""Avaliacao FINAL contra a verdade validada: qual IA usar, com que peso, e se
vale a pena combinar.

Responde, assim que a conferencia manual (M/N/P) tiver volume suficiente:
1. qual IA/metodo e o mais apropriado para a reclassificacao;
2. qual o peso de cada IA (acuracia validada e log-odds para voto ponderado);
3. o quanto a melhor IA e melhor que as outras (delta + IC95 bootstrap);
4. se vale a pena combinar as IAs (ensembles avaliados out-of-fold dentro do
   conjunto validado, com McNemar contra a melhor IA isolada).

Verdade = categoria DECIDIDA pela conferencia humana (decisao_validada):
N=Correto -> G; M=Correto -> C; P=Correto -> O. Concordancia com o historico NAO
entra aqui como acerto. Enquanto validados < --min-validados, o JSON sai com
status 'aguardando_validacao' (o dashboard mostra o aviso, nao numeros vazios).

Honestidade estatistica: os pesos do voto ponderado sao aprendidos APENAS nos
folds de treino e avaliados no fold de teste (k-fold sobre os validados), para
nao avaliar o ensemble com peso ajustado no proprio dado.

Saida: docs/dados/avaliacao_final.json (sanitizado: sem texto de chamado).
Read-only na planilha; dry-run por natureza.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planilha as pl  # noqa: E402
import decisao_validada as dv  # noqa: E402
from tempo import agora_bahia  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
SAIDA = RAIZ / "docs" / "dados" / "avaliacao_final.json"
NATUREZA = ("acerto contra a VERDADE VALIDADA pela conferencia humana (M/N/P); "
            "NAO e concordancia com o historico")


def parse_conf(v) -> float:
    try:
        f = float(str(v).replace("%", "").replace(",", ".").strip())
        return f / 100.0 if f > 1 else f
    except (ValueError, TypeError):
        return 0.0


def carregar_config(caminho: Path) -> dict:
    with caminho.open("r", encoding="utf-8") as f:
        return json.load(f)


def carregar_predicoes(sh, config, modelos) -> dict[str, dict[int, dict]]:
    """{modelo: {linha: {'pred': cat, 'conf': float}}} das abas CLASSIF__<m>."""
    template = config["multimodelo"]["aba_classificacao"]
    out = {}
    for m in modelos:
        aba = template.replace("{modelo}", m)
        try:
            vals = sh.worksheet(aba).get_values("A:K", value_render_option="UNFORMATTED_VALUE")
        except Exception:  # noqa: BLE001
            continue
        d = {}
        for r in vals[1:]:
            if len(r) < 6:
                continue
            try:
                ln = int(r[1])
            except (ValueError, TypeError):
                continue
            pred = str(r[4] or "").strip()
            if pred:
                d[ln] = {"pred": pred, "conf": parse_conf(r[5])}
        if d:
            out[m] = d
    return out


def _carregar_calibradores() -> dict[str, dict]:
    arq = RAIZ / "docs" / "dados" / "calibracao_ajustada_modelos.json"
    try:
        d = json.loads(arq.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return {m.get("modelo"): (m.get("calibrador") or {}) for m in d.get("modelos", [])}


def _calibrar(calibrador: dict, conf: float) -> float:
    g = (calibrador or {}).get("y_grid")
    c = max(0.0, min(1.0, float(conf or 0.0)))
    if not g:
        return c
    pos = c * (len(g) - 1)
    i = int(pos)
    if i >= len(g) - 1:
        return float(g[-1])
    f = pos - i
    return float(g[i] * (1 - f) + g[i + 1] * f)


def ic_bootstrap(acertos: np.ndarray, n_boot: int, seed: int = 42) -> tuple[float, float]:
    if len(acertos) == 0:
        return (0.0, 0.0)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(acertos), size=(n_boot, len(acertos)))
    medias = acertos[idx].mean(axis=1)
    return (float(np.percentile(medias, 2.5)), float(np.percentile(medias, 97.5)))


def peso_log_odds(acc: float, eps: float = 1e-3) -> float:
    """Peso classico do voto ponderado por maioria: ln(acc/(1-acc)), recortado."""
    a = min(max(acc, eps), 1 - eps)
    return math.log(a / (1 - a))


def mcnemar_p(b: int, c: int) -> float | None:
    """McNemar exato (binomial) nos pares discordantes b (so A acerta) x c (so B)."""
    n = b + c
    if n == 0:
        return None
    try:
        from scipy.stats import binomtest
        return float(binomtest(min(b, c), n, 0.5).pvalue)
    except Exception:  # noqa: BLE001
        # Fallback: aproximacao normal com correcao de continuidade.
        from math import erf, sqrt
        z = (abs(b - c) - 1) / sqrt(n) if n > 0 else 0.0
        return float(2 * (1 - 0.5 * (1 + erf(z / sqrt(2)))))


# ---- Ensembles -------------------------------------------------------------

def votar_maioria(preds_linha: dict[str, dict], pesos: dict[str, float] | None,
                  vetadas: set[str], calibradores: dict | None = None) -> str | None:
    """Voto (ponderado ou nao) entre os modelos para UMA linha, respeitando o
    veto das categorias ja conferidas como erradas (regra de memoria)."""
    urna: Counter = Counter()
    conf_total: Counter = Counter()
    for m, pc in preds_linha.items():
        cat = pc["pred"]
        if cat in vetadas:
            continue  # nao repetir erro conferido
        w = (pesos or {}).get(m, 1.0)
        urna[cat] += w
        conf = pc["conf"]
        if calibradores is not None:
            conf = _calibrar(calibradores.get(m, {}), conf)
        conf_total[cat] += conf
    if not urna:
        return None
    # Desempate: maior soma de votos > maior soma de confianca > ordem alfabetica.
    return max(urna, key=lambda c: (urna[c], conf_total[c], c))


def confianca_maxima(preds_linha: dict[str, dict], calibradores: dict,
                     vetadas: set[str]) -> str | None:
    """Escolhe a predicao do modelo com maior confianca CALIBRADA."""
    melhor, melhor_conf = None, -1.0
    for m, pc in sorted(preds_linha.items()):
        if pc["pred"] in vetadas:
            continue
        conf = _calibrar(calibradores.get(m, {}), pc["conf"])
        if conf > melhor_conf:
            melhor, melhor_conf = pc["pred"], conf
    return melhor


def avaliar_ensembles_oof(linhas: list[int], verdade: dict[int, str],
                          preds: dict[str, dict[int, dict]], vetos: dict[int, set],
                          calibradores: dict, k: int, seed: int = 42) -> dict[str, np.ndarray]:
    """Acertos (0/1) por linha de cada metodo de combinacao, com pesos aprendidos
    OUT-OF-FOLD: o peso usado na linha i vem so dos outros folds."""
    modelos = sorted(preds)
    n = len(linhas)
    res = {"maioria_simples": np.zeros(n), "maioria_ponderada": np.zeros(n),
           "confianca_calibrada_max": np.zeros(n)}
    from sklearn.model_selection import KFold
    kk = max(2, min(k, n))
    kf = KFold(n_splits=kk, shuffle=True, random_state=seed)
    for tr_idx, te_idx in kf.split(range(n)):
        # pesos do fold: acuracia validada APENAS nas linhas de treino
        pesos = {}
        for m in modelos:
            oks = [1.0 if preds[m].get(linhas[i], {}).get("pred") == verdade[linhas[i]] else 0.0
                   for i in tr_idx if linhas[i] in preds[m]]
            acc = float(np.mean(oks)) if oks else 0.5
            pesos[m] = max(0.0, peso_log_odds(acc))
        for i in te_idx:
            ln = linhas[i]
            pl_ = {m: preds[m][ln] for m in modelos if ln in preds[m]}
            vet = vetos.get(ln, set())
            v = votar_maioria(pl_, None, vet)
            res["maioria_simples"][i] = 1.0 if v == verdade[ln] else 0.0
            v = votar_maioria(pl_, pesos, vet, calibradores)
            res["maioria_ponderada"][i] = 1.0 if v == verdade[ln] else 0.0
            v = confianca_maxima(pl_, calibradores, vet)
            res["confianca_calibrada_max"][i] = 1.0 if v == verdade[ln] else 0.0
    return res


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Avaliacao final validada: qual IA, peso e ensemble.")
    p.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    p.add_argument("--credenciais", default=None)
    p.add_argument("--min-validados", type=int, default=50,
                   help="Minimo de chamados com decisao travada para emitir numeros.")
    p.add_argument("--n-boot", type=int, default=2000)
    p.add_argument("--k-folds", type=int, default=5)
    p.add_argument("--saida", type=Path, default=SAIDA)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    config = carregar_config(args.config)
    mm = config.get("multimodelo", {})
    modelos = list(mm.get("modelos_leves", [])) + list(mm.get("modelos_pesados", []))
    gerado = agora_bahia()

    try:
        sh = pl.abrir_planilha(pl.id_planilha(config), args.credenciais)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001
        print(f"Falha ao acessar planilha: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    decisoes = dv.carregar_decisoes(sh, config["aba_principal"])
    verdade = dv.verdade_validada(decisoes)
    vetos = {ln: set(d.get("eliminadas") or set()) for ln, d in decisoes.items()}
    res_dec = dv.resumo_decisoes(decisoes)
    validados = len(verdade)
    print(f"conferencias={res_dec['com_conferencia']} | decididos(verdade)={validados} | "
          f"restritos={res_dec['restritos']} | conflitos={res_dec['conflitos']}")

    saida = {
        "gerado_em": gerado,
        "natureza": NATUREZA,
        "validados": validados,
        "minimo_recomendado": args.min_validados,
        "conferencias": res_dec,
    }

    if validados < args.min_validados:
        saida["status"] = "aguardando_validacao"
        saida["mensagem"] = (f"Apenas {validados} chamados com decisao travada "
                             f"(minimo recomendado: {args.min_validados}). Termine a conferencia "
                             "manual (M/N) para liberar a avaliacao final.")
        args.saida.parent.mkdir(parents=True, exist_ok=True)
        args.saida.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"status=aguardando_validacao (validados={validados}); JSON gravado.")
        return 0

    preds = carregar_predicoes(sh, config, modelos)
    if not preds:
        print("Nenhuma aba CLASSIF__<modelo> legivel.", file=sys.stderr)
        return 1
    calibradores = _carregar_calibradores()

    # Linhas avaliaveis: verdade conhecida e TODOS os modelos com predicao
    # (paridade entre IAs — mesma base de comparacao, como na estatistica).
    linhas = sorted(ln for ln in verdade if all(ln in preds[m] for m in preds))
    n = len(linhas)
    print(f"linhas avaliaveis (verdade + 7 predicoes): {n}")
    saida["n_avaliado"] = n
    if n < args.min_validados:
        saida["status"] = "aguardando_validacao"
        saida["mensagem"] = (f"So {n} validados tem predicao de todos os modelos "
                             f"(minimo: {args.min_validados}).")
        args.saida.parent.mkdir(parents=True, exist_ok=True)
        args.saida.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0

    # ---- por modelo ----
    por_modelo = []
    acertos_modelo: dict[str, np.ndarray] = {}
    for m in sorted(preds):
        oks = np.array([1.0 if preds[m][ln]["pred"] == verdade[ln] else 0.0 for ln in linhas])
        acertos_modelo[m] = oks
        acc = float(oks.mean())
        lo, hi = ic_bootstrap(oks, args.n_boot)
        por_modelo.append({"modelo": m, "n": n, "acerto_validado": round(acc, 4),
                           "ic95": [round(lo, 4), round(hi, 4)],
                           "peso_log_odds": round(peso_log_odds(acc), 4)})
    por_modelo.sort(key=lambda d: -d["acerto_validado"])
    soma_acc = sum(d["acerto_validado"] for d in por_modelo) or 1.0
    for d in por_modelo:
        d["peso_normalizado"] = round(d["acerto_validado"] / soma_acc, 4)
    melhor = por_modelo[0]
    segundo = por_modelo[1] if len(por_modelo) > 1 else None

    # delta melhor vs segunda (com McNemar)
    if segundo:
        a, b = acertos_modelo[melhor["modelo"]], acertos_modelo[segundo["modelo"]]
        so_a = int(((a == 1) & (b == 0)).sum())
        so_b = int(((a == 0) & (b == 1)).sum())
        melhor_vs_segundo = {
            "segundo": segundo["modelo"],
            "delta": round(melhor["acerto_validado"] - segundo["acerto_validado"], 4),
            "p_mcnemar": mcnemar_p(so_a, so_b),
        }
    else:
        melhor_vs_segundo = None

    # ---- ensembles (out-of-fold) ----
    ens = avaliar_ensembles_oof(linhas, verdade, preds, vetos, calibradores, args.k_folds)
    ensembles = []
    a_melhor = acertos_modelo[melhor["modelo"]]
    for nome, oks in ens.items():
        acc = float(oks.mean())
        lo, hi = ic_bootstrap(oks, args.n_boot, seed=43)
        so_e = int(((oks == 1) & (a_melhor == 0)).sum())
        so_m = int(((oks == 0) & (a_melhor == 1)).sum())
        ensembles.append({"metodo": nome, "acerto_validado": round(acc, 4),
                          "ic95": [round(lo, 4), round(hi, 4)],
                          "delta_vs_melhor_ia": round(acc - melhor["acerto_validado"], 4),
                          "p_mcnemar_vs_melhor_ia": mcnemar_p(so_e, so_m)})
    ensembles.sort(key=lambda d: -d["acerto_validado"])
    melhor_ens = ensembles[0]

    combinar = (melhor_ens["delta_vs_melhor_ia"] > 0
                and (melhor_ens["p_mcnemar_vs_melhor_ia"] or 1.0) < 0.05)
    if combinar:
        recomendacao = melhor_ens["metodo"]
        justificativa = (f"O ensemble '{melhor_ens['metodo']}' supera a melhor IA isolada "
                         f"({melhor['modelo']}) em {melhor_ens['delta_vs_melhor_ia']:+.4f} "
                         f"com McNemar p={melhor_ens['p_mcnemar_vs_melhor_ia']:.4f} (<0,05).")
    else:
        recomendacao = melhor["modelo"]
        justificativa = ("Nenhum ensemble supera a melhor IA isolada com significancia "
                         "(McNemar p>=0,05) — combinar nao compensa o custo adicional; "
                         f"use '{melhor['modelo']}' com calibracao.")

    saida.update({
        "status": "ok",
        "por_modelo": por_modelo,
        "melhor_ia": melhor["modelo"],
        "melhor_vs_segundo": melhor_vs_segundo,
        "ensembles": ensembles,
        "vale_combinar": {"veredicto": bool(combinar), "recomendacao": recomendacao,
                          "justificativa": justificativa},
        "observacoes": [
            "Pesos do voto ponderado aprendidos out-of-fold (k-fold nos validados).",
            "Votos que cairiam em categoria ja conferida como ERRADA sao vetados (regra de memoria).",
            "Amostra validada pode nao ser aleatoria (priorizou divergentes); interpretar como piso/teto conforme o desenho da conferencia.",
        ],
    })
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: avaliacao final gravada em {args.saida} | melhor_ia={melhor['modelo']} | "
          f"melhor_ensemble={melhor_ens['metodo']} ({melhor_ens['delta_vs_melhor_ia']:+.4f}) | "
          f"vale_combinar={combinar}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
