#!/usr/bin/env python3
"""Analise de ERROS da IA contra a verdade validada: por que a IA erra e que
informacoes pedir ao SOLICITANTE para a categoria sair certa.

Hipotese do pesquisador (2026-06-10): melhorando a qualidade do titulo e da
descricao, a IA acerta mais a categoria. Este script TESTA essa hipotese nos
chamados conferidos manualmente e converte o resultado em recomendacoes
operacionais de abertura de chamado — sem nunca pedir ao solicitante que
escolha a categoria (ele tambem erra).

Como funciona (apenas chamados com conferencia da IA, coluna N):
1. separa ACERTOS (N=Correto) de ERROS (N=Errado) da classificacao IA (col G);
2. mede caracteristicas do texto de cada chamado: comprimento do titulo, da
   descricao, n de tokens, campos preenchidos (descricao GLPI/titulo OSM/
   descricao OSM) e COBERTURA DE TERMOS DISCRIMINATIVOS da categoria verdadeira
   (termos do log-odds publicado em termos_relevantes.json presentes no texto);
3. compara erros x acertos com Mann-Whitney U (nao parametrico, padrao do
   projeto) + delta de Cliff (tamanho de efeito);
4. por categoria (verdade validada): taxa de erro da IA e os termos
   discriminativos que mais FALTAM nos textos dos erros — a base do checklist
   "o que pedir ao solicitante".

Saida: docs/dados/analise_erros.json (sanitizado: agregados e termos publicos,
sem texto de chamado). Read-only na planilha. Enquanto a conferencia for
insuficiente, emite status 'aguardando_validacao'.
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planilha as pl  # noqa: E402
import decisao_validada as dv  # noqa: E402
from tempo import agora_bahia  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
SAIDA = RAIZ / "docs" / "dados" / "analise_erros.json"
TERMOS_JSON = RAIZ / "docs" / "dados" / "termos_relevantes.json"

# Campos de abertura de chamado recomendados independentemente da categoria.
# A parte data-driven (termos por categoria) complementa, nunca substitui.
CAMPOS_FORMULARIO = [
    {"campo": "objeto/equipamento", "pergunta": "Qual equipamento ou item apresenta o problema? (ex.: ar condicionado split, torneira, luminaria, porta)"},
    {"campo": "sintoma", "pergunta": "O que esta acontecendo? (ex.: nao liga, vazando, entupido, quebrado, barulho)"},
    {"campo": "local", "pergunta": "Onde fica? (predio/bloco, andar, sala/laboratorio)"},
    {"campo": "desde_quando", "pergunta": "Desde quando ocorre e se e intermitente ou continuo"},
]


def _norm(s) -> str:
    t = unicodedata.normalize("NFKD", str(s or ""))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return " ".join(t.split()).casefold()


def _tokens(texto: str) -> list[str]:
    return _norm(texto).split()


def cliffs_delta(a: np.ndarray, b: np.ndarray) -> float:
    """Delta de Cliff (a=erros, b=acertos): -1..1; |d|<0,147 desprezivel."""
    if len(a) == 0 or len(b) == 0:
        return 0.0
    # O(n log n) via ranks: delta = 2*AUC - 1.
    from scipy.stats import rankdata
    tudo = np.concatenate([a, b])
    r = rankdata(tudo)
    r_a = r[:len(a)].sum()
    auc = (r_a - len(a) * (len(a) + 1) / 2) / (len(a) * len(b))
    return float(2 * auc - 1)


def mann_whitney(a: np.ndarray, b: np.ndarray) -> float | None:
    if len(a) < 3 or len(b) < 3:
        return None
    try:
        from scipy.stats import mannwhitneyu
        return float(mannwhitneyu(a, b, alternative="two-sided").pvalue)
    except Exception:  # noqa: BLE001
        return None


def carregar_chamados(ws, range_a1: str = "A:P") -> dict[int, dict]:
    """{linha: {titulo, descricao, texto, n_campos}} da aba principal."""
    valores = pl.ler_valores(ws, range_a1)
    cab = valores[0] if valores else []
    idx = {_norm(n): i for i, n in enumerate(cab)}
    i_tit = idx.get(_norm("TÍTULO"))
    i_dg = idx.get(_norm("DESCRIÇÃO GLPI"))
    i_to = idx.get(_norm("TÍTULO O.S.M."))
    i_do = idx.get(_norm("DESCRIÇÃO O.S.M."))

    def cel(linha, i):
        return str(linha[i] or "").strip() if (i is not None and i < len(linha)) else ""

    out = {}
    for pos, linha in enumerate(valores[1:], start=2):
        titulo = cel(linha, i_tit)
        partes = [cel(linha, i_dg), cel(linha, i_to), cel(linha, i_do)]
        descricao = "\n".join(p for p in partes if p)
        if not titulo and not descricao:
            continue
        out[pos] = {
            "titulo": titulo,
            "descricao": descricao,
            "texto": (titulo + "\n" + descricao).strip(),
            "n_campos": sum(1 for p in partes if p),
        }
    return out


def carregar_termos() -> dict[str, list[str]]:
    """{categoria: [termos log-odds publicados]} de termos_relevantes.json."""
    try:
        d = json.loads(TERMOS_JSON.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    out = {}
    for cat, info in (d.get("termos_por_categoria") or {}).items():
        termos = [t.get("termo", "") for t in (info.get("top_log_odds") or []) if t.get("termo")]
        if termos:
            out[cat] = termos
    return out


def cobertura_termos(texto: str, termos: list[str]) -> float:
    """Fracao dos termos discriminativos da categoria presentes no texto."""
    if not termos:
        return 0.0
    t = " " + " ".join(_tokens(texto)) + " "
    presentes = sum(1 for termo in termos if f" {_norm(termo)} " in t or _norm(termo) in t)
    return presentes / len(termos)


def features(chamado: dict, termos_cat: list[str]) -> dict[str, float]:
    return {
        "comprimento_titulo": float(len(chamado["titulo"])),
        "comprimento_descricao": float(len(chamado["descricao"])),
        "n_tokens": float(len(_tokens(chamado["texto"]))),
        "campos_preenchidos": float(chamado["n_campos"]),
        "cobertura_termos_categoria": cobertura_termos(chamado["texto"], termos_cat),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Analise de erros da IA vs qualidade do texto.")
    p.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    p.add_argument("--credenciais", default=None)
    p.add_argument("--min-validados", type=int, default=30,
                   help="Minimo de chamados com conferencia da IA (N) para emitir numeros.")
    p.add_argument("--min-erros-categoria", type=int, default=3)
    p.add_argument("--top-termos-faltantes", type=int, default=8)
    p.add_argument("--saida", type=Path, default=SAIDA)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    with args.config.open("r", encoding="utf-8") as f:
        config = json.load(f)
    gerado = agora_bahia()

    try:
        sh = pl.abrir_planilha(pl.id_planilha(config), args.credenciais)
        ws = sh.worksheet(config["aba_principal"])
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001
        print(f"Falha ao acessar planilha: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    decisoes = dv.carregar_decisoes(sh, config["aba_principal"])
    conf = pl.ler_conferencias(sh, config["aba_principal"])
    chamados = carregar_chamados(ws)
    termos = carregar_termos()

    # Casos com veredito humano sobre a IA (coluna N) e texto disponivel.
    casos = []
    for ln_str, v in conf.items():
        ln = int(ln_str)
        if v.get("ia") is None or ln not in chamados:
            continue
        d = decisoes.get(ln, {})
        casos.append({
            "linha": ln,
            "ia_acertou": v["ia"] == "Correto",
            "verdade": d.get("decidida"),  # pode ser None (so sabemos que a IA errou)
            "chamado": chamados[ln],
        })
    n_conf_ia = len(casos)
    print(f"chamados com conferencia da IA (N): {n_conf_ia}")

    saida = {"gerado_em": gerado,
             "natureza": ("analise exploratoria de erros da IA contra a conferencia humana; "
                          "orienta a qualidade da ABERTURA do chamado, nao e metrica de producao"),
             "n_conferidos_ia": n_conf_ia,
             "minimo_recomendado": args.min_validados,
             "campos_formulario_sugeridos": CAMPOS_FORMULARIO}

    if n_conf_ia < args.min_validados:
        saida["status"] = "aguardando_validacao"
        saida["mensagem"] = (f"Apenas {n_conf_ia} chamados com conferencia da IA (coluna N); "
                             f"minimo recomendado: {args.min_validados}. Termine a conferencia manual.")
        args.saida.parent.mkdir(parents=True, exist_ok=True)
        args.saida.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")
        print("status=aguardando_validacao; JSON gravado.")
        return 0

    erros = [c for c in casos if not c["ia_acertou"]]
    acertos = [c for c in casos if c["ia_acertou"]]

    # ---- 1) erros x acertos por caracteristica do texto ----
    feats_err, feats_ok = defaultdict(list), defaultdict(list)
    for c in casos:
        termos_cat = termos.get(c["verdade"] or "", [])
        fs = features(c["chamado"], termos_cat)
        alvo = feats_ok if c["ia_acertou"] else feats_err
        for k, v in fs.items():
            # cobertura so e comparavel quando a categoria verdadeira e conhecida
            if k == "cobertura_termos_categoria" and not c["verdade"]:
                continue
            alvo[k].append(v)

    comparacao = []
    for k in ["comprimento_titulo", "comprimento_descricao", "n_tokens",
              "campos_preenchidos", "cobertura_termos_categoria"]:
        a = np.array(feats_err.get(k, []))
        b = np.array(feats_ok.get(k, []))
        if len(a) == 0 or len(b) == 0:
            continue
        comparacao.append({
            "caracteristica": k,
            "n_erros": int(len(a)), "n_acertos": int(len(b)),
            "mediana_erros": round(float(np.median(a)), 4),
            "mediana_acertos": round(float(np.median(b)), 4),
            "p_mann_whitney": mann_whitney(a, b),
            "delta_cliff": round(cliffs_delta(a, b), 4),
        })

    # ---- 2) por categoria verdadeira: taxa de erro + termos que faltam ----
    por_cat = defaultdict(lambda: {"n": 0, "erros": 0, "faltantes": defaultdict(int)})
    for c in casos:
        cat = c["verdade"]
        if not cat:
            continue
        d = por_cat[cat]
        d["n"] += 1
        if not c["ia_acertou"]:
            d["erros"] += 1
            t = " " + " ".join(_tokens(c["chamado"]["texto"])) + " "
            for termo in termos.get(cat, []):
                if f" {_norm(termo)} " not in t and _norm(termo) not in t:
                    d["faltantes"][termo] += 1

    categorias = []
    for cat, d in sorted(por_cat.items(), key=lambda kv: -(kv[1]["erros"] / max(1, kv[1]["n"]))):
        if d["n"] < 1:
            continue
        falt = sorted(d["faltantes"].items(), key=lambda kv: -kv[1])[:args.top_termos_faltantes] \
            if d["erros"] >= args.min_erros_categoria else []
        categorias.append({
            "categoria": cat,
            "n_conferidos": d["n"],
            "erros_ia": d["erros"],
            "taxa_erro_ia": round(d["erros"] / d["n"], 4),
            "termos_que_faltaram_nos_erros": [
                {"termo": t, "ausente_em": k} for t, k in falt],
            "informacao_a_solicitar": (
                "Pedir que o solicitante descreva o problema citando o objeto e o sintoma "
                f"(vocabulario tipico desta categoria: {', '.join(t for t, _ in falt[:5])})."
                if falt else None),
        })

    saida.update({
        "status": "ok",
        "n_erros_ia": len(erros),
        "n_acertos_ia": len(acertos),
        "comparacao_erros_vs_acertos": comparacao,
        "leitura": ("Se 'cobertura_termos_categoria' e comprimentos forem significativamente "
                    "menores nos ERROS (p<0,05 e |delta de Cliff|>=0,147), a hipotese se "
                    "confirma: texto pobre -> erro de categoria. O checklist por categoria "
                    "lista os termos discriminativos ausentes nos erros — e a informacao "
                    "que o formulario deve induzir o solicitante a fornecer, sem nunca "
                    "pedir a categoria em si."),
        "por_categoria": categorias,
    })
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: analise de erros gravada em {args.saida} | erros={len(erros)} | acertos={len(acertos)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
