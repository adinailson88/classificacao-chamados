#!/usr/bin/env python3
"""Teste de viabilidade da cascata modelo + LLM (Trilha B).

Le o snapshot do corte B na planilha privada, seleciona os chamados listados em
``docs/dados/trilha_b/cascata_amostra.json`` (apenas hashes de id), mascara dados
pessoais e pede a um LLM do GitHub Models que escolha uma das categorias da
referencia. Grava somente agregados e a categoria prevista por hash de id; texto
de chamado nunca vai para arquivo versionado nem para o log.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import corte_b as cb  # noqa: E402
import conferencia_derivada as cd  # noqa: E402
import planilha as pl  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / "docs" / "dados" / "trilha_b"
AMOSTRA = DADOS / "cascata_amostra.json"
SAIDA = DADOS / "cascata_llm.json"
URL_MODELOS = "https://models.github.ai/inference/chat/completions"
MODELO_PADRAO = "openai/gpt-4.1-mini"
LIMITE_TEXTO = 700

_PADROES = [
    (re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+"), "[email]"),
    (re.compile(r"https?://\S+|www\.\S+"), "[url]"),
    (re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}"), "[doc]"),
    (re.compile(r"\(?\d{2}\)?[\s.-]?9?\d{4}[\s.-]?\d{4}"), "[telefone]"),
    (re.compile(r"\d{5,}"), "[numero]"),
]


def mascarar(texto: str) -> str:
    for padrao, subst in _PADROES:
        texto = padrao.sub(subst, texto)
    return re.sub(r"\s+", " ", texto).strip()


def texto_do_chamado(linha: dict[str, str]) -> str:
    partes = [linha.get("titulo", ""), linha.get("descricao_glpi", "")]
    return mascarar(" | ".join(p for p in partes if p.strip()))[:LIMITE_TEXTO]


def montar_prompt(texto: str, categorias: list[str]) -> list[dict[str, str]]:
    lista = "\n".join(f"- {c}" for c in categorias)
    return [
        {"role": "system", "content": (
            "Voce classifica chamados de manutencao predial de uma universidade federal "
            "brasileira. Escolha exatamente uma categoria da lista e responda apenas com "
            'JSON no formato {"categoria": "<texto identico ao da lista>"}.\n\nCategorias:\n'
            + lista)},
        {"role": "user", "content": texto},
    ]


def interpretar_resposta(resposta: str, categorias: list[str]) -> str | None:
    m = re.search(r"\{.*\}", resposta, flags=re.S)
    if not m:
        return None
    try:
        cat = json.loads(m.group(0)).get("categoria")
    except (json.JSONDecodeError, AttributeError):
        return None
    return cat if cat in categorias else None


def resumir(itens: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(itens)
    validos = [i for i in itens if i["llm"] is not None]
    llm_ok = sum(i["llm"] == i["referencia_humana"] for i in validos)
    modelo_ok = sum(i["previsto"] == i["referencia_humana"] for i in itens)
    so_llm = sum(i["llm"] == i["referencia_humana"] and i["previsto"] != i["referencia_humana"]
                 for i in validos)
    so_modelo = sum(i["previsto"] == i["referencia_humana"] and i["llm"] != i["referencia_humana"]
                    for i in itens)
    return {"n": n, "respostas_validas": len(validos),
            "acuracia_modelo": round(modelo_ok / n, 4),
            "acuracia_llm_sobre_n": round(llm_ok / n, 4),
            "llm_acerta_e_modelo_erra": so_llm, "modelo_acerta_e_llm_erra": so_modelo,
            "concordancia_llm_modelo": round(
                sum(i["llm"] == i["previsto"] for i in validos) / max(1, len(validos)), 4)}


def chamar(token: str, modelo: str, mensagens: list[dict[str, str]]) -> str:
    corpo = json.dumps({"model": modelo, "messages": mensagens, "max_tokens": 80,
                        "temperature": 0}).encode("utf-8")
    for tentativa in range(6):
        req = urllib.request.Request(URL_MODELOS, data=corpo, headers={
            "Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and tentativa < 5:
                time.sleep(min(60, 5 * 2 ** tentativa))
                continue
            raise RuntimeError(f"GitHub Models devolveu HTTP {e.code}") from None
    raise RuntimeError("sem resposta do GitHub Models")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--credenciais", default=None)
    p.add_argument("--modelo", default=MODELO_PADRAO)
    p.add_argument("--limite", type=int, default=0, help="processa so os N primeiros (0 = todos)")
    args = p.parse_args()
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("GITHUB_TOKEN ausente.", file=sys.stderr)
        return 1
    amostra = json.loads(AMOSTRA.read_text(encoding="utf-8"))
    manifesto = json.loads(cb.SAIDA_JSON_PADRAO.read_text(encoding="utf-8"))
    config = json.loads(args.config.read_text(encoding="utf-8"))
    sh = pl.abrir_planilha(pl.id_planilha(config), args.credenciais)
    valores = sh.worksheet(manifesto["aba_snapshot"]).get_all_values()
    cab = valores[0]
    if cab != cb.CABECALHO_SNAPSHOT:
        raise RuntimeError("Cabecalho inesperado no snapshot.")
    por_hash = {}
    for v in valores[1:]:
        if any(str(c).strip() for c in v):
            d = dict(zip(cab, list(v) + [""] * (len(cab) - len(v))))
            d["id_chamado"] = cd.normalizar_id(d["id_chamado"])
            por_hash[hashlib.sha256(d["id_chamado"].encode("utf-8")).hexdigest()] = d
    itens_in = amostra["itens"][: args.limite or None]
    faltando = [i["id_sha256"] for i in itens_in if i["id_sha256"] not in por_hash]
    if faltando:
        raise RuntimeError(f"{len(faltando)} ids da amostra ausentes do snapshot.")
    cats = amostra["categorias"]
    itens = []
    for k, it in enumerate(itens_in, 1):
        texto = texto_do_chamado(por_hash[it["id_sha256"]])
        bruta = chamar(token, args.modelo, montar_prompt(texto, cats))
        itens.append({"id_sha256": it["id_sha256"], "previsto": it["previsto"],
                      "referencia_humana": it["referencia_humana"],
                      "llm": interpretar_resposta(bruta, cats)})
        if k % 50 == 0:
            print(f"{k}/{len(itens_in)}", flush=True)
        time.sleep(1.0)
    saida = {"protocolo": amostra["protocolo"], "modelo_llm": args.modelo,
             "texto_enviado": "titulo e descricao GLPI mascarados (e-mail, url, documento, "
                              f"telefone, numeros longos), ate {LIMITE_TEXTO} caracteres",
             "resumo": resumir(itens), "itens": itens}
    SAIDA.write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(saida["resumo"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
