#!/usr/bin/env python3
"""Classificação IA - 3: classifica os chamados também com o HISTÓRICO GLPI (coluna R) e grava na coluna S.

Texto de cada chamado = TÍTULO (B) + DESCRIÇÃO GLPI (D) + TÍTULO O.S.M. (E) + DESCRIÇÃO O.S.M. (F)
+ HISTÓRICO GLPI (R). Os campos vazios são ignorados (E/F só existem nos chamados com ordem de serviço;
R vazia, "(sem interações)" ou "(indisponível...)" também não entram no texto).

Pergunta que o experimento responde: o histórico (R) muda a classificação?
Para isso o mesmo modelo (TF-IDF + regressão logística) é treinado em DUAS versões do texto, com e sem R,
e as duas são avaliadas com predição FORA DA AMOSTRA (k-fold) contra a verdade validada (M/N/P/Q,
via `decisao_validada`). A coluna S recebe a predição fora da amostra da versão COM R.

Garantias:
- Sem --aplicar = simulação: nada é gravado; o relatório fica em dados/classificacao_s_relatorio.json.
- Com --aplicar grava SOMENTE a coluna S (cria o cabeçalho/coluna se faltar). Nunca toca em A:R,
  nem em G, M, N, O, P ou Q. Antes de gravar confere o alinhamento linha x id_chamado.
- Não altera a coluna O (Classificação IA - 2, escrita pelo comitê).
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import decisao_validada as dv  # noqa: E402
import planilha as pl  # noqa: E402
from tempo import agora_bahia  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
DADOS = RAIZ / "dados"

COL_S = 19  # S (1-based)
CABECALHO_S = "Classificação IA - 3 (B+D+E+F+R)"
NOME_R = "HISTÓRICO GLPI"
CAMPOS_BASE = ("TÍTULO", "DESCRIÇÃO GLPI", "TÍTULO O.S.M.", "DESCRIÇÃO O.S.M.")
MARCA_SEM_INTERACOES = "(sem interações)"


def norm(s: Any) -> str:
    return " ".join(str(s or "").split()).casefold()


def cel(linha: list[Any], idx: int | None) -> str:
    return str(linha[idx] or "").strip() if (idx is not None and idx < len(linha)) else ""


def historico_util(valor: Any) -> str:
    """Texto do histórico que vale como informação (ignora marcadores do script de coleta)."""
    v = str(valor or "").strip()
    if not v or v == MARCA_SEM_INTERACOES or v.startswith("(indisponível"):
        return ""
    return v


_PREFIXO_ENTRADA = re.compile(
    r"^\[\d{2}/\d{2}/\d{4} \d{2}:\d{2}\]\s*(?:Acompanhamento|Tarefa|Solução)(?: \([^)]*\))?(?: \[privado\])?:\s*", re.M)
_LINHA_DOCUMENTO = re.compile(r"^Documento adicionado:.*$", re.M)


def limpar_historico(valor: str) -> str:
    """Só o conteúdo das interações: tira data, tipo, login e a lista de anexos (que só poluem o texto)."""
    t = _LINHA_DOCUMENTO.sub("", _PREFIXO_ENTRADA.sub("", valor))
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def montar_texto(linha: list[Any], idx: dict[str, int], variante: bool | str) -> str:
    """variante: False/'sem' = B+D+E+F; True/'bruto' = + R como está; 'limpo' = + R só com o conteúdo."""
    partes = [cel(linha, idx.get(norm(nome))) for nome in CAMPOS_BASE]
    if variante not in (False, "sem"):
        h = historico_util(cel(linha, idx.get(norm(NOME_R))))
        partes.append(limpar_historico(h) if variante == "limpo" else h)
    return "\n".join(p for p in partes if p)


def normalizar_id(valor: Any) -> str:
    bruto = str(valor or "").strip()
    if not bruto:
        return ""
    try:
        return str(int(float(bruto)))
    except (TypeError, ValueError):
        return bruto


def novo_modelo():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    return Pipeline([
        ("tfidf", TfidfVectorizer(strip_accents="unicode", lowercase=True,
                                  ngram_range=(1, 2), min_df=1, max_features=30000)),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced", solver="lbfgs")),
    ])


def prever_fora_da_amostra(textos: list[str], rotulos: list[str], k: int, semente: int):
    """Predição k-fold: cada chamado é previsto por um modelo que NÃO o viu no treino."""
    from sklearn.model_selection import KFold

    n = len(textos)
    preds = [""] * n
    confs = [0.0] * n
    for treino, teste in KFold(n_splits=k, shuffle=True, random_state=semente).split(np.arange(n)):
        clf = novo_modelo()
        clf.fit([textos[i] for i in treino], [rotulos[i] for i in treino])
        probs = clf.predict_proba([textos[i] for i in teste])
        melhor = probs.argmax(axis=1)
        for pos, i in enumerate(teste):
            preds[i] = str(clf.classes_[melhor[pos]])
            confs[i] = float(probs[pos, melhor[pos]])
    return preds, confs


def mcnemar_exato(n_a_certo_b_errado: int, n_b_certo_a_errado: int) -> float:
    """p-valor bilateral do teste de McNemar exato (binomial, p=0,5) sobre os discordantes."""
    n = n_a_certo_b_errado + n_b_certo_a_errado
    if n == 0:
        return 1.0
    menor = min(n_a_certo_b_errado, n_b_certo_a_errado)
    cauda = sum(math.comb(n, k) for k in range(menor + 1)) / (2 ** n)
    return min(1.0, 2 * cauda)


def avaliar(ids_linha: list[int], preds_base: list[str], preds_r: list[str],
            tem_historico: list[bool], verdade: dict[int, str],
            historica: list[str], coluna_g: list[str]) -> dict[str, Any]:
    """Compara as duas versões do texto contra a verdade validada (só chamados com decisão travada)."""
    val = [i for i, ln in enumerate(ids_linha) if ln in verdade]

    def acerto(preds: list[str], sub: list[int]) -> float | None:
        return round(sum(1 for i in sub if preds[i] == verdade[ids_linha[i]]) / len(sub), 4) if sub else None

    base_ok_r_erra = sum(1 for i in val if preds_base[i] == verdade[ids_linha[i]] != preds_r[i])
    r_ok_base_erra = sum(1 for i in val if preds_r[i] == verdade[ids_linha[i]] != preds_base[i])
    com_hist = [i for i in val if tem_historico[i]]
    g_val = [i for i in val if coluna_g[i]]
    return {
        "validados": len(val),
        "validados_com_historico_util": len(com_hist),
        "acerto_categoria_historica": acerto(historica, val),
        "acerto_coluna_G_atual": acerto(coluna_g, g_val),
        "acerto_sem_R_fora_da_amostra": acerto(preds_base, val),
        "acerto_com_R_fora_da_amostra": acerto(preds_r, val),
        "acerto_sem_R_so_com_historico": acerto(preds_base, com_hist),
        "acerto_com_R_so_com_historico": acerto(preds_r, com_hist),
        "so_sem_R_acerta": base_ok_r_erra,
        "so_com_R_acerta": r_ok_base_erra,
        "mcnemar_p": round(mcnemar_exato(base_ok_r_erra, r_ok_base_erra), 6),
        "mudou_predicao_total": sum(1 for a, b in zip(preds_base, preds_r) if a != b),
        "total_classificados": len(preds_r),
    }


def conferir_alinhamento(ws, alvos: dict[int, str]) -> None:
    """Aborta se a coluna A mudou de lugar desde a leitura (mesma ideia do gate da etapa 1)."""
    linha_ini, linha_fim = min(alvos), max(alvos)
    bloco = pl.ler_valores(ws, f"A{linha_ini}:A{linha_fim}")
    divergentes = []
    for linha, esperado in alvos.items():
        off = linha - linha_ini
        atual = normalizar_id(bloco[off][0]) if off < len(bloco) and bloco[off] else ""
        if atual != esperado:
            divergentes.append((linha, esperado, atual))
    if divergentes:
        amostra = "; ".join(f"linha {ln}: esperado={e or '(vazio)'}, atual={a or '(vazio)'}" for ln, e, a in divergentes[:10])
        raise RuntimeError(f"alinhamento linha x id_chamado mudou; nada foi gravado ({len(divergentes)} divergências). {amostra}")


def gravar_coluna_s(ws, valores_por_linha: dict[int, str], ids_por_linha: dict[int, str]) -> int:
    """Grava SOMENTE a coluna S (cabeçalho em S1 e valores abaixo)."""
    if getattr(ws, "col_count", COL_S) < COL_S:
        ws.add_cols(COL_S - ws.col_count)
    conferir_alinhamento(ws, ids_por_linha)
    ultima = max(valores_por_linha)
    bloco = [[valores_por_linha.get(ln, "")] for ln in range(2, ultima + 1)]
    ws.update(range_name="S1", values=[[CABECALHO_S]], value_input_option="RAW")
    ws.update(range_name=f"S2:S{ultima}", values=bloco, value_input_option="RAW")
    return len(valores_por_linha)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    p.add_argument("--credenciais", default=None)
    p.add_argument("--folds", type=int, default=5)
    p.add_argument("--semente", type=int, default=42)
    p.add_argument("--variante", choices=["bruto", "limpo"], default="bruto",
                   help="Qual texto com R vai para a coluna S (as duas são sempre avaliadas).")
    p.add_argument("--aplicar", action="store_true", help="Grava a coluna S (sem isso: simulação).")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    with args.config.open("r", encoding="utf-8") as f:
        config = json.load(f)
    aba = config["aba_principal"]
    gerado = agora_bahia()

    try:
        sh = pl.abrir_planilha(pl.id_planilha(config), args.credenciais)
        ws = sh.worksheet(aba)
        valores = pl.ler_valores(ws, "A:S")
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2
    cab = valores[0] if valores else []
    idx = {norm(n): i for i, n in enumerate(cab)}
    if idx.get(norm(NOME_R)) is None:
        print(f"Coluna '{NOME_R}' não encontrada na aba {aba}.", file=sys.stderr)
        return 1
    i_id, i_cat, i_g = idx.get(norm("ID Chamado")), idx.get(norm("CATEGORIA COMPLETA")), idx.get(norm("Classificação IA"))

    decisoes = dv.carregar_decisoes(sh, aba)
    verdade = dv.verdade_validada(decisoes)

    linhas, ids, hist, textos_base, textos_r, textos_limpo, rotulos, tem_hist, col_g = [], {}, [], [], [], [], [], [], []
    for pos, linha in enumerate(valores[1:], start=2):
        cat = pl.normalizar_categoria(cel(linha, i_cat))
        t_base, t_r = montar_texto(linha, idx, "sem"), montar_texto(linha, idx, "bruto")
        t_limpo = montar_texto(linha, idx, "limpo")
        if not (cat and t_base):
            continue
        linhas.append(pos)
        ids[pos] = normalizar_id(cel(linha, i_id))
        hist.append(cat)
        textos_base.append(t_base)
        textos_r.append(t_r)
        textos_limpo.append(t_limpo)
        rotulos.append(verdade.get(pos) or cat)  # treino: verdade validada quando existe; senão a categoria histórica
        tem_hist.append(bool(historico_util(cel(linha, idx.get(norm(NOME_R))))))
        col_g.append(pl.normalizar_categoria(cel(linha, i_g)))

    print(f"classificáveis={len(linhas)} | validados={sum(1 for ln in linhas if ln in verdade)} | com histórico útil={sum(tem_hist)}")
    if len(linhas) < args.folds * 2:
        print("Informação insuficiente para verificar.")
        return 1

    print("treinando versão SEM R (k-fold)...")
    preds_base, _ = prever_fora_da_amostra(textos_base, rotulos, args.folds, args.semente)
    print("treinando versão COM R bruto (k-fold)...")
    preds_bruto, confs_bruto = prever_fora_da_amostra(textos_r, rotulos, args.folds, args.semente)
    print("treinando versão COM R limpo (k-fold)...")
    preds_limpo, confs_limpo = prever_fora_da_amostra(textos_limpo, rotulos, args.folds, args.semente)
    preds_r, confs_r = (preds_bruto, confs_bruto) if args.variante == "bruto" else (preds_limpo, confs_limpo)

    metricas = {
        "com_R_bruto": avaliar(linhas, preds_base, preds_bruto, tem_hist, verdade, hist, col_g),
        "com_R_limpo": avaliar(linhas, preds_base, preds_limpo, tem_hist, verdade, hist, col_g),
    }
    relatorio = {
        "gerado_em": gerado, "modelo": "TF-IDF + LogisticRegression", "folds": args.folds, "semente": args.semente,
        "texto_sem_R": "B+D+E+F", "texto_com_R_bruto": "B+D+E+F+R",
        "texto_com_R_limpo": "B+D+E+F+R sem data/login/anexos",
        "variante_na_coluna_S": args.variante, "coluna_saida": "S",
        "treino": "verdade validada (M/N/P/Q) quando existe; senão categoria histórica",
        "metricas": metricas,
    }
    DADOS.mkdir(parents=True, exist_ok=True)
    (DADOS / "classificacao_s_relatorio.json").write_text(json.dumps(relatorio, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metricas, ensure_ascii=False, indent=2))

    if not args.aplicar:
        print("modo=simulação (nada gravado na planilha)")
        return 0
    n = gravar_coluna_s(ws, dict(zip(linhas, preds_r)), {ln: ids[ln] for ln in linhas})
    print(f"OK: coluna S gravada em {n} linhas (confiança média {np.mean(confs_r):.3f}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
