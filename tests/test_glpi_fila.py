#!/usr/bin/env python3
"""Testes offline da fila fixa de correcoes do GLPI."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import gerar_fila_correcoes_glpi as fila  # noqa: E402


CAB = [
    "TÍTULO", "CATEGORIA CORRETA MANUAL", "ID Chamado", "CONFERÊNCIA IA - 2",
    "Classificação IA - 2", "CONFERÊNCIA IA", "Classificação IA",
    "CONFERÊNCIA GLPI", "CATEGORIA COMPLETA",
]


def linha(ident, q="Destino", n="", p="", ia="IA", reclass="Reclass"):
    return ["Titulo privado", q, ident, p, reclass, n, ia, "Errado", "Origem"]


class TestSelecao(unittest.TestCase):
    def test_cabecalhos_reordenados_e_id_como_chave(self):
        candidatos = fila.selecionar_candidatos([CAB, linha(123.0)])
        self.assertEqual(len(candidatos), 1)
        self.assertEqual(candidatos[0]["id_chamado"], "123")
        self.assertEqual(candidatos[0]["categoria_correta"], "Destino")
        self.assertEqual(candidatos[0]["situacao_validacao"], "ELEGIVEL")

    def test_conflito_n_ou_p_confirmando_categoria_diferente(self):
        candidatos = fila.selecionar_candidatos([
            CAB, linha(1, n="Correto"), linha(2, p="Correto"),
        ])
        self.assertEqual([c["situacao_validacao"] for c in candidatos],
                         ["CONFLITO", "CONFLITO"])

    def test_marca_conflito_canonico_sem_trocar_nome_exato_da_fila(self):
        with patch.object(fila.pl, "normalizar_categoria",
                          side_effect=lambda x: "Atual" if x in {"Antigo", "Atual"} else x):
            candidatos = fila.selecionar_candidatos([
                CAB, ["T", "Atual", 3, "", "", "", "", "Errado", "Antigo"],
            ])
        self.assertEqual(candidatos[0]["categoria_correta"], "Atual")
        self.assertEqual(candidatos[0]["situacao_validacao"], "CONFLITO")

    def test_rejeita_id_duplicado_mesmo_fora_dos_candidatos(self):
        nao_candidato = linha(9)
        nao_candidato[CAB.index("CONFERÊNCIA GLPI")] = "Correto"
        with self.assertRaisesRegex(ValueError, "duplicado"):
            fila.selecionar_candidatos([CAB, linha(9), nao_candidato])


class TestUpsert(unittest.TestCase):
    def test_aprovacao_e_auditoria_preservadas_por_id(self):
        original = fila.upsert_fila([], fila.selecionar_candidatos([CAB, linha(4)]))[0]
        original.update(aprovado_glpi=True, status_glpi="APLICADO",
                        categoria_api_antes="Origem", categoria_api_depois="Destino",
                        data_execucao="17/09/2026 10:00", erro="")
        novo = dict(original, categoria_correta="Outro", titulo="Titulo alterado")
        mesclado = fila.upsert_fila([original], [novo])[0]
        self.assertIs(mesclado["aprovado_glpi"], True)
        self.assertEqual(mesclado["categoria_correta"], "Destino")
        self.assertEqual(mesclado["status_glpi"], "APLICADO")
        self.assertEqual(mesclado["data_execucao"], "17/09/2026 10:00")
        self.assertEqual(mesclado["situacao_validacao"], "CONFLITO")

    def test_aprovado_ausente_da_origem_fica_bloqueado(self):
        original = fila.upsert_fila([], fila.selecionar_candidatos([CAB, linha(5)]))[0]
        original["aprovado_glpi"] = True
        mesclado = fila.upsert_fila([original], [])[0]
        self.assertIs(mesclado["aprovado_glpi"], True)
        self.assertEqual(mesclado["situacao_validacao"], "CONFLITO")


class TestEscritaIsolada(unittest.TestCase):
    def setUp(self):
        self.sh = MagicMock()
        self.ws = self.sh.worksheet.return_value
        self.ws.id = 77
        self.ws.row_values.return_value = list(fila.COLUNAS_FILA)
        self.registro = fila.upsert_fila([], fila.selecionar_candidatos([CAB, linha(6)]))[0]
        self.registro["aprovado_glpi"] = True
        self.bloco = [list(fila.COLUNAS_FILA),
                      [self.registro[c] for c in fila.COLUNAS_FILA]]

    def test_upsert_so_escreve_na_aba_fila_sem_checkbox_existente(self):
        with patch.object(fila.pl, "ler_valores", side_effect=[self.bloco, [["id_chamado"], [6]]]):
            fila.escrever_fila(self.sh, [self.registro])
        self.sh.worksheet.assert_called_with(fila.ABA_FILA)
        intervalos = [item["range"] for item in self.ws.batch_update.call_args.args[0]]
        self.assertEqual(intervalos, ["A2:E2", "G2:L2"])
        self.assertNotIn("F2", " ".join(intervalos))

    def test_resultado_so_escreve_g_l_e_exige_checkbox_booleano(self):
        resultado = dict(self.registro, status_glpi="APLICADO")
        with patch.object(fila.pl, "ler_valores", return_value=self.bloco):
            fila.atualizar_resultado(self.sh, resultado)
        self.assertEqual(self.ws.batch_update.call_args.args[0][0]["range"], "G2:L2")
        self.registro["aprovado_glpi"] = "TRUE"
        bloco_textual = [self.bloco[0], [self.registro[c] for c in fila.COLUNAS_FILA]]
        with patch.object(fila.pl, "ler_valores", return_value=bloco_textual):
            with self.assertRaises(ValueError):
                fila.atualizar_resultado(self.sh, resultado)


if __name__ == "__main__":
    unittest.main()
