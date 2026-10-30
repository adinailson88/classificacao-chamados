from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import trilha_b as tb  # noqa: E402


def _pontos(n, semente, erro_alto=0.02, erro_baixo=0.5):
    rng = random.Random(semente)
    saida = []
    for i in range(n):
        alto = rng.random() < 0.6
        escore = rng.uniform(0.7, 1.0) if alto else rng.uniform(0.0, 0.7)
        saida.append((escore, rng.random() > (erro_alto if alto else erro_baixo), f"g{semente}_{i}"))
    return saida


class TestRiscoTrilhaB(unittest.TestCase):
    def test_divisao_por_grupo_nao_separa_o_mesmo_grupo(self):
        grupos = ["a", "a", "b", "c", "c", "d", "e", "f"]
        treino, cal = tb._dividir_por_grupo(list(range(8)), grupos, 0.5, 3)
        self.assertEqual(sorted(treino + cal), list(range(8)))
        self.assertFalse({grupos[i] for i in treino} & {grupos[i] for i in cal})

    def test_analise_do_cenario_traz_controlado_e_ingenuo(self):
        r = tb.analisar_cenario_risco(_pontos(3000, 1), _pontos(3000, 2), alfas=(0.05,),
                                      reamostragens=30)
        a = r["alvos"]["0.05"]
        self.assertLessEqual(a["controlado"]["erro"], 0.05)
        self.assertEqual(a["controlado"]["taxa_de_violacao"], 0.0)
        self.assertGreaterEqual(a["ingenuo"]["cobertura"], a["controlado"]["cobertura"])
        self.assertIn("erro_limite_superior_cp95", a["controlado"])

    def test_sem_dados_suficientes_nao_ha_limiar(self):
        r = tb.analisar_cenario_risco(_pontos(20, 1), _pontos(100, 2), alfas=(0.05,),
                                      reamostragens=5)
        self.assertIsNone(r["alvos"]["0.05"]["controlado"]["limiar"])


if __name__ == "__main__":
    unittest.main()
