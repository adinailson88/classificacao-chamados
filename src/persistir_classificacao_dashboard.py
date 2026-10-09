#!/usr/bin/env python3
"""Publica os artefatos sanitizados dos modelos com concorrencia segura.

Cada tentativa parte do ``origin/main`` mais recente em um worktree temporario.
Somente ``registros_<modelo>.json`` e a auditoria podem ser alterados. Em caso
de push concorrente, a tentativa inteira e refeita sobre o novo HEAD remoto.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from exportar_dashboard import carregar_registros_modelos_de_artefatos


RAIZ = Path(__file__).resolve().parents[1]
REJEICOES = ("[rejected]", "non-fast-forward", "fetch first", "stale info")


class PushConcorrente(RuntimeError):
    pass


def _git(args: list[str], cwd: Path, permitir_rejeicao: bool = False) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        saida = f"{r.stdout}\n{r.stderr}".strip()
        if permitir_rejeicao and any(x in saida.lower() for x in REJEICOES):
            raise PushConcorrente(saida)
        raise RuntimeError(f"git {' '.join(args)} falhou: {saida}")
    return r.stdout.strip()


def nomes_permitidos(config: dict) -> list[str]:
    mm = config.get("multimodelo", {}) or {}
    modelos = list(mm.get("modelos_leves", [])) + list(mm.get("modelos_pesados", []))
    if not modelos or any(not re.fullmatch(r"[a-z0-9_]+", str(m)) for m in modelos):
        raise ValueError("lista de modelos ausente ou invalida")
    return ["registros_modelos_auditoria.json", *(f"registros_{m}.json" for m in modelos)]


def _uma_tentativa(config: dict, origem: Path, remote: str, branch: str, cwd: Path) -> str:
    _git(["fetch", remote, branch], cwd)
    sha = _git(["rev-parse", "FETCH_HEAD"], cwd)
    tmp = Path(tempfile.mkdtemp(prefix="publicar-classificacao-"))
    try:
        _git(["worktree", "add", "--detach", str(tmp), sha], cwd)
        destino = tmp / "docs" / "dados"
        destino.mkdir(parents=True, exist_ok=True)
        for nome in nomes_permitidos(config):
            fonte = origem / nome
            alvo = destino / nome
            if fonte.is_file():
                shutil.copyfile(fonte, alvo)
            elif nome.startswith("registros_") and nome != "registros_modelos_auditoria.json":
                alvo.unlink(missing_ok=True)
            else:
                raise FileNotFoundError(f"artefato obrigatorio ausente: {nome}")

        mm = config.get("multimodelo", {}) or {}
        modelos = list(mm.get("modelos_leves", [])) + list(mm.get("modelos_pesados", []))
        carregar_registros_modelos_de_artefatos(destino, modelos)
        paths = [f"docs/dados/{nome}" for nome in nomes_permitidos(config)]
        # Worktree novo e limpo: o staging do diretorio captura tambem a remocao
        # intencional de um JSON obsoleto. A allowlist abaixo falha fechado antes
        # do commit caso qualquer outro path apareca.
        _git(["add", "-A", "--", "docs/dados"], tmp)
        if not _git(["diff", "--cached", "--name-only"], tmp):
            return "no-op"
        alterados = set(_git(["diff", "--cached", "--name-only"], tmp).splitlines())
        if not alterados.issubset(set(paths)):
            raise RuntimeError(f"staging fora da allowlist: {sorted(alterados - set(paths))}")
        _git(["config", "user.name", "github-actions[bot]"], tmp)
        _git(["config", "user.email", "github-actions[bot]@users.noreply.github.com"], tmp)
        _git(["commit", "-m", "classificacao do dashboard [skip ci]"], tmp)
        _git(["push", remote, f"HEAD:{branch}"], tmp, permitir_rejeicao=True)
        return _git(["rev-parse", "HEAD"], tmp)
    finally:
        try:
            _git(["worktree", "remove", "--force", str(tmp)], cwd)
        except Exception:  # noqa: BLE001
            shutil.rmtree(tmp, ignore_errors=True)
            subprocess.run(["git", "worktree", "prune"], cwd=cwd, capture_output=True)


def persistir(config: dict, origem: Path, remote: str, branch: str,
              cwd: Path, max_tentativas: int) -> str:
    ultimo = None
    for _ in range(max_tentativas):
        try:
            return _uma_tentativa(config, origem, remote, branch, cwd)
        except PushConcorrente as e:
            ultimo = e
    raise RuntimeError(f"push falhou apos {max_tentativas} tentativas: {ultimo}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Persiste a classificacao sanitizada.")
    p.add_argument("--config", type=Path, default=RAIZ / "config_experimento.json")
    p.add_argument("--origem", type=Path, default=RAIZ / "docs" / "dados")
    p.add_argument("--remote", default="origin")
    p.add_argument("--branch", default="main")
    p.add_argument("--max-tentativas", type=int, default=5)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    resultado = persistir(config, args.origem, args.remote, args.branch,
                          Path.cwd(), args.max_tentativas)
    print(f"classificacao_dashboard_publicada={resultado}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
