#!/usr/bin/env python3
"""Exporta os dados AGREGADOS das abas para JSON, alimentando o dashboard HTML.

Lê (via conta de serviço) as abas de métricas/logs agregados — que NÃO contêm
texto de chamado, apenas categorias, contagens e percentuais — e grava um JSON por
aba em docs/dados/. O dashboard estático (docs/index.html) consome esses JSON.

Abas exportadas: LOG_TURNOS_CLASSIFICACAO, METRICAS_POR_CATEGORIA,
LOG_TURNOS_RECLASSIFICACAO, METRICAS_EXPERIMENTO, EXPERIMENTO_CONFIG.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planilha as pl  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
SAIDA = RAIZ / "docs" / "dados"
FUSO_BAHIA = timezone(timedelta(hours=-3))

# (chave_json, chave_no_config_abas)
# NÃO exportar EXPERIMENTO_CONFIG: contém spreadsheet_id e outros identificadores
# (repo público). O dashboard não usa essa aba; só agregados sem dado sensível.
ABAS = [
    ("log_turnos_classificacao", "log_turnos_classificacao"),
    ("metricas_por_categoria", "metricas_por_categoria"),
    ("log_turnos_reclassificacao", "log_turnos_reclassificacao"),
    ("metricas_experimento", "metricas"),
]


def aba_para_objetos(sh, nome):
    """Lê a aba (sem formatação) e retorna lista de dicts {cabecalho: valor}."""
    try:
        vals = sh.worksheet(nome).get_values("A:Z", value_render_option="UNFORMATTED_VALUE")
    except Exception:  # noqa: BLE001
        return []
    if len(vals) < 2:
        return []
    cab = [str(c).strip() for c in vals[0]]
    out = []
    for r in vals[1:]:
        if not any(str(c).strip() for c in r):
            continue
        out.append({cab[i]: (r[i] if i < len(r) else "") for i in range(len(cab))})
    return out


def main() -> int:
    with CONFIG_PADRAO.open(encoding="utf-8") as f:
        config = json.load(f)
    abas_cfg = config["abas_experimento"]
    SAIDA.mkdir(parents=True, exist_ok=True)

    try:
        sh = pl.abrir_planilha(config["spreadsheet_id"])
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr); return 2
    except Exception as e:  # noqa: BLE001
        print(f"Falha ao acessar a planilha: {type(e).__name__}: {e}", file=sys.stderr); return 1

    resumo = {"gerado_em": datetime.now(FUSO_BAHIA).strftime("%Y-%m-%dT%H:%M:%S-03:00"),
              "run_id": config.get("run_id", ""), "abas": {}}
    for chave_json, chave_cfg in ABAS:
        nome = abas_cfg.get(chave_cfg)
        dados = aba_para_objetos(sh, nome) if nome else []
        (SAIDA / f"{chave_json}.json").write_text(
            json.dumps(dados, ensure_ascii=False), encoding="utf-8")
        resumo["abas"][chave_json] = len(dados)
        print(f"{chave_json}: {len(dados)} linhas")

    (SAIDA / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"gerado_em={resumo['gerado_em']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
