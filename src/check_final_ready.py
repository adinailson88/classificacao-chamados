#!/usr/bin/env python3
"""Verificador tecnico final do repositorio.

Nao acessa a planilha e nao le texto de chamado. Confere arquivos essenciais,
compilacao dos scripts e JSONs publicos agregados para responder se o gargalo
restante e validacao humana ou problema tecnico real.
"""

from __future__ import annotations

import json
import py_compile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

ESSENCIAIS = [
    "config_experimento.json",
    "src/planilha.py",
    "src/decisao_validada.py",
    "src/avaliacao_final.py",
    "src/reclassificacao_multimodelo.py",
    "src/reclassificar_validados.py",
    "src/auditar_conferencias.py",
    ".github/workflows/auditar_conferencias.yml",
    ".github/workflows/check_final_ready.yml",
]

JSONS_PUBLICOS = [
    "docs/dados/avaliacao_final.json",
    "docs/dados/reclass_resumo.json",
    "docs/dados/estatistica.json",
    "docs/dados/calibracao_modelos.json",
    "docs/dados/calibracao_ajustada_modelos.json",
]


def ler_json(rel: str) -> dict:
    with (RAIZ / rel).open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    problemas: list[str] = []
    print("== Arquivos essenciais ==")
    for rel in ESSENCIAIS:
        ok = (RAIZ / rel).exists()
        print(f"{'OK' if ok else 'FALTA'} {rel}")
        if not ok:
            problemas.append(f"arquivo essencial ausente: {rel}")

    print("\n== Compilacao Python ==")
    for arq in sorted((RAIZ / "src").glob("*.py")):
        try:
            py_compile.compile(str(arq), doraise=True)
            print(f"OK {arq.relative_to(RAIZ)}")
        except py_compile.PyCompileError as e:
            print(f"ERRO {arq.relative_to(RAIZ)}: {e.msg}")
            problemas.append(f"falha de compilacao: {arq.relative_to(RAIZ)}")

    print("\n== JSONs publicos ==")
    dados: dict[str, dict] = {}
    for rel in JSONS_PUBLICOS:
        caminho = RAIZ / rel
        if not caminho.exists():
            print(f"FALTA {rel}")
            problemas.append(f"json publico ausente: {rel}")
            continue
        try:
            dados[rel] = ler_json(rel)
            print(f"OK {rel}")
        except json.JSONDecodeError as e:
            print(f"ERRO {rel}: JSON invalido ({e})")
            problemas.append(f"json invalido: {rel}")

    avaliacao = dados.get("docs/dados/avaliacao_final.json") or {}
    reclass = dados.get("docs/dados/reclass_resumo.json") or {}

    print("\n== Avaliacao final ==")
    conferencias = avaliacao.get("conferencias") or {}
    print(f"status={avaliacao.get('status', 'ausente')}")
    print(f"validados={avaliacao.get('validados', 0)}")
    print(f"conflitos={conferencias.get('conflitos', 0)}")
    print(f"melhor_ia={avaliacao.get('melhor_ia', '')}")

    print("\n== Reclassificacao ==")
    modelos = [m.get("modelo") for m in reclass.get("por_modelo", []) if m.get("modelo")]
    print(f"modelos={', '.join(modelos) if modelos else 'nenhum'}")
    if not modelos:
        problemas.append("reclass_resumo.json sem modelos")

    status = avaliacao.get("status")
    if problemas:
        print("\nstatus=problema_tecnico")
        for p in problemas:
            print(f"- {p}")
        return 1
    if status == "aguardando_validacao":
        print("\nstatus=aguardando_validacao")
        print("Repositorio tecnicamente pronto; gargalo restante: conferencia humana.")
        return 0
    if status == "ok":
        print("\nstatus=ok")
        print("Repositorio tecnicamente pronto; avaliacao validada disponivel.")
        return 0
    print("\nstatus=problema_tecnico")
    print("- avaliacao_final.json sem status reconhecido")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
