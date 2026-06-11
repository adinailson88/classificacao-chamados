#!/usr/bin/env python3
"""Auditoria sanitizada das conferencias humanas M/N/P.

Le a aba principal, conta inconsistencias operacionais e gera
docs/dados/auditoria_conferencias.json sem texto livre e sem ID de chamado.
Com --aplicar, grava tambem uma aba privada AUDITORIA_CONFERENCIAS.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import decisao_validada as dv  # noqa: E402
import planilha as pl  # noqa: E402
from tempo import agora_bahia  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
SAIDA_PADRAO = RAIZ / "docs" / "dados" / "auditoria_conferencias.json"
ABA_AUDITORIA = "AUDITORIA_CONFERENCIAS"

VALORES_VALIDOS = {
    "",
    "correto",
    "errado",
    "true",
    "false",
    "sim",
    "nao",
    "não",
}


def carregar_config(caminho: Path) -> dict[str, Any]:
    with caminho.open("r", encoding="utf-8") as f:
        return json.load(f)


def cel(linha: list[Any], col_1based: int) -> str:
    idx = col_1based - 1
    return str(linha[idx] or "").strip() if len(linha) > idx else ""


def norm_veredito(valor: Any) -> str | None:
    s = str(valor or "").strip()
    if not s:
        return None
    return "Correto" if s.casefold() == "correto" else "Errado"


def valor_invalido(valor: Any) -> bool:
    return pl.normalizar_cabecalho(valor) not in VALORES_VALIDOS


def auditar(valores: list[list[Any]]) -> tuple[dict[str, Any], list[list[Any]]]:
    cab = valores[0] if valores else []
    col_c = pl.localizar_coluna(cab, ("CATEGORIA COMPLETA",), 3)
    col_g = pl.localizar_coluna(cab, ("Classificacao IA", "Classificação IA"), 7)
    col_o = pl.localizar_coluna(cab, ("Classificacao IA - 2", "Classificação IA - 2"), 15)
    col_m = pl.localizar_coluna(cab, ("CONFERENCIA GLPI", "CONFERÊNCIA GLPI"), 13)
    col_n = pl.localizar_coluna(cab, ("CONFERENCIA IA", "CONFERÊNCIA IA"), 14)
    col_p = pl.localizar_coluna(cab, ("CONFERENCIA IA - 2", "CONFERÊNCIA IA - 2"), 16)

    cont = Counter()
    linhas_privadas: list[list[Any]] = []
    for pos, linha in enumerate(valores[1:], start=2):
        historico = cel(linha, col_c)
        ia1 = cel(linha, col_g)
        reclass = cel(linha, col_o)
        raw_m, raw_n, raw_p = cel(linha, col_m), cel(linha, col_n), cel(linha, col_p)
        v_m, v_n, v_p = norm_veredito(raw_m), norm_veredito(raw_n), norm_veredito(raw_p)
        tem_conf = any(v is not None for v in (v_m, v_n, v_p))
        if tem_conf:
            cont["total_com_alguma_conferencia"] += 1
            decisao = dv.decidir(historico, ia1, reclass, v_m, v_n, v_p)
            if decisao["status"] == dv.STATUS_DECIDIDO:
                cont["decisoes_travadas"] += 1
            if decisao["status"] == dv.STATUS_RESTRITO:
                cont["restritos"] += 1
            if decisao.get("conflito"):
                cont["conflitos"] += 1
        problemas: list[str] = []
        if v_m == "Correto" and v_n == "Correto" and historico and ia1 and historico != ia1:
            cont["m_correto_n_correto_com_c_diferente_g"] += 1
            problemas.append("M=Correto e N=Correto com C diferente de G")
        if v_p == "Correto" and reclass and (
            (v_m == "Correto" and historico and reclass != historico)
            or (v_n == "Correto" and ia1 and reclass != ia1)
        ):
            cont["p_correto_conflitando_com_c_ou_g"] += 1
            problemas.append("P=Correto conflita com conferencia de C ou G")
        if reclass and v_p is None:
            cont["o_preenchida_p_vazia"] += 1
            problemas.append("O preenchida e P vazia")
        if reclass and v_m is None and v_n is None:
            cont["m_n_vazias_o_preenchida"] += 1
            problemas.append("M/N vazias e O preenchida")
        invalidos = [nome for nome, bruto in (("M", raw_m), ("N", raw_n), ("P", raw_p))
                     if valor_invalido(bruto)]
        if invalidos:
            cont["valores_invalidos_m_n_p"] += 1
            problemas.append("Valor invalido em " + "/".join(invalidos))
        if problemas:
            linhas_privadas.append([pos, "; ".join(problemas), bool(tem_conf)])

    resumo = {
        "gerado_em": agora_bahia(),
        "natureza": "auditoria operacional das conferencias M/N/P; sem texto de chamado e sem ID de chamado",
        "colunas_usadas": {"historico": col_c, "ia": col_g, "reclassificacao": col_o,
                           "conferencia_glpi": col_m, "conferencia_ia": col_n,
                           "conferencia_ia_2": col_p},
        "contagens": dict(cont),
        "linhas_com_problema": len(linhas_privadas),
    }
    return resumo, linhas_privadas


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Audita conferencias humanas M/N/P.")
    p.add_argument("--config", type=Path, default=CONFIG_PADRAO)
    p.add_argument("--credenciais", default=None)
    p.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    p.add_argument("--aplicar", action="store_true", help="Grava aba privada AUDITORIA_CONFERENCIAS.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    config = carregar_config(args.config)
    try:
        sh = pl.abrir_planilha(pl.id_planilha(config), args.credenciais)
        ws = sh.worksheet(config["aba_principal"])
        valores = pl.ler_valores(ws, "A:P")
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001
        print(f"Falha ao acessar planilha: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    resumo, linhas_privadas = auditar(valores)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(resumo, ensure_ascii=False, indent=2))
    if args.aplicar:
        pl.escrever_aba(
            sh,
            ABA_AUDITORIA,
            ["linha_planilha", "problemas", "tem_alguma_conferencia"],
            linhas_privadas,
        )
        print(f"OK: aba {ABA_AUDITORIA} gravada com {len(linhas_privadas)} linhas.")
    else:
        print("modo=dry-run (aba privada nao gravada).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
