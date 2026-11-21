from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import comparar_direcoes_ufrn as cd  # noqa: E402


class TestCompararDirecoes(unittest.TestCase):
    def test_spearman_de_ordens_iguais_e_invertidas(self):
        a = {"x": 0.9, "y": 0.8, "z": 0.7, "w": 0.6}
        self.assertEqual(cd.spearman(a, {"x": 4, "y": 3, "z": 2, "w": 1}), 1.0)
        self.assertEqual(cd.spearman(a, {"x": 1, "y": 2, "z": 3, "w": 4}), -1.0)
        self.assertIsNone(cd.spearman({"x": 1, "y": 2}, {"x": 2, "y": 1}))

    def test_coluna_sem_viario_pondera_pelo_n_de_cada_divisao(self):
        direto = {"modelos": {"a": {"concordancia_com_correspondencia": 0.5, "por_divisao": {
            "servicos gerais": {"n": 100, "concordancia": 0.9},
            "ar condicionado": {"n": 100, "concordancia": 0.7},
            "viario": {"n": 100, "concordancia": 0.0}}}}}
        res = cd.reunir({"modelos": []}, None, direto, {"resultados": {}})
        self.assertEqual(res["acuracia_por_condicao"]["nossa_para_ufrn_sem_viario"]["a"], 0.8)

    def test_reunir_e_renderizar_quatro_condicoes(self):
        retreino = {"modelos": [{"modelo": "a", "acuracia": 0.8}, {"modelo": "b", "acuracia": 0.7},
                                {"modelo": "c", "acuracia": 0.6}]}
        direto = {"modelos": {n: {"concordancia_com_correspondencia": v}
                              for n, v in (("a", 0.7), ("b", 0.6), ("c", 0.5))}}
        reverso = {"resultados": {n: {"ufrn_teste": {"acuracia": u}, "nossa_base": {"acuracia": o}}
                                  for n, u, o in (("a", 0.9, 0.5), ("b", 0.8, 0.6), ("c", 0.7, 0.7))}}
        res = cd.reunir(retreino, None, direto, reverso)
        self.assertEqual(set(res["acuracia_por_condicao"]),
                         {"nossa_para_nossa", "nossa_para_ufrn", "nossa_para_ufrn_sem_viario",
                          "ufrn_para_ufrn", "ufrn_para_nossa"})
        self.assertEqual(res["acuracia_por_condicao"]["nossa_para_ufrn_sem_viario"], {})
        corr = {tuple(c["condicoes"]): c["spearman"] for c in res["correlacao_de_postos"]}
        self.assertEqual(corr[("nossa_para_nossa", "nossa_para_ufrn")], 1.0)
        self.assertEqual(corr[("nossa_para_nossa", "ufrn_para_nossa")], -1.0)
        texto = cd.renderizar(res)
        self.assertIn("| a |", texto)
        self.assertIn("0,8000", texto)


if __name__ == "__main__":
    unittest.main()
