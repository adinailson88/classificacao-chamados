from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import amostragem_avaliacao as am  # noqa: E402


class TestAmostragemAvaliacao(unittest.TestCase):
    def test_tamanho_conhecido_para_populacao_grande(self):
        # 385 e o valor classico para 95% de confianca e margem de 5%.
        self.assertEqual(am.tamanho_amostra(10 ** 9, 0.05), 385)
        self.assertEqual(am.tamanho_amostra(10 ** 9, 0.02), 2401)

    def test_correcao_de_populacao_finita_e_censo_quando_pequena(self):
        self.assertEqual(am.tamanho_amostra(631, 0.05), 240)
        self.assertEqual(am.tamanho_amostra(10, 0.05), 10)
        self.assertEqual(am.tamanho_amostra(0, 0.05), 0)
        with self.assertRaises(ValueError):
            am.tamanho_amostra(100, 0)

    def test_margem_volta_para_a_margem_pedida(self):
        n = am.tamanho_amostra(10000, 0.05)
        self.assertLessEqual(am.margem_estrato(10000, n), 0.05)
        self.assertGreater(am.margem_estrato(10000, n - 5), 0.0499)

    def test_margem_global_pondera_pelo_peso_do_estrato(self):
        pops = {"a": 9000, "b": 1000}
        m = am.margem_global(pops, {"a": 400, "b": 100})
        self.assertLess(m, am.margem_estrato(1000, 100))
        self.assertEqual(am.margem_global(pops, {"a": 400}), 1.0)

    def test_sorteio_e_reprodutivel_e_estende_sem_repetir(self):
        ids = {"x": [f"x{i}" for i in range(100)], "y": [f"y{i}" for i in range(50)]}
        a = am.sortear_ids(ids, {"x": 30, "y": 10}, semente=7)
        self.assertEqual(a, am.sortear_ids(ids, {"x": 30, "y": 10}, semente=7))
        self.assertEqual((len(a["x"]), len(a["y"])), (30, 10))
        ja = a["x"] + a["y"]
        b = am.sortear_ids(ids, {"x": 45, "y": 10}, semente=8, ja_sorteados=ja)
        self.assertEqual((len(b["x"]), len(b["y"])), (15, 0))
        self.assertFalse(set(b["x"]) & set(a["x"]))
        # ID de fora do estrato nao conta como ja sorteado
        c = am.sortear_ids({"x": ["x1", "x2", "x3"]}, {"x": 2}, semente=1, ja_sorteados=["z9"])
        self.assertEqual(len(c["x"]), 2)

    def test_sorteio_nao_passa_do_tamanho_do_estrato(self):
        c = am.sortear_ids({"x": ["x1", "x2"]}, {"x": 10}, semente=1)
        self.assertEqual(c["x"], ["x1", "x2"])


if __name__ == "__main__":
    unittest.main()
