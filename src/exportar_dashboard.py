#!/usr/bin/env python3
"""Exporta os dados AGREGADOS das abas para JSON, alimentando o dashboard HTML.

Lê (via conta de serviço) as abas de métricas/logs agregados — que NÃO contêm
texto de chamado, apenas categorias, contagens e percentuais — e grava um JSON por
aba em docs/dados/. O dashboard estático (docs/index.html) consome esses JSON.

Abas exportadas: LOG_TURNOS_CLASSIFICACAO, METRICAS_POR_CATEGORIA,
LOG_TURNOS_RECLASSIFICACAO, METRICAS_EXPERIMENTO, EXPERIMENTO_CONFIG.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planilha as pl  # noqa: E402
from tempo import agora_bahia  # noqa: E402
from tipo_manutencao import tipo_manutencao  # noqa: E402,F401

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_PADRAO = RAIZ / "config_experimento.json"
SAIDA = RAIZ / "docs" / "dados"
CHAVES_REGISTRO_MODELO = {"l", "g", "m", "o", "p", "c", "f", "e", "k", "v"}

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
# do chamado (texto). COMPARACAO_PREVISOES sai apenas em versao sanitizada.
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


def sanitizar_comparacao_previsoes(rows):
    """Remove ID, titulo e observacao livre antes de publicar no GitHub Pages."""
    seguros = []
    for r in rows:
        if not r:
            continue
        seguros.append({
            "modelo": r.get("modelo", ""),
            "linha_planilha": r.get("linha_planilha", ""),
            "categoria_original": r.get("categoria_original", ""),
            "categoria_prevista": r.get("categoria_prevista", ""),
            "score": r.get("score", ""),
            "divergencia": r.get("divergencia", ""),
            "enviado_revisao": r.get("enviado_revisao", ""),
            "executado_em": r.get("executado_em", ""),
            "validacao_humana_final": r.get("validacao_humana_final", ""),
            "quem_estava_correto": r.get("quem_estava_correto", ""),
            "data_validacao": r.get("data_validacao", ""),
        })
    return seguros


def normalizar_id(valor) -> str:
    """Normaliza IDs numericos do Sheets sem depender da representacao 1693/1693.0."""
    texto = str(valor or "").strip()
    if not texto:
        return ""
    try:
        return str(int(float(texto)))
    except (TypeError, ValueError):
        return texto


def normalizar_confianca(valor) -> float:
    try:
        numero = float(str(valor).replace("%", "").replace(",", ".").strip())
        return numero / 100.0 if numero > 1 else numero
    except (ValueError, TypeError):
        return 0.0


def deduplicar_registros_modelo(vals, ids_atuais, linha_atual_por_id, valida, modelo):
    """Produz registros publicos com uma previsao por ID, mantendo a ultima.

    O ID real existe apenas como chave temporaria. O retorno publico nao o contem.
    ``linha_planilha`` e atualizada pelo mapa da aba principal e nunca e usada
    como identidade, pois pode mudar quando a base cresce ou e reordenada.
    """
    if not ids_atuais:
        raise RuntimeError("IDs atuais indisponiveis; publicacao por modelo bloqueada")

    por_id = {}
    brutos = invalidos = 0
    for rr in vals[1:]:
        if len(rr) < 6:
            continue
        cia = str(rr[4] or "").strip()
        if not cia:
            continue
        brutos += 1
        idc = normalizar_id(rr[2] if len(rr) > 2 else "")
        if not idc or not idc.isdigit() or int(idc) <= 0:
            invalidos += 1
            continue
        por_id[idc] = rr

    if invalidos:
        raise ValueError(f"{modelo}: {invalidos} previsao(oes) com ID vazio/invalido")

    fora_base = sum(1 for idc in por_id if idc not in ids_atuais)
    rm = []
    for idc, rr in sorted(
        por_id.items(), key=lambda item: linha_atual_por_id.get(item[0], 10**12)
    ):
        if idc not in ids_atuais:
            continue
        ln = str(linha_atual_por_id[idc])
        orig = str(rr[3] or "").strip()
        cia = str(rr[4] or "").strip()
        conf = normalizar_confianca(rr[5])
        ex = str(rr[7] or "").strip() if len(rr) > 7 else modelo
        faixa = "acima_95" if conf >= 0.95 else ("entre_70_95" if conf >= 0.70 else "abaixo_70")
        rm.append({
            "l": ln,
            "g": orig.split(" > ")[0].strip() if orig else "(sem)",
            "m": tipo_manutencao(orig),
            "o": orig,
            "p": cia,
            "c": round(conf, 4),
            "f": faixa,
            "e": ex or modelo,
            "k": 1 if cia == orig else 0,
            "v": valida.get(ln, ""),
        })

    if len(rm) > len(ids_atuais):
        raise RuntimeError(f"{modelo}: registros finais excedem os IDs atuais")
    auditoria = {
        "modelo": modelo,
        "registros_brutos": brutos,
        "ids_unicos_origem": len(por_id),
        "duplicados_descartados": brutos - len(por_id),
        "ids_fora_base_descartados": fora_base,
        "ids_invalidos": invalidos,
        "ids_esperados": len(ids_atuais),
        "ids_unicos": len(rm),
        "status": ("ausente" if not rm else
                   "valido_completo" if len(rm) == len(ids_atuais) else "parcial"),
    }
    return rm, auditoria


def carregar_registros_modelos_de_artefatos(saida: Path, modelos: list[str]):
    """Valida e reutiliza os JSONs sanitizados, sem consultar CLASSIF__*."""
    caminho_auditoria = saida / "registros_modelos_auditoria.json"
    if not caminho_auditoria.is_file():
        raise FileNotFoundError("registros_modelos_auditoria.json ausente")
    raiz = json.loads(caminho_auditoria.read_text(encoding="utf-8"))
    auditoria = raiz.get("modelos", {}) if isinstance(raiz, dict) else {}
    contagens = {}
    for modelo in modelos:
        aud = auditoria.get(modelo)
        if not isinstance(aud, dict):
            raise ValueError(f"{modelo}: auditoria ausente")
        arquivo = saida / f"registros_{modelo}.json"
        status = aud.get("status")
        if status == "ausente":
            if aud.get("ids_unicos") != 0 or arquivo.exists():
                raise ValueError(f"{modelo}: estado ausente inconsistente")
            continue
        if status not in {"valido_completo", "parcial"}:
            raise ValueError(f"{modelo}: status invalido: {status!r}")
        if aud.get("ids_invalidos") != 0 or not arquivo.is_file():
            raise ValueError(f"{modelo}: artefato indisponivel ou com ID invalido")
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        if not isinstance(dados, list) or len(dados) != aud.get("ids_unicos"):
            raise ValueError(f"{modelo}: contagem do artefato diverge da auditoria")
        for registro in dados:
            if not isinstance(registro, dict) or not set(registro).issubset(CHAVES_REGISTRO_MODELO):
                raise ValueError(f"{modelo}: campo nao permitido no artefato")
        contagens[modelo] = len(dados)
    return contagens, auditoria


def exportar_registros_modelos_da_planilha(sh, config: dict, saida: Path):
    """Renova somente os artefatos sanitizados derivados de ``CLASSIF__*``."""
    valida = {}
    try:
        conferencias = pl.ler_conferencias(sh, config["aba_principal"])
        valida = {ln: (d.get("ia") or "") for ln, d in conferencias.items()}
    except Exception:  # noqa: BLE001
        pass

    ids_atuais: set[str] = set()
    linha_atual_por_id: dict[str, int] = {}
    bloco_principal = com_retentativa(
        "ler ids da aba principal",
        lambda: sh.worksheet(config["aba_principal"]).get_values(
            "A:A", value_render_option="UNFORMATTED_VALUE"),
    )
    for linha_atual, rr in enumerate(bloco_principal[1:], start=2):
        idc = normalizar_id(rr[0] if rr else "")
        if idc:
            ids_atuais.add(idc)
            linha_atual_por_id[idc] = linha_atual
    if not ids_atuais:
        raise RuntimeError("IDs atuais indisponiveis; publicacao por modelo bloqueada")

    mm = config.get("multimodelo", {}) or {}
    modelos = list(mm.get("modelos_leves", [])) + list(mm.get("modelos_pesados", []))
    padrao = mm.get("aba_classificacao", "CLASSIF__{modelo}")
    contagens = {}
    auditoria = {}
    saida.mkdir(parents=True, exist_ok=True)
    for modelo in modelos:
        nome_aba = padrao.replace("{modelo}", modelo)
        try:
            vals = com_retentativa(
                f"ler {nome_aba}",
                lambda na=nome_aba: sh.worksheet(na).get_values(
                    "A:K", value_render_option="UNFORMATTED_VALUE"),
            )
        except Exception:  # noqa: BLE001
            vals = []
        registros, aud = deduplicar_registros_modelo(
            vals, ids_atuais, linha_atual_por_id, valida, modelo
        )
        auditoria[modelo] = aud
        arquivo = saida / f"registros_{modelo}.json"
        if registros:
            arquivo.write_text(json.dumps(registros, ensure_ascii=False), encoding="utf-8")
            contagens[modelo] = len(registros)
        else:
            arquivo.unlink(missing_ok=True)
    (saida / "registros_modelos_auditoria.json").write_text(
        json.dumps({"modelos": auditoria}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return contagens, auditoria


def exportar_reclass_resumo(sh, config):
    """Agrega as abas RECLASS__<modelo> em contagens seguras (sem texto/ID).

    Por modelo: total reclassificado, contagem por resultado (corrigido,
    prejudicado, mantido_correto, mantido_errado, decidido_humano,
    sem_referencia), por base de comparacao (validada/historico) e quantos
    mudaram de categoria. Alimenta a aba Reclassificacao do painel.

    Deduplica por linha_planilha antes de agregar (achado de 2026-07-23:
    RECLASS__random_forest acumulou 4.737 linhas duplicadas -- 18.049 linhas
    brutas para 13.312 linha_planilha distintas -- provavelmente por falha
    silenciosa do mecanismo de dedup em reclassificacao_multimodelo.py
    (linhas_ja_reclass), nao investigada em profundidade; a deduplicacao
    aqui e defensiva, mantendo a ULTIMA linha de cada linha_planilha
    (assume-se que reflete o estado mais recente da reclassificacao),
    e nao corrige a causa raiz na planilha.
    """
    mm = config.get("multimodelo", {}) or {}
    template = mm.get("aba_reclassificacao", "RECLASS__{modelo}")
    modelos = list(mm.get("modelos_leves", [])) + list(mm.get("modelos_pesados", []))
    por_modelo = []
    for m in modelos:
        rows_brutas = aba_para_objetos(sh, template.replace("{modelo}", m))
        if not rows_brutas:
            continue
        dedup = {}
        for r in rows_brutas:
            chave = str(r.get("linha_planilha", "")).strip()
            dedup[chave or id(r)] = r  # sem linha_planilha: nao deduplica (chave unica por objeto)
        rows = list(dedup.values())
        duplicadas = len(rows_brutas) - len(rows)
        res = {}
        base = {}
        mudou = 0
        ultima = ""
        for r in rows:
            res[str(r.get("resultado", "")).strip() or "?"] = res.get(str(r.get("resultado", "")).strip() or "?", 0) + 1
            b = str(r.get("base_comparacao", "")).strip() or "historico"
            base[b] = base.get(b, 0) + 1
            if str(r.get("mudou", "")).strip().lower() == "true":
                mudou += 1
            d = str(r.get("data", "")).strip()
            if d > ultima:
                ultima = d
        corr = res.get("corrigido", 0)
        prej = res.get("prejudicado", 0)
        por_modelo.append({
            "modelo": m, "total_reclassificado": len(rows), "mudou_categoria": mudou,
            "por_resultado": res, "por_base_comparacao": base,
            "corrigidos": corr, "prejudicados": prej, "ganho_liquido": corr - prej,
            "reuso_decisao_humana": res.get("decidido_humano", 0),
            "sem_referencia": res.get("sem_referencia", 0),
            "ultima_execucao": ultima,
            "linhas_duplicadas_removidas": duplicadas,
        })
    return {"gerado_em": agora_bahia(),
            "natureza": ("reclassificacao por modelo; corrigidos/prejudicados medidos contra a "
                         "verdade VALIDADA quando travada (base_comparacao=validada), senao contra "
                         "o historico (preliminar); deduplicado por linha_planilha (mantida a ultima "
                         "ocorrencia) -- ver linhas_duplicadas_removidas por modelo"),
            "por_modelo": por_modelo}


FORMATOS_DATA_HISTORICO = ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y")

NATUREZA_ESTABILIDADE = (
    "estabilidade da reclassificacao ao longo de TODO o historico (RECLASS_HISTORICO, "
    "append-only, todas as rodadas e modelos) -- complementa reclass_resumo.json, que so "
    "mostra o snapshot mais recente por modelo (abas RECLASS__<modelo>). So agregados: "
    "sem id_chamado no JSON publico, mesma regra de sanitizar_comparacao_previsoes."
)


def _parse_data_historico(valor):
    from datetime import datetime  # noqa: PLC0415
    s = str(valor or "").strip()
    for fmt in FORMATOS_DATA_HISTORICO:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _vazio_estabilidade_reclassificacao(aba: str) -> dict:
    return {
        "gerado_em": agora_bahia(), "aba_origem": aba, "natureza": NATUREZA_ESTABILIDADE,
        "total_entradas_historico": 0, "total_chamados_reclassificados": 0,
        "reclassificacoes_por_chamado": {"media": 0, "mediana": 0, "maximo": 0},
        "distribuicao_qtd_reclassificacoes": {}, "resultado_mais_recente": {},
        "mudou_categoria_desde_a_primeira": {"sim": 0, "nao": 0},
        "top_categorias_mais_reclassificadas": [], "modelo_mais_recente": {},
    }


def exportar_estabilidade_reclassificacao(sh, config):
    """Agrega RECLASS_HISTORICO (log append-only, todas as rodadas/modelos) por
    id_chamado, medindo ESTABILIDADE ao longo do tempo -- angulo que
    reclass_resumo.json (snapshot mais recente por modelo) nao cobre: quantas
    vezes cada chamado foi reclassificado no total, se a categoria oscilou
    entre a primeira e a ultima entrada, e qual o resultado mais recente
    (corrigido/prejudicado/mantido_correto/mantido_errado).

    So agregados no retorno: nenhum id_chamado nem texto de chamado (repo
    publico), mesma regra usada por sanitizar_comparacao_previsoes.
    """
    aba = (config.get("multimodelo", {}) or {}).get(
        "aba_historico_reclassificacao", "RECLASS_HISTORICO")
    try:
        ws = sh.worksheet(aba)
        valores = ws.get_values(value_render_option="UNFORMATTED_VALUE")
    except Exception:  # noqa: BLE001
        valores = []

    vazio = _vazio_estabilidade_reclassificacao(aba)
    if len(valores) < 2:
        return vazio

    cab = valores[0]
    norm = lambda s: " ".join(str(s or "").split()).strip().casefold()  # noqa: E731
    idx = {norm(n): i for i, n in enumerate(cab)}

    def col(nome):
        return idx.get(norm(nome))

    i_id, i_data, i_modelo = col("id_chamado"), col("data"), col("modelo")
    i_cat_antes, i_cat_depois = col("categoria_antes"), col("categoria_depois")
    i_resultado, i_cat_ref = col("resultado"), col("categoria_referencia")
    if i_id is None:
        return vazio

    def cel(linha, i):
        if i is None or i >= len(linha) or linha[i] is None:
            return ""
        return str(linha[i]).strip()

    por_id: dict[str, list[dict]] = {}
    for linha in valores[1:]:
        id_chamado = cel(linha, i_id)
        if not id_chamado:
            continue
        por_id.setdefault(id_chamado, []).append({
            "data": _parse_data_historico(cel(linha, i_data)),
            "modelo": cel(linha, i_modelo),
            "categoria_antes": cel(linha, i_cat_antes),
            "categoria_depois": cel(linha, i_cat_depois),
            "categoria_referencia": cel(linha, i_cat_ref),
            "resultado": cel(linha, i_resultado) or "?",
        })

    qtds = sorted(len(v) for v in por_id.values())
    n_chamados = len(qtds)
    dist_qtd: dict[str, int] = {}
    resultado_recente: dict[str, int] = {}
    modelo_recente: dict[str, int] = {}
    mudou_sim = mudou_nao = 0
    categoria_contagem: dict[str, int] = {}

    for entradas in por_id.values():
        chave = str(len(entradas)) if len(entradas) < 4 else "4_ou_mais"
        dist_qtd[chave] = dist_qtd.get(chave, 0) + 1

        com_data = [e for e in entradas if e["data"] is not None]
        ordenadas = sorted(com_data, key=lambda e: e["data"]) if com_data else entradas
        primeira, ultima = ordenadas[0], ordenadas[-1]

        res = ultima["resultado"] or "?"
        resultado_recente[res] = resultado_recente.get(res, 0) + 1
        mod = ultima["modelo"] or "?"
        modelo_recente[mod] = modelo_recente.get(mod, 0) + 1

        cat_inicial = primeira["categoria_antes"] or primeira["categoria_referencia"]
        cat_final = ultima["categoria_depois"]
        if cat_inicial and cat_final and cat_inicial != cat_final:
            mudou_sim += 1
        else:
            mudou_nao += 1

        cat_ref = ultima["categoria_referencia"] or cat_inicial
        if cat_ref:
            categoria_contagem[cat_ref] = categoria_contagem.get(cat_ref, 0) + 1

    top_categorias = sorted(categoria_contagem.items(), key=lambda kv: -kv[1])[:10]

    return {
        "gerado_em": agora_bahia(), "aba_origem": aba, "natureza": NATUREZA_ESTABILIDADE,
        "total_entradas_historico": len(valores) - 1,
        "total_chamados_reclassificados": n_chamados,
        "reclassificacoes_por_chamado": {
            "media": round(sum(qtds) / n_chamados, 2) if n_chamados else 0,
            "mediana": qtds[n_chamados // 2] if n_chamados else 0,
            "maximo": qtds[-1] if n_chamados else 0,
        },
        "distribuicao_qtd_reclassificacoes": dist_qtd,
        "resultado_mais_recente": resultado_recente,
        "mudou_categoria_desde_a_primeira": {"sim": mudou_sim, "nao": mudou_nao},
        "top_categorias_mais_reclassificadas": [
            {"categoria": c, "qtd_chamados": n} for c, n in top_categorias],
        "modelo_mais_recente": modelo_recente,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Exporta os JSONs sanitizados do dashboard.")
    p.add_argument(
        "--fonte-modelos", choices=("auto", "artefatos", "planilha"), default="planilha",
        help=("auto prefere artefatos e usa CLASSIF__* como fallback; "
              "artefatos falha fechado; planilha renova os arquivos."),
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
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

    # COMPARACAO_PREVISOES contem id_chamado, titulo e observacao livre na planilha.
    # O JSON publico remove esses campos e preserva apenas categorias/statuses.
    dados_prev = sanitizar_comparacao_previsoes(
        aba_para_objetos(sh, abas_cfg.get("comparacao_previsoes")) if abas_cfg.get("comparacao_previsoes") else []
    )
    (SAIDA / "comparacao_previsoes.json").write_text(
        json.dumps(dados_prev, ensure_ascii=False), encoding="utf-8")
    resumo["abas"]["comparacao_previsoes"] = len(dados_prev)
    print(f"comparacao_previsoes: {len(dados_prev)} linhas (sanitizado)")

    # Abas multimodelo (nome literal). Exporta [] quando ainda nao materializado.
    for chave_json, nome_aba in _abas_multimodelo(config):
        dados = aba_para_objetos(sh, nome_aba) if nome_aba else []
        (SAIDA / f"{chave_json}.json").write_text(
            json.dumps(dados, ensure_ascii=False), encoding="utf-8")
        resumo["abas"][chave_json] = len(dados)
        print(f"{chave_json}: {len(dados)} linhas")

    # Resumo agregado da reclassificacao por modelo (abas RECLASS__*, sem texto).
    try:
        rr = exportar_reclass_resumo(sh, config)
        (SAIDA / "reclass_resumo.json").write_text(json.dumps(rr, ensure_ascii=False), encoding="utf-8")
        resumo["abas"]["reclass_resumo"] = len(rr.get("por_modelo", []))
        print(f"reclass_resumo: {len(rr.get('por_modelo', []))} modelos")
    except Exception as e:  # noqa: BLE001
        print(f"reclass_resumo falhou: {type(e).__name__}: {e}", file=sys.stderr)

    # Estabilidade da reclassificacao no historico completo (RECLASS_HISTORICO,
    # todas as rodadas/modelos) -- complementa reclass_resumo.json (snapshot
    # mais recente por modelo) com a trajetoria: quantas vezes cada chamado foi
    # reclassificado, se oscilou, resultado mais recente. So agregados.
    try:
        er = exportar_estabilidade_reclassificacao(sh, config)
        (SAIDA / "estabilidade_reclassificacao.json").write_text(
            json.dumps(er, ensure_ascii=False), encoding="utf-8")
        resumo["abas"]["estabilidade_reclassificacao"] = er.get("total_chamados_reclassificados", 0)
        print(f"estabilidade_reclassificacao: {er.get('total_entradas_historico', 0)} entradas, "
              f"{er.get('total_chamados_reclassificados', 0)} chamados")
    except Exception as e:  # noqa: BLE001
        print(f"estabilidade_reclassificacao falhou: {type(e).__name__}: {e}", file=sys.stderr)

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
    # Validacao humana: conferencia dupla na aba principal (M=CONFERENCIA IA,
    # N=CONFERENCIA GLPI). O campo "v" do registro usa a conferencia da IA (coluna M).
    valida = {}
    try:
        conferencias = pl.ler_conferencias(sh, config["aba_principal"])
        valida = {ln: (d.get("ia") or "") for ln, d in conferencias.items()}
    except Exception:  # noqa: BLE001
        pass

    # SNAPSHOT_ETAPA_1 e' append-only: uma rematerializacao (G:K) forca reclassificar
    # chamados ja presentes no snapshot, sem apagar o registro antigo (decisao da
    # rodada 20, ver src/rematerializar_etapa1_oficial.py). Sem dedup, um chamado
    # reprocessado apareceria duas vezes em registros.json.
    #
    # A dedup e por id_chamado (coluna 2), NUNCA por linha_planilha (coluna 1). A
    # aba principal muda de tamanho quando o GLPI ganha ou perde chamados, e uma
    # mesma linha passa a designar outro chamado; deduplicar por linha faz dois
    # chamados distintos colidirem e o painel mostrar um total que nao existe mais.
    # Em 02/08/2026 o painel exibia 14.094 registros enquanto a base tinha 14.058.
    #
    # O snapshot tambem guarda chamados que SAIRAM da base (54 de 'UFSB > Dinfra >
    # Projetos e Obras' e 2 excluidos no GLPI). Eles nao podem entrar no painel,
    # entao a lista e filtrada pelos ids que existem hoje na aba principal.
    ids_atuais: set[str] = set()
    linha_atual_por_id: dict[str, int] = {}
    try:
        bloco_principal = com_retentativa(
            "ler ids da aba principal",
            lambda: sh.worksheet(config["aba_principal"]).get_values(
                "A:A", value_render_option="UNFORMATTED_VALUE"),
        )
        for linha_atual, rr in enumerate(bloco_principal[1:], start=2):
            i = normalizar_id(rr[0] if rr else "")
            if i:
                ids_atuais.add(i)
                linha_atual_por_id[i] = linha_atual
    except Exception:  # noqa: BLE001
        ids_atuais = set()

    por_id = {}
    descartados_fora_da_base = 0
    for rr in snap[1:]:
        if len(rr) < 6:
            continue
        ln = str(rr[1]).strip()
        idc = normalizar_id(rr[2] if len(rr) > 2 else "")
        orig = str(rr[3]).strip()
        cia = str(rr[4]).strip()
        if not cia or not idc:
            continue
        if ids_atuais and idc not in ids_atuais:
            descartados_fora_da_base += 1
            continue
        c = normalizar_confianca(rr[5])
        ex = str(rr[6]).strip() if len(rr) > 6 else ""
        fa = "acima_95" if c >= 0.95 else ("entre_70_95" if c >= 0.70 else "abaixo_70")
        por_id[idc] = {"l": ln, "g": (orig.split(" > ")[0].strip() if orig else "(sem)"),
                       "m": tipo_manutencao(orig), "o": orig, "p": cia, "c": round(c, 4), "f": fa, "e": ex,
                       "k": 1 if cia == orig else 0, "v": valida.get(ln, "")}
    if descartados_fora_da_base:
        print(f"snapshot: {descartados_fora_da_base} registro(s) de chamados que "
              "nao estao mais na base foram descartados")
    regs = list(por_id.values())
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
    auditoria_modelos = {}
    fonte_modelos_usada = ""
    if args.fonte_modelos in {"auto", "artefatos"}:
        try:
            registros_modelos, auditoria_modelos = carregar_registros_modelos_de_artefatos(
                SAIDA, modelos_mm
            )
            fonte_modelos_usada = "artefatos"
            print(f"registros_modelos: artefatos validados ({len(registros_modelos)} modelos)")
        except Exception as e:  # noqa: BLE001
            if args.fonte_modelos == "artefatos":
                raise
            print(f"registros_modelos: artefatos recusados ({type(e).__name__}: {e}); "
                  "fallback para CLASSIF__*", file=sys.stderr)

    if not fonte_modelos_usada:
        fonte_modelos_usada = "planilha"
        for modelo in modelos_mm:
            nome_aba = padrao.replace("{modelo}", modelo)
            try:
                vals = com_retentativa(
                    f"ler {nome_aba}",
                    lambda na=nome_aba: sh.worksheet(na).get_values(
                        "A:K", value_render_option="UNFORMATTED_VALUE"))
            except Exception:  # noqa: BLE001
                vals = []
            rm, aud = deduplicar_registros_modelo(
                vals, ids_atuais, linha_atual_por_id, valida, modelo
            )
            auditoria_modelos[modelo] = aud
            arquivo_modelo = SAIDA / f"registros_{modelo}.json"
            if rm:
                arquivo_modelo.write_text(
                    json.dumps(rm, ensure_ascii=False), encoding="utf-8")
                registros_modelos[modelo] = len(rm)
                print(f"registros_{modelo}={len(rm)} "
                      f"(brutos={aud['registros_brutos']}, "
                      f"duplicados_descartados={aud['duplicados_descartados']}, "
                      f"status={aud['status']})")
            else:
                arquivo_modelo.unlink(missing_ok=True)
                print(f"registros_{modelo}=0 (status=ausente; JSON obsoleto removido)")
        (SAIDA / "registros_modelos_auditoria.json").write_text(
            json.dumps({"modelos": auditoria_modelos}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    resumo["registros_modelos"] = registros_modelos
    resumo["fonte_registros_modelos"] = fonte_modelos_usada

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
