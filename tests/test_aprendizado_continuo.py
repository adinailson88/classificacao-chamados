from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import aprendizado_continuo as ac  # noqa: E402


class ModeloMemoria:
    """Memoriza o rotulo majoritario por texto; confianca 0.9 se viu o texto, 0.2 se nao."""

    def fit(self, textos, rotulos):
        self.m = dict(zip(textos, rotulos))

    def predict_score(self, textos):
        return ([self.m.get(t, "X") for t in textos],
                [0.9 if t in self.m else 0.2 for t in textos])


def dados():
    textos, rotulos, grupos, datas = [], [], [], []
    for ano in (2021, 2022, 2023):
        for tri in (1, 2, 3, 4):
            for k in range(40):
                t = f"t{k % 20}"
                textos.append(t)
                rotulos.append("A" if int(t[1:]) % 2 else "B")
                grupos.append(t)
                datas.append(f"{ano}-{(tri - 1) * 3 + 1:02d}-10 08:00")
    return textos, rotulos, grupos, datas


class BlocosTest(unittest.TestCase):
    def test_trimestre(self):
        self.assertEqual(ac.trimestre("2022-03-31 10:00"), "2022T1")
        self.assertEqual(ac.trimestre("2022-04-01 10:00"), "2022T2")

    def test_blocos_separam_inicial_e_trimestres(self):
        _, _, _, datas = dados()
        ini, blocos = ac.montar_blocos(datas, 2022)
        self.assertEqual(len(ini), 160)
        self.assertEqual([b for b, _ in blocos][:2], ["2022T1", "2022T2"])
        self.assertEqual(sum(len(i) for _, i in blocos), 320)


class RevisaoTest(unittest.TestCase):
    def test_ativo_escolhe_menor_confianca_fora_da_auditoria(self):
        bloco = list(range(10))
        conf = {i: i / 10 for i in bloco}
        esc = ac.escolher_revisoes("ativo", bloco, {0}, conf, 3, random.Random(1))
        self.assertEqual(esc, [1, 2, 3])

    def test_aleatorio_nao_repete_auditoria_e_completo_pega_tudo(self):
        bloco = list(range(10))
        esc = ac.escolher_revisoes("aleatorio", bloco, {0, 1}, {}, 4, random.Random(1))
        self.assertEqual(len(set(esc)), 4)
        self.assertFalse({0, 1} & set(esc))
        self.assertEqual(len(ac.escolher_revisoes("completo", bloco, {0}, {}, 4, random.Random(1))), 9)
        self.assertEqual(ac.escolher_revisoes("estatico", bloco, {0}, {}, 4, random.Random(1)), [])


class SimulacaoTest(unittest.TestCase):
    def test_sem_vazamento_do_bloco_atual_e_completo_aprende(self):
        textos, rotulos, grupos, datas = dados()
        silencio = lambda *_: None  # noqa: E731
        r = ac.simular(textos, rotulos, grupos, datas, ModeloMemoria, 2022, auditoria=10,
                       revisoes=10, log=silencio)
        self.assertEqual(r["treino_inicial"], 160)
        for est in ac.ESTRATEGIAS:
            self.assertEqual(len(r["estrategias"][est]), 8)
        # o treino inicial ja cobre todos os textos, entao todos acertam; o treino do estatico nao cresce
        est = r["estrategias"]["estatico"]
        self.assertTrue(all(l["treino"] == 160 for l in est))
        comp = r["estrategias"]["completo"]
        self.assertGreater(comp[-1]["treino"], comp[0]["treino"])
        # o treino do bloco k nao inclui nada do bloco k (so rotulos de blocos anteriores)
        self.assertEqual(comp[0]["treino"], 160)
        self.assertEqual(comp[1]["treino"], 160 + 40)

    def test_agregado(self):
        textos, rotulos, grupos, datas = dados()
        r = ac.simular(textos, rotulos, grupos, datas, ModeloMemoria, 2022, auditoria=10,
                       revisoes=10, log=lambda *_: None)
        ag = ac.agregar(r)
        self.assertEqual(ag["completo"]["n"], 320)
        self.assertEqual(ag["completo"]["acuracia"], 1.0)


if __name__ == "__main__":
    unittest.main()
