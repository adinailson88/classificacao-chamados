#!/usr/bin/env python3
"""Testes de `classificar_com_historico`: montagem do texto (B+D+E+F+R), teste de McNemar,
avaliação fora da amostra e o gate de alinhamento antes de gravar a coluna S."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import classificar_com_historico as ch  # noqa: E402

CAB = ["ID Chamado", "TÍTULO", "CATEGORIA COMPLETA", "DESCRIÇÃO GLPI", "TÍTULO O.S.M.",
       "DESCRIÇÃO O.S.M.", "Classificação IA", "HISTÓRICO GLPI"]
IDX = {ch.norm(n): i for i, n in enumerate(CAB)}


class MontarTextoTest(unittest.TestCase):
    def test_sem_historico_usa_b_d_e_f(self):
        linha = ["1", "Titulo", "Cat", "Desc", "TituloOS", "DescOS", "", "[01/01/2026 10:00] Acompanhamento: oi"]
        self.assertEqual(ch.montar_texto(linha, IDX, False), "Titulo\nDesc\nTituloOS\nDescOS")

    def test_com_historico_acrescenta_r_no_fim(self):
        linha = ["1", "Titulo", "Cat", "Desc", "", "", "", "Conversa"]
        self.assertEqual(ch.montar_texto(linha, IDX, True), "Titulo\nDesc\nConversa")

    def test_e_f_so_entram_quando_existem(self):
        linha = ["1", "Titulo", "Cat", "Desc", "", "", "", ""]
        self.assertEqual(ch.montar_texto(linha, IDX, True), "Titulo\nDesc")

    def test_marcadores_do_coletor_nao_entram_no_texto(self):
        for marca in ("(sem interações)", "(indisponível: HTTP 404)", "  "):
            linha = ["1", "Titulo", "Cat", "Desc", "", "", "", marca]
            self.assertEqual(ch.montar_texto(linha, IDX, True), "Titulo\nDesc")

    def test_variante_limpa_tira_data_tipo_login_e_anexos(self):
        r = ("[12/11/2026 09:32] Acompanhamento (joao.reis): Anderson,\n\nFavor executar.\n\n"
             "[12/11/2026 13:56] Solução (joao.reis) [privado]: O serviço foi executado.\n\n"
             "Documento adicionado: Documento do Chamado 1 - foto.jpeg")
        linha = ["1", "Titulo", "Cat", "Desc", "", "", "", r]
        txt = ch.montar_texto(linha, IDX, "limpo")
        self.assertIn("Favor executar.", txt)
        self.assertIn("O serviço foi executado.", txt)
        for ruido in ("joao.reis", "12/11/2026", "Acompanhamento", "Documento adicionado", "[privado]"):
            self.assertNotIn(ruido, txt)

    def test_variante_bruta_mantem_o_historico_como_esta(self):
        r = "[12/11/2026 09:32] Acompanhamento (joao.reis): Favor executar."
        linha = ["1", "Titulo", "Cat", "Desc", "", "", "", r]
        self.assertTrue(ch.montar_texto(linha, IDX, "bruto").endswith(r))
        self.assertEqual(ch.montar_texto(linha, IDX, True), ch.montar_texto(linha, IDX, "bruto"))

    def test_linha_curta_nao_quebra(self):
        self.assertEqual(ch.montar_texto(["1", "So titulo"], IDX, True), "So titulo")


class McNemarTest(unittest.TestCase):
    def test_sem_discordantes_p_um(self):
        self.assertEqual(ch.mcnemar_exato(0, 0), 1.0)

    def test_empate_p_um(self):
        self.assertEqual(ch.mcnemar_exato(5, 5), 1.0)

    def test_diferenca_grande_p_pequeno(self):
        self.assertLess(ch.mcnemar_exato(0, 20), 0.001)

    def test_simetrico(self):
        self.assertEqual(ch.mcnemar_exato(3, 9), ch.mcnemar_exato(9, 3))


class AvaliarTest(unittest.TestCase):
    def test_conta_acertos_e_discordantes_so_nos_validados(self):
        linhas = [2, 3, 4, 5]
        verdade = {2: "A", 3: "B", 4: "C"}  # linha 5 sem verdade validada
        base = ["A", "X", "C", "Z"]
        com_r = ["A", "B", "Y", "Z"]
        m = ch.avaliar(linhas, base, com_r, [True, True, False, False], verdade,
                       ["A", "A", "A", "A"], ["A", "", "", ""])
        self.assertEqual(m["validados"], 3)
        self.assertEqual(m["acerto_sem_R_fora_da_amostra"], round(2 / 3, 4))
        self.assertEqual(m["acerto_com_R_fora_da_amostra"], round(2 / 3, 4))
        self.assertEqual(m["so_com_R_acerta"], 1)  # linha 3
        self.assertEqual(m["so_sem_R_acerta"], 1)  # linha 4
        self.assertEqual(m["validados_com_historico_util"], 2)
        self.assertEqual(m["acerto_coluna_G_atual"], 1.0)
        self.assertEqual(m["mudou_predicao_total"], 2)

    def test_sem_validados_nao_divide_por_zero(self):
        m = ch.avaliar([2], ["A"], ["A"], [False], {}, ["A"], [""])
        self.assertEqual(m["validados"], 0)
        self.assertIsNone(m["acerto_com_R_fora_da_amostra"])


class ForaDaAmostraTest(unittest.TestCase):
    def test_cada_chamado_e_previsto_por_modelo_que_nao_o_viu(self):
        textos = [f"ar condicionado split sala {i}" if i % 2 == 0 else f"vazamento torneira banheiro {i}" for i in range(40)]
        rotulos = ["Climatização" if i % 2 == 0 else "Hidráulica" for i in range(40)]
        preds, confs = ch.prever_fora_da_amostra(textos, rotulos, 5, 42)
        self.assertEqual(len(preds), 40)
        self.assertTrue(all(p for p in preds))
        self.assertTrue(all(0.0 <= c <= 1.0 for c in confs))
        self.assertGreaterEqual(sum(p == r for p, r in zip(preds, rotulos)) / 40, 0.9)


class _WsFalso:
    col_count = 20

    def __init__(self, coluna_a):
        self.coluna_a = coluna_a
        self.gravacoes = []

    def get_values(self, range_name=None, *a, **k):  # noqa: ARG002
        return [[v] for v in self.coluna_a]

    def update(self, range_name, values, value_input_option=None):  # noqa: ARG002
        self.gravacoes.append((range_name, values))


class GateAlinhamentoTest(unittest.TestCase):
    def test_aborta_e_nao_grava_se_o_id_mudou_de_linha(self):
        ws = _WsFalso(["10", "99", "30"])  # linha 3 agora tem outro id
        with self.assertRaises(RuntimeError):
            ch.conferir_alinhamento(ws, {2: "10", 3: "20", 4: "30"})
        self.assertEqual(ws.gravacoes, [])

    def test_passa_quando_alinhado(self):
        ch.conferir_alinhamento(_WsFalso(["10", "20", "30"]), {2: "10", 3: "20", 4: "30"})


if __name__ == "__main__":
    unittest.main()
