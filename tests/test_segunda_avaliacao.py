from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import segunda_avaliacao as s  # noqa: E402


class EstratoTest(unittest.TestCase):
    def test_estratos(self):
        self.assertEqual(s.estrato("X", "X", "X"), "A")
        self.assertEqual(s.estrato("X", "X", "Y"), "B")
        self.assertEqual(s.estrato("X", "Y", "Y"), "C")


class SorteioTest(unittest.TestCase):
    def cand(self):
        return {e: [{"grupo": f"{e}{i % 150}", "id": f"{e}{i}"} for i in range(300)] for e in s.ESTRATOS}

    def test_um_por_grupo_e_tamanho(self):
        r = s.sortear(self.cand(), 100, random.Random(1))
        self.assertEqual(len(r), 300)
        self.assertEqual(len({x["grupo"] for x in r}), 300)

    def test_reprodutivel(self):
        a = [x["id"] for x in s.sortear(self.cand(), 50, random.Random(7))]
        b = [x["id"] for x in s.sortear(self.cand(), 50, random.Random(7))]
        self.assertEqual(a, b)

    def test_erra_se_faltam_grupos(self):
        c = self.cand()
        c["A"] = c["A"][:10]
        with self.assertRaises(ValueError):
            s.sortear(c, 100, random.Random(1))


class KappaTest(unittest.TestCase):
    def test_extremos(self):
        self.assertEqual(s.kappa_cohen(["a", "b", "a", "b"], ["a", "b", "a", "b"]), 1.0)
        self.assertAlmostEqual(s.kappa_cohen(["a", "a", "b", "b"], ["a", "b", "a", "b"]), 0.0)

    def test_resumir(self):
        chave = {"1": {"estrato": "A", "referencia": "x", "historica": "x", "previsto": "x"},
                 "2": {"estrato": "C", "referencia": "y", "historica": "x", "previsto": "y"}}
        aval = [{"id": "1", "categoria": "x"}, {"id": "2", "categoria": "x"}]
        r = s.resumir(aval, chave)
        self.assertEqual(r["por_estrato"]["A"]["coincide_com_referencia"], 1.0)
        self.assertEqual(r["por_estrato"]["C"]["coincide_com_historica"], 1.0)
        self.assertEqual(r["por_estrato"]["C"]["coincide_com_referencia"], 0.0)


if __name__ == "__main__":
    unittest.main()
