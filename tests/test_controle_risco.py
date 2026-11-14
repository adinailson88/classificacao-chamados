from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import controle_risco as cr  # noqa: E402


def _amostra(n, semente, erro_alto=0.02, erro_baixo=0.5):
    """Escore alto quase sempre acerta; escore baixo erra metade das vezes."""
    rng = random.Random(semente)
    escores, acertos = [], []
    for _ in range(n):
        alto = rng.random() < 0.6
        escores.append(rng.uniform(0.7, 1.0) if alto else rng.uniform(0.0, 0.7))
        acertos.append(rng.random() > (erro_alto if alto else erro_baixo))
    return escores, acertos


class TestControleRisco(unittest.TestCase):
    def test_minimo_de_automatizados_sem_erro(self):
        self.assertEqual(cr.confianca_minima_para_zero_erros(0.05, 0.05), 59)

    def test_um_por_grupo_mantem_o_primeiro(self):
        self.assertEqual(cr.um_por_grupo(["a", "b", "a", "c", "b"]), [0, 1, 3])

    def test_sem_dados_suficientes_nao_automatiza(self):
        self.assertIsNone(cr.escolher_limiar([0.9] * 10, [True] * 10, 0.05, 0.05))

    def test_limiar_separa_a_regiao_confiavel(self):
        e, a = _amostra(4000, 1)
        t = cr.escolher_limiar(e, a, 0.05, 0.05)
        self.assertIsNotNone(t)
        self.assertGreaterEqual(t, 0.6)
        teste_e, teste_a = _amostra(4000, 2)
        r = cr.risco_e_cobertura(teste_e, teste_a, t)
        self.assertLessEqual(r["erro"], 0.05)
        self.assertGreater(r["cobertura"], 0.3)

    def test_taxa_de_violacao_fica_abaixo_de_delta(self):
        violacoes = 0
        rodadas = 60
        for s in range(rodadas):
            e, a = _amostra(1500, 100 + s)
            t = cr.escolher_limiar(e, a, 0.05, 0.1)
            te, ta = _amostra(20000, 900 + s)
            r = cr.risco_e_cobertura(te, ta, t)
            if r["erro"] is not None and r["erro"] > 0.05:
                violacoes += 1
        self.assertLessEqual(violacoes / rodadas, 0.1 + 0.08)

    def test_limite_superior_de_clopper_pearson(self):
        self.assertAlmostEqual(cr.limite_superior_clopper_pearson(0, 59, 0.95), 0.0495, places=3)
        self.assertEqual(cr.limite_superior_clopper_pearson(5, 5), 1.0)

    def test_limiar_ingenuo_e_menos_conservador_que_o_controlado(self):
        e, a = _amostra(3000, 5)
        ing = cr.limiar_ingenuo(e, a, 0.05)
        ctl = cr.escolher_limiar(e, a, 0.05, 0.05)
        self.assertIsNotNone(ing)
        self.assertLessEqual(ing, ctl)

    def test_tamanhos_diferentes_geram_erro(self):
        with self.assertRaises(ValueError):
            cr.escolher_limiar([0.1], [True, False])


if __name__ == "__main__":
    unittest.main()
