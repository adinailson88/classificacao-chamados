from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import figuras_pesos_trilha_b as f  # noqa: E402


class TermosTest(unittest.TestCase):
    def test_maiores_pesos_so_entre_as_palavras(self):
        pesos = [0.5, -1.0, 2.0, 0.1, 9.0, -9.0]
        nomes = ["a", "b", "c", "d", "char1", "char2"]
        pos, neg = f.termos_de_maior_peso(pesos, nomes, n_palavras=4, positivos=2, negativos=1)
        self.assertEqual([t for t, _ in pos], ["c", "a"])
        self.assertEqual([t for t, _ in neg], ["b"])

    def test_paginar(self):
        self.assertEqual(f.paginar(list(range(7)), 3), [[0, 1, 2], [3, 4, 5], [6]])

    def test_formato_numerico(self):
        self.assertEqual(f.numero(1.2345), "+1,23")
        self.assertEqual(f.numero(-0.5), "−0,50")


if __name__ == "__main__":
    unittest.main()
