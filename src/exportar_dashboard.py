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
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planilha as pl  # noqa: E402
from tempo import agora_bahia  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
SAIDA = RAIZ / "docs" / "dados"

# (chave_json, chave_no_config_abas)
# NÃO exportar EXPERIMENTO_CONFIG: contém spreadsheet_id e outros identificadores
# (repo público). O dashboard não usa essa aba; só agregados sem dado sensível.
ABAS = [
    ("log_turnos_classificacao", "log_turnos_classificacao"),
    ("metricas_por_categoria", "metricas_por_categoria"),
    ("log_turnos_reclassificacao", "log_turnos_reclassificacao"),
    ("metricas_experimento", "metricas"),
    ("comparacao_modelos", "comparacao_modelos"),
    ("comparacao_categoria", "comparacao_categoria"),
]

# Abas multimodelo: AGREGADAS, sem texto de chamado (seguras p/ repo publico).
# Nomes literais (config["multimodelo"]) + a aba derivada de reclassificacao.
# NAO exportar COMPARACAO_PREVISOES nem CLASSIF__*/RECLASS__* crus: contem titulo
# do chamado (texto). Se o painel precisar, exportar um agregado SEM texto.
def _abas_multimodelo(config):
    mm = config.get("multimodelo", {}) or {}
    if not mm:
        return []
    turnos = mm.get("aba_turnos", "MULTIMODELO_TURNOS")
    return [
        ("multimodelo_turnos", turnos),
        ("multimodelo_metricas", mm.get("aba_metricas", "MULTIMODELO_METRICAS")),
        ("multimodelo_reclass_turnos", turnos.replace("TURNOS", "RECLASS_TURNOS")),
    ]


def _erro_transitorio(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(t in msg for t in ("429", "quota exceeded", "rate limit", "temporarily unavailable"))


def com_retentativa(rotulo, func, tentativas=5, espera_inicial=20):
    for tentativa in range(1, tentativas + 1):
        try:
            return func()
        except Exception as e:  # noqa: BLE001
            if tentativa >= tentativas or not _erro_transitorio(e):
                raise
            espera = espera_inicial * tentativa
            print(f"{rotulo}: falha transitoria ({type(e).__name__}); nova tentativa em {espera}s", file=sys.stderr)
            time.sleep(espera)


def aba_para_objetos(sh, nome):
    """Lê a aba (sem formatação) e retorna lista de dicts {cabecalho: valor}."""
    try:
        vals = com_retentativa(
            f"ler aba {nome}",
            lambda: sh.worksheet(nome).get_values("A:Z", value_render_option="UNFORMATTED_VALUE"),
        )
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
        sh = com_retentativa("abrir planilha", lambda: pl.abrir_planilha(pl.id_planilha(config)))
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr); return 2
    except Exception as e:  # noqa: BLE001
        print(f"Falha ao acessar a planilha: {type(e).__name__}: {e}", file=sys.stderr); return 1

    resumo = {"gerado_em": agora_bahia(),
              "run_id": config.get("run_id", ""), "abas": {}}
    for chave_json, chave_cfg in ABAS:
        nome = abas_cfg.get(chave_cfg)
        dados = aba_para_objetos(sh, nome) if nome else []
        (SAIDA / f"{chave_json}.json").write_text(
            json.dumps(dados, ensure_ascii=False), encoding="utf-8")
        resumo["abas"][chave_json] = len(dados)
        print(f"{chave_json}: {len(dados)} linhas")

    # Abas multimodelo (nome literal). Exporta [] quando ainda nao materializado.
    for chave_json, nome_aba in _abas_multimodelo(config):
        dados = aba_para_objetos(sh, nome_aba) if nome_aba else []
        (SAIDA / f"{chave_json}.json").write_text(
            json.dumps(dados, ensure_ascii=False), encoding="utf-8")
        resumo["abas"][chave_json] = len(dados)
        print(f"{chave_json}: {len(dados)} linhas")

    # Calibração (confiança × acerto) — critério central do objetivo final.
    try:
        import calibracao
        cal = calibracao.calcular(sh, config)
        (SAIDA / "calibracao.json").write_text(json.dumps(cal, ensure_ascii=False), encoding="utf-8")
        resumo["calibracao"] = {"total": cal.get("total", 0), "ece_historico": cal.get("ece_historico"),
                                "validados": cal.get("validados", 0)}
        print(f"calibracao: total={cal.get('total')} ECE={cal.get('ece_historico')} validados={cal.get('validados')}")
    except Exception as e:  # noqa: BLE001
        print(f"calibracao falhou: {type(e).__name__}: {e}", file=sys.stderr)

    # Registros por chamado (SEM texto de chamado) para os filtros do painel.
    try:
        snap = com_retentativa(
            "ler snapshot",
            lambda: sh.worksheet(abas_cfg["snapshot_etapa_1"]).get_values(
                "A:J", value_render_option="UNFORMATTED_VALUE"),
        )
    except Exception:  # noqa: BLE001
        snap = []
    valida = {}
    try:
        vv = sh.worksheet(abas_cfg["validacao_humana"]).get_all_values()
        if len(vv) > 1:
            cabv = {(" ".join(str(c).split()).casefold()): i for i, c in enumerate(vv[0])}
            iln, idec = cabv.get("linha_planilha"), cabv.get("decisao")
            if iln is not None and idec is not None:
                for rr in vv[1:]:
                    ln = str(rr[iln]).strip() if iln < len(rr) else ""
                    dec = str(rr[idec]).strip() if idec < len(rr) else ""
                    if ln and dec:
                        valida[ln] = dec
    except Exception:  # noqa: BLE001
        pass

    def _conf(x):
        try:
            f = float(str(x).replace("%", "").replace(",", ".").strip())
            return f / 100.0 if f > 1 else f
        except (ValueError, TypeError):
            return 0.0

    regs = []
    for rr in snap[1:]:
        if len(rr) < 6:
            continue
        ln = str(rr[1]).strip()
        orig = str(rr[3]).strip()
        cia = str(rr[4]).strip()
        if not cia:
            continue
        c = _conf(rr[5])
        ex = str(rr[6]).strip() if len(rr) > 6 else ""
        fa = "acima_95" if c >= 0.95 else ("entre_70_95" if c >= 0.70 else "abaixo_70")
        regs.append({"l": ln, "g": (orig.split(" > ")[0].strip() if orig else "(sem)"),
                     "o": orig, "p": cia, "c": round(c, 4), "f": fa, "e": ex,
                     "k": 1 if cia == orig else 0, "v": valida.get(ln, "")})
    (SAIDA / "registros.json").write_text(json.dumps(regs, ensure_ascii=False), encoding="utf-8")
    resumo["registros"] = len(regs)
    print(f"registros={len(regs)}")

    # Registros POR MODELO (multimodelo) — 1 IA por vez, MESMO schema de registros.json,
    # SEM texto/ID de chamado. Permite ao painel trocar a aba Classificacao por modelo
    # (out-of-fold). NÃO concatena modelos (evita o antigo 13.825 x 7 = 96.775).
    # CLASSIF__<modelo>: 1 linha_planilha, 3 cat_original, 4 cat_ia, 5 confianca, 7 executor.
    mm = config.get("multimodelo", {}) or {}
    modelos_mm = list(mm.get("modelos_leves", [])) + list(mm.get("modelos_pesados", []))
    padrao = mm.get("aba_classificacao", "CLASSIF__{modelo}")
    registros_modelos = {}
    for modelo in modelos_mm:
        nome_aba = padrao.replace("{modelo}", modelo)
        try:
            vals = com_retentativa(
                f"ler {nome_aba}",
                lambda na=nome_aba: sh.worksheet(na).get_values(
                    "A:K", value_render_option="UNFORMATTED_VALUE"))
        except Exception:  # noqa: BLE001
            vals = []
        rm = []
        for rr in vals[1:]:
            if len(rr) < 6:
                continue
            ln = str(rr[1]).strip()
            orig = str(rr[3]).strip()
            cia = str(rr[4]).strip()
            if not cia:
                continue
            c = _conf(rr[5])
            ex = str(rr[7]).strip() if len(rr) > 7 else modelo
            fa = "acima_95" if c >= 0.95 else ("entre_70_95" if c >= 0.70 else "abaixo_70")
            rm.append({"l": ln, "g": (orig.split(" > ")[0].strip() if orig else "(sem)"),
                       "o": orig, "p": cia, "c": round(c, 4), "f": fa, "e": ex or modelo,
                       "k": 1 if cia == orig else 0, "v": valida.get(ln, "")})
        if rm:
            (SAIDA / f"registros_{modelo}.json").write_text(
                json.dumps(rm, ensure_ascii=False), encoding="utf-8")
            registros_modelos[modelo] = len(rm)
            print(f"registros_{modelo}={len(rm)}")
    resumo["registros_modelos"] = registros_modelos

    # Diagnostico de calibracao por IA, usando somente os registros agregados
    # exportados acima. Nao ajusta calibrador nem usa texto de chamado.
    try:
        import calibracao_modelos
        cal_models = calibracao_modelos.calcular_de_arquivos(SAIDA, list(registros_modelos.keys()))
        (SAIDA / "calibracao_modelos.json").write_text(
            json.dumps(cal_models, ensure_ascii=False, indent=2), encoding="utf-8")
        resumo["calibracao_modelos"] = {
            "modelos": len(cal_models.get("modelos", [])),
            "melhor_ece": cal_models.get("melhor_ece", ""),
            "melhor_faixa_95": cal_models.get("melhor_faixa_95", ""),
            "calibrador_ajustado": cal_models.get("calibrador_ajustado", False),
        }
        print(f"calibracao_modelos={len(cal_models.get('modelos', []))}")
    except Exception as e:  # noqa: BLE001
        print(f"calibracao_modelos falhou: {type(e).__name__}: {e}", file=sys.stderr)

    # Calibracao escalar preliminar: confianca bruta -> probabilidade empirica
    # de acerto contra historico. Usa somente registros_<modelo>.json, sem texto.
    try:
        import calibracao_confianca
        cal_ajustada = calibracao_confianca.calcular_de_arquivos(SAIDA, list(registros_modelos.keys()))
        (SAIDA / "calibracao_ajustada_modelos.json").write_text(
            json.dumps(cal_ajustada, ensure_ascii=False, indent=2), encoding="utf-8")
        resumo["calibracao_ajustada_modelos"] = {
            "modelos": len(cal_ajustada.get("modelos", [])),
            "melhor_ece_ajustado": cal_ajustada.get("melhor_ece_ajustado", ""),
            "alvo": cal_ajustada.get("alvo", ""),
        }
        print(f"calibracao_ajustada_modelos={len(cal_ajustada.get('modelos', []))}")
    except Exception as e:  # noqa: BLE001
        print(f"calibracao_ajustada_modelos falhou: {type(e).__name__}: {e}", file=sys.stderr)

    (SAIDA / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"gerado_em={resumo['gerado_em']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
