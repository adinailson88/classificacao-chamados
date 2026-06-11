#!/usr/bin/env python3
"""Testes offline da memoria de decisao (conferencias M/N/P) e do veto de
categorias na predicao e nos ensembles. Nao tocam na planilha."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import decisao_validada as dv  # noqa: E402
import planilha as pl  # noqa: E402
from classificacao_multimodelo import _prever_com_veto, prever_out_of_fold  # noqa: E402
from avaliacao_final import (mcnemar_p, peso_log_odds, votar_maioria,  # noqa: E402
                             confianca_maxima)
from analise_erros import cliffs_delta, cobertura_termos  # noqa: E402


class _WorksheetFalsa:
    def __init__(self, valores):
        self.valores = valores

    def get_values(self, *_args, **_kwargs):
        return self.valores


class _SpreadsheetFalsa:
    def __init__(self, valores):
        self.valores = valores

    def worksheet(self, _nome):
        return _WorksheetFalsa(self.valores)


def _linha(*valores, largura=16):
    return list(valores) + [""] * max(0, largura - len(valores))


class TestDecidir(unittest.TestCase):
    def test_acerto_conferido_trava(self):
        # N=Correto: a categoria da IA (G) vira decisao travada.
        d = dv.decidir("HIDRAULICA", "ELETRICA", "", None, "Correto", None)
        self.assertEqual(d["status"], dv.STATUS_DECIDIDO)
        self.assertEqual(d["decidida"], "ELETRICA")
        self.assertEqual(d["fonte_decisao"], "conferencia_ia")

    def test_erro_conferido_elimina(self):
        # M=Errado: o historico (C) fica vetado; nada decidido.
        d = dv.decidir("HIDRAULICA", "ELETRICA", "", "Errado", None, None)
        self.assertEqual(d["status"], dv.STATUS_RESTRITO)
        self.assertIsNone(d["decidida"])
        self.assertEqual(d["eliminadas"], {"HIDRAULICA"})

    def test_glpi_certo_ia_errada(self):
        # M=Correto + N=Errado: decisao = historico; categoria da IA eliminada.
        d = dv.decidir("HIDRAULICA", "ELETRICA", "", "Correto", "Errado", None)
        self.assertEqual(d["decidida"], "HIDRAULICA")
        self.assertEqual(d["eliminadas"], {"ELETRICA"})

    def test_ambos_errados(self):
        # M=Errado + N=Errado: duas categorias vetadas, verdade desconhecida.
        d = dv.decidir("HIDRAULICA", "ELETRICA", "", "Errado", "Errado", None)
        self.assertEqual(d["status"], dv.STATUS_RESTRITO)
        self.assertEqual(d["eliminadas"], {"HIDRAULICA", "ELETRICA"})

    def test_conflito_devolvido(self):
        # M=Correto e N=Correto com C != G: contraditorio -> sem decisao.
        d = dv.decidir("HIDRAULICA", "ELETRICA", "", "Correto", "Correto", None)
        self.assertTrue(d["conflito"])
        self.assertIsNone(d["decidida"])

    def test_concordantes_corretos(self):
        # C == G e ambos Corretos: decide sem conflito.
        d = dv.decidir("HIDRAULICA", "HIDRAULICA", "", "Correto", "Correto", None)
        self.assertFalse(d["conflito"])
        self.assertEqual(d["decidida"], "HIDRAULICA")

    def test_reclass_conferida(self):
        # P=Correto trava a categoria da reclassificacao (O).
        d = dv.decidir("HIDRAULICA", "ELETRICA", "CLIMATIZACAO", None, None, "Correto")
        self.assertEqual(d["decidida"], "CLIMATIZACAO")
        self.assertEqual(d["fonte_decisao"], "conferencia_reclass")

    def test_reclass_correta_trava(self):
        d = dv.decidir("HIDRAULICA", "ELETRICA", "CLIMATIZACAO", None, None, "Correto")
        self.assertEqual(d["status"], dv.STATUS_DECIDIDO)
        self.assertEqual(d["decidida"], "CLIMATIZACAO")

    def test_decidida_nao_eliminada(self):
        # Mesma categoria certa numa conferencia e errada noutra coluna nao
        # pode constar eliminada (ex.: C==O, M=Correto, P=Errado e impossivel
        # na pratica, mas a decisao prevalece).
        d = dv.decidir("X", "", "X", "Correto", None, "Errado")
        self.assertEqual(d["decidida"], "X")
        self.assertNotIn("X", d["eliminadas"])


class _ModeloFixo:
    """Modelo de mentira com distribuicao conhecida para testar o veto."""
    classes = ["A", "B", "C"]

    def predict_score(self, textos):
        return ["A"] * len(textos), [0.6] * len(textos)

    def predict_dist(self, textos):
        return self.classes, np.array([[0.6, 0.3, 0.1]] * len(textos))


class TestVeto(unittest.TestCase):
    def test_sem_veto_argmax(self):
        preds, scores = _prever_com_veto(_ModeloFixo(), ["t"], [set()])
        self.assertEqual(preds, ["A"])
        self.assertAlmostEqual(scores[0], 0.6)

    def test_veto_cai_para_segunda(self):
        preds, scores = _prever_com_veto(_ModeloFixo(), ["t"], [{"A"}])
        self.assertEqual(preds, ["B"])
        # renormalizada: 0.3 / (0.3 + 0.1)
        self.assertAlmostEqual(scores[0], 0.75)

    def test_veto_total_ignorado(self):
        # Se TODAS as classes fossem vetadas, o veto e ignorado (sem opcao).
        preds, _ = _prever_com_veto(_ModeloFixo(), ["t"], [{"A", "B", "C"}])
        self.assertEqual(preds, ["A"])

    def test_oof_respeita_veto(self):
        # Corpus sintetico bem separavel; o veto da classe verdadeira forca a 2a.
        lote = [{"texto": f"agua vazamento torneira {i}", "categoria_original": "HID"}
                for i in range(10)]
        base_t = [f"agua vazamento torneira pia {i}" for i in range(30)] + \
                 [f"energia tomada disjuntor luz {i}" for i in range(30)]
        base_c = ["HID"] * 30 + ["ELE"] * 30
        preds, _, _ = prever_out_of_fold(
            "naive_bayes", lote, base_t, base_c, k_folds=5, min_base=10,
            fracao_topup=0.9, vetos=[{"HID"}] * len(lote))
        self.assertTrue(all(p != "HID" for p in preds))


class TestLeituraPorCabecalho(unittest.TestCase):
    def test_decisao_por_cabecalhos_ordem_normal(self):
        cab = _linha("ID", "TITULO", "CATEGORIA COMPLETA", "D", "E", "F",
                     "Classificacao IA", "H", "I", "J", "K", "L",
                     "CONFERENCIA GLPI", "CONFERENCIA IA", "Classificacao IA - 2",
                     "CONFERENCIA IA - 2")
        vals = [cab, _linha("1", "", "HID", "", "", "", "ELE", "", "", "", "", "", "Errado", "Correto", "", "")]
        decisoes = dv.carregar_decisoes(_SpreadsheetFalsa(vals), "Aba")
        self.assertEqual(decisoes[2]["decidida"], "ELE")
        conferencias = pl.ler_conferencias(_SpreadsheetFalsa(vals), "Aba")
        self.assertEqual(conferencias["2"]["ia"], "Correto")
        self.assertEqual(conferencias["2"]["glpi"], "Errado")

    def test_decisao_por_cabecalhos_com_acentos(self):
        cab = _linha("ID", "TÍTULO", "CATEGORIA COMPLETA", "D", "E", "F",
                     "Classificação IA", "H", "I", "J", "K", "L",
                     "CONFERÊNCIA GLPI", "CONFERÊNCIA IA", "Classificação IA - 2",
                     "CONFERÊNCIA IA - 2")
        vals = [cab, _linha("1", "", "HID", "", "", "", "ELE", "", "", "", "", "", "Correto", "Correto", "CLIMA", "")]
        decisoes = dv.carregar_decisoes(_SpreadsheetFalsa(vals), "Aba")
        self.assertTrue(decisoes[2]["conflito"])

    def test_fallback_posicional_sem_cabecalho(self):
        cab = _linha("A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P")
        vals = [cab, _linha("1", "", "HID", "", "", "", "ELE", "", "", "", "", "", "Errado", "", "CLIMA", "Correto")]
        decisoes = dv.carregar_decisoes(_SpreadsheetFalsa(vals), "Aba")
        self.assertEqual(decisoes[2]["decidida"], "CLIMA")

    def test_categoria_errada_vira_veto(self):
        cab = _linha("ID", "TITULO", "CATEGORIA COMPLETA", "D", "E", "F",
                     "Classificacao IA", "H", "I", "J", "K", "L",
                     "CONFERENCIA GLPI", "CONFERENCIA IA", "Classificacao IA - 2",
                     "CONFERENCIA IA - 2")
        vals = [cab, _linha("1", "", "HID", "", "", "", "ELE", "", "", "", "", "", "Errado", "", "", "")]
        decisoes = dv.carregar_decisoes(_SpreadsheetFalsa(vals), "Aba")
        self.assertEqual(decisoes[2]["status"], dv.STATUS_RESTRITO)
        self.assertEqual(decisoes[2]["eliminadas"], {"HID"})


class TestEnsembles(unittest.TestCase):
    def test_maioria_respeita_veto(self):
        preds_linha = {"m1": {"pred": "A", "conf": 0.9},
                       "m2": {"pred": "A", "conf": 0.8},
                       "m3": {"pred": "B", "conf": 0.7}}
        self.assertEqual(votar_maioria(preds_linha, None, set()), "A")
        self.assertEqual(votar_maioria(preds_linha, None, {"A"}), "B")

    def test_maioria_ponderada(self):
        preds_linha = {"m1": {"pred": "A", "conf": 0.9},
                       "m2": {"pred": "B", "conf": 0.8},
                       "m3": {"pred": "B", "conf": 0.7}}
        pesos = {"m1": 5.0, "m2": 1.0, "m3": 1.0}
        self.assertEqual(votar_maioria(preds_linha, pesos, set()), "A")

    def test_confianca_maxima_veto(self):
        preds_linha = {"m1": {"pred": "A", "conf": 0.99},
                       "m2": {"pred": "B", "conf": 0.5}}
        self.assertEqual(confianca_maxima(preds_linha, {}, set()), "A")
        self.assertEqual(confianca_maxima(preds_linha, {}, {"A"}), "B")

    def test_mcnemar_e_pesos(self):
        self.assertIsNone(mcnemar_p(0, 0))
        p = mcnemar_p(20, 5)
        self.assertIsNotNone(p)
        self.assertLess(p, 0.05)
        self.assertGreater(peso_log_odds(0.9), peso_log_odds(0.6))
        self.assertAlmostEqual(peso_log_odds(0.5), 0.0)


class TestAnaliseErros(unittest.TestCase):
    def test_cliffs_delta_extremos(self):
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([10.0, 11.0, 12.0])
        self.assertAlmostEqual(cliffs_delta(a, b), -1.0)
        self.assertAlmostEqual(cliffs_delta(b, a), 1.0)
        self.assertAlmostEqual(cliffs_delta(a, a), 0.0)

    def test_cobertura_termos(self):
        texto = "ar condicionado nao esta gelando na sala"
        termos = ["ar condicionado", "gelando", "split", "gas"]
        self.assertAlmostEqual(cobertura_termos(texto, termos), 0.5)
        self.assertEqual(cobertura_termos(texto, []), 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
