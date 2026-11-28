from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import bertimbau_corte_b as b  # noqa: E402


class AuxiliaresTest(unittest.TestCase):
    def test_lotes_cobrem_todos_os_indices_uma_vez(self):
        comp = [5, 50, 7, 49, 6, 51, 8, 48]
        lotes = b.lotes_por_comprimento(comp, 3, random.Random(1))
        todos = sorted(i for lote in lotes for i in lote)
        self.assertEqual(todos, list(range(8)))
        self.assertTrue(all(len(x) <= 3 for x in lotes))

    def test_lotes_agrupam_comprimentos_proximos(self):
        comp = [5, 50, 7, 49, 6, 51]
        for lote in b.lotes_por_comprimento(comp, 3, random.Random(1)):
            valores = [comp[i] for i in lote]
            self.assertLess(max(valores) - min(valores), 10)

    def test_pesos_balanceados(self):
        w = b.pesos_balanceados([0, 0, 0, 1], 2)
        self.assertAlmostEqual(w[0], 4 / (2 * 3))
        self.assertAlmostEqual(w[1], 4 / (2 * 1))

    def test_metricas(self):
        m = b.metricas(["a", "a", "b", "b"], ["a", "b", "b", "b"])
        self.assertEqual(m["acuracia"], 0.75)
        self.assertAlmostEqual(m["macro_f1"], round((0.6667 + 0.8) / 2, 4), places=3)


if __name__ == "__main__":
    unittest.main()
