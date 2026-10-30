from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import corte_b as cb  # noqa: E402
import trilha_b as tb  # noqa: E402

CATEGORIAS = {
    "Cat A": "ar condicionado split vazando agua sala",
    "Cat B": "lampada queimada corredor troca iluminacao",
    "Cat C": "vazamento torneira banheiro hidraulica reparo",
}
CAMPI = ["Campus X", "Campus Y"]


def registros_sinteticos(n_por_categoria: int = 30) -> list[dict[str, str]]:
    """Cada chamado tem texto distinto (grupo unitario), ano e campus variados."""
    regs = []
    contador = 0
    for cat, base in CATEGORIAS.items():
        for j in range(n_por_categoria):
            contador += 1
            ano = 2021 + (j % 6)
            regs.append({
                "id": str(1000 + contador),
                "titulo": f"{base} {j}", "descricao_glpi": f"detalhe {contador}",
                "titulo_osm": "", "descricao_osm": "",
                "categoria_historica": cat, "conferencia_glpi": "Correto",
                "categoria_manual": "",
                "data_abertura": f"{ano}-0{1 + j % 9}-10 08:00" if ano < 2027 else "",
                "campus": CAMPI[j % 2],
                "periodo": (cb.PERIODO_PROSPECTIVO if ano == 2026
                            else cb.PERIODO_HISTORICO),
            })
    return regs


def linhas_snapshot(regs):
    out = []
    for r in regs:
        out.append({
            "id_chamado": r["id"], "titulo": r["titulo"],
            "descricao_glpi": r["descricao_glpi"], "titulo_osm": r["titulo_osm"],
            "descricao_osm": r["descricao_osm"],
            "categoria_historica": r["categoria_historica"],
            "conferencia_glpi": r["conferencia_glpi"],
            "categoria_manual": r["categoria_manual"],
            "referencia_humana": r["categoria_historica"],
            "fonte_referencia": "conferencia_glpi",
            "data_abertura": r["data_abertura"], "campus": r["campus"],
            "periodo": r["periodo"],
        })
    return out


class TestTrilhaB(unittest.TestCase):
    def test_snapshot_que_reproduz_o_manifesto_passa(self):
        linhas = linhas_snapshot(registros_sinteticos())
        manifesto = {"impressoes_digitais": cb.impressoes_digitais(linhas),
                     "corpus": {"linhas": len(linhas)}}
        digitais = tb.verificar_snapshot(linhas, manifesto)
        self.assertEqual(digitais, manifesto["impressoes_digitais"])

    def test_snapshot_alterado_e_recusado(self):
        linhas = linhas_snapshot(registros_sinteticos())
        manifesto = {"impressoes_digitais": cb.impressoes_digitais(linhas),
                     "corpus": {"linhas": len(linhas)}}
        linhas[0]["titulo"] += " editado"
        with self.assertRaises(RuntimeError):
            tb.verificar_snapshot(linhas, manifesto)

    def test_particoes_nao_dividem_grupos_e_cobrem_tudo(self):
        regs = registros_sinteticos()
        r = tb.etapa_particoes(regs, k=3, semente=42, minimo=3)
        p = r["particoes"]
        self.assertEqual(p["status"], "apto_para_treinar")
        self.assertEqual(p["linhas_particionadas"], len(regs))
        self.assertEqual(p["grupos_divididos_entre_dobras"], 0)
        self.assertEqual(len(r["atributos"]), len(regs))

    def test_particoes_sao_deterministicas(self):
        regs = registros_sinteticos()
        a = tb.etapa_particoes(regs, k=3, minimo=3)["particoes"]["mapa_sha256"]
        b = tb.etapa_particoes(list(reversed(regs)), k=3, minimo=3)[
            "particoes"]["mapa_sha256"]
        self.assertEqual(a, b)

    def _corpus(self):
        regs = registros_sinteticos()
        r = tb.etapa_particoes(regs, k=3, minimo=3)
        mapa = {x["id_sha256"]: x["dobra"] for x in r["particoes"]["_mapa"]}
        return regs, r, tb.preparar_corpus(regs, mapa)

    def test_retreino_gera_predicoes_sem_vazamento_e_por_campus(self):
        _regs, _r, corpus = self._corpus()
        rel = tb.etapa_retreino(corpus, ["naive_bayes", "linear_svc"],
                                registrar=lambda m: None)
        self.assertEqual(rel["status"], "apto_para_regras")
        for m in rel["modelos"]:
            self.assertEqual(m["grupos_vazados_para_o_treino"], 0)
            self.assertEqual(m["registros_sem_predicao"], 0)
            self.assertEqual({c["campus"] for c in m["por_campus"]}, set(CAMPI))
            self.assertEqual(sum(c["n"] for c in m["por_campus"]), len(corpus["textos"]))

    def test_temporal_treina_no_passado_e_testa_no_futuro(self):
        _regs, _r, corpus = self._corpus()
        rel = tb.etapa_temporal(corpus, ["naive_bayes"], anos_teste=(2024, 2026),
                                registrar=lambda m: None)
        nomes = [c["cenario"] for c in rel["cenarios"]]
        self.assertEqual(nomes, ["prospectivo", "origem_rolante_2024",
                                 "origem_rolante_2026"])
        pros = rel["cenarios"][0]
        n_hist = sum(1 for p in corpus["periodos"] if p == cb.PERIODO_HISTORICO)
        n_pros = sum(1 for p in corpus["periodos"] if p == cb.PERIODO_PROSPECTIVO)
        self.assertEqual((pros["treino"], pros["teste"]), (n_hist, n_pros))
        rolante = rel["cenarios"][1]
        self.assertEqual(rolante["treino"], sum(
            1 for a in corpus["anos"] if int(a) < 2024))

    def test_saidas_nao_publicam_texto_nem_ids(self):
        regs, r, corpus = self._corpus()
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            saidas = {k: base / v.name for k, v in tb.SAIDAS.items()}
            digitais = {"hash_corte": "x"}
            tb.gravar_particoes(r, digitais, "agora", saidas)
            rel = tb.etapa_retreino(corpus, ["naive_bayes"], registrar=lambda m: None)
            tb.gravar_retreino(rel, corpus, digitais, "agora", saidas)
            tudo = "".join(p.read_text(encoding="utf-8") for p in base.iterdir())
        for reg in regs:
            self.assertNotIn(reg["titulo"], tudo)
            self.assertNotIn(f'"{reg["id"]}"', tudo)
            self.assertNotIn(f",{reg['id']},", tudo)

    def test_gravacao_recusa_artefato_do_artigo_congelado(self):
        protegido = cb.RAIZ / "docs" / "dados" / "retreino_canonico.json"
        saidas = dict(tb.SAIDAS, retreino_json=protegido)
        with self.assertRaises(RuntimeError):
            tb.gravar_retreino({"modelos": [], "_resultados": []},
                               {"chaves": [], "dobras": [], "rotulos": []},
                               {"hash_corte": "x"}, "agora", saidas)

    def test_saidas_padrao_ficam_no_namespace_da_trilha_b(self):
        for caminho in tb.SAIDAS.values():
            self.assertEqual(caminho.parent, tb.DADOS_B)
            cb.garantir_fora_do_congelado(caminho)

    def test_calibracao_usa_as_predicoes_do_retreino_sem_vazar_a_dobra_externa(self):
        _regs, _r, corpus = self._corpus()
        with tempfile.TemporaryDirectory() as d:
            saidas = {k: Path(d) / v.name for k, v in tb.SAIDAS.items()}
            rel = tb.etapa_retreino(corpus, ["naive_bayes"], registrar=lambda m: None)
            tb.gravar_retreino(rel, corpus, {"hash_corte": "x"}, "agora", saidas)
            cal = tb.etapa_calibracao(corpus, ["naive_bayes"],
                                      saidas["retreino_pred"], registrar=lambda m: None)
            with self.assertRaises(RuntimeError):
                tb.etapa_calibracao(corpus, ["linear_svc"], saidas["retreino_pred"],
                                    registrar=lambda m: None)
            tb.gravar_calibracao(cal, {"hash_corte": "x"}, "agora", saidas)
            gravado = json.loads(saidas["calibracao_json"].read_text(encoding="utf-8"))
        self.assertEqual(cal["trilha"], "B")
        self.assertEqual(cal["corpus"]["registros"], len(corpus["chaves"]))
        self.assertEqual(gravado["hash_corte"], "x")
        self.assertEqual(len(cal["modelos"]), 1)

    def test_regras_comparam_modelo_puro_e_hibrido_nos_mesmos_registros(self):
        _regs, _r, corpus = self._corpus()
        with tempfile.TemporaryDirectory() as d:
            saidas = {k: Path(d) / v.name for k, v in tb.SAIDAS.items()}
            rel = tb.etapa_retreino(corpus, ["naive_bayes"], registrar=lambda m: None)
            tb.gravar_retreino(rel, corpus, {"hash_corte": "x"}, "agora", saidas)
            regras = tb.etapa_regras(corpus, saidas["retreino_pred"])
            tb.gravar_regras(regras, {"hash_corte": "x"}, "agora", saidas)
            gravado = json.loads(saidas["regras_json"].read_text(encoding="utf-8"))
        self.assertEqual(regras["trilha"], "B")
        self.assertEqual(regras["corpus"]["registros"], len(corpus["chaves"]))
        self.assertEqual(list(regras["modelos"]), ["naive_bayes"])
        self.assertEqual(gravado["hash_corte"], "x")

    def test_kfold_compara_linha_e_grupo_no_mesmo_corte(self):
        _regs, _r, corpus = self._corpus()
        rel = tb.etapa_kfold(corpus, ["naive_bayes"], k=3, registrar=lambda m: None)
        r = rel["resultados"][0]
        self.assertEqual(rel["trilha"], "B")
        self.assertEqual(rel["duplicatas_textuais"]["n_linhas"], len(corpus["textos"]))
        self.assertIn("delta_acuracia_kfold_menos_groupkfold", r)
        self.assertEqual(rel["ranking_kfold"], ["naive_bayes"])

    def test_lstm_deterministico_restaura_a_fabrica(self):
        original = tb.rmc.zoo.criar_modelo
        with tb.lstm_deterministico(42):
            self.assertIsNot(tb.rmc.zoo.criar_modelo, original)
        self.assertIs(tb.rmc.zoo.criar_modelo, original)


if __name__ == "__main__":
    unittest.main()
