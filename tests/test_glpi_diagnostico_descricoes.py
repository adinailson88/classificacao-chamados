"""Testes offline do diagnóstico somente leitura dos 69 Tickets históricos."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import diagnosticar_descricoes_glpi as diag  # noqa: E402
import glpi_client as gc  # noqa: E402


class ClienteDiagnosticoFalso:
    def __init__(self, ticket=None, solucoes=None):
        self.ticket_resposta = ticket
        self.solucoes_resposta = solucoes or []
        self.chamadas = []

    def ticket(self, ticket_id):
        self.chamadas.append(("GET_TICKET", ticket_id))
        return self.ticket_resposta

    def solucoes_ticket(self, ticket_id):
        self.chamadas.append(("GET_SOLUCOES", ticket_id))
        return self.solucoes_resposta


class TesteDiagnosticoDescricoes(unittest.TestCase):
    def test_lista_tem_69_ids_unicos(self):
        self.assertEqual(len(diag.IDS_69), 69)
        self.assertEqual(len(set(diag.IDS_69)), 69)

    def test_ticket_nao_encontrado_nao_tenta_solucao(self):
        cliente = ClienteDiagnosticoFalso(ticket=None)
        resultado = diag.diagnosticar_ticket(cliente, "123")
        self.assertEqual(resultado["status"], "NAO_ENCONTRADO")
        self.assertEqual(cliente.chamadas, [("GET_TICKET", "123")])

    def test_uma_solucao_composta_coluna_d(self):
        cliente = ClienteDiagnosticoFalso(
            ticket={"id": 123, "content": "Descrição original"},
            solucoes=[{"id": 7, "content": "Solução original"}],
        )
        resultado = diag.diagnosticar_ticket(cliente, "123")
        self.assertEqual(resultado["status"], "RECUPERADO")
        self.assertEqual(
            resultado["descricao_composta"],
            "Descrição - Descrição original\n\nSolução - Solução original",
        )
        self.assertEqual(
            cliente.chamadas,
            [("GET_TICKET", "123"), ("GET_SOLUCOES", "123")],
        )

    def test_multiplas_solucoes_nao_sao_escolhidas_silenciosamente(self):
        cliente = ClienteDiagnosticoFalso(
            ticket={"id": 123, "content": "Descrição"},
            solucoes=[
                {"id": 7, "content": "Solução A"},
                {"id": 8, "content": "Solução B"},
            ],
        )
        resultado = diag.diagnosticar_ticket(cliente, "123")
        self.assertEqual(resultado["status"], "MULTIPLAS_SOLUCOES")
        self.assertEqual(resultado["solucao_selecionada"], "")
        self.assertEqual(resultado["descricao_composta"], "")

    def test_sem_solucao_preserva_descricao(self):
        cliente = ClienteDiagnosticoFalso(
            ticket={"id": 123, "content": "Descrição"},
            solucoes=[],
        )
        resultado = diag.diagnosticar_ticket(cliente, "123")
        self.assertEqual(resultado["status"], "RECUPERADO_SEM_SOLUCAO")
        self.assertEqual(
            resultado["descricao_composta"],
            "Descrição - Descrição\n\nSolução - ",
        )

    def test_cliente_solucoes_usa_get(self):
        cliente = gc.GLPIClient("https://exemplo.invalid/apirest.php", "u", "a")
        cliente.session_token = "sessao"
        with patch.object(
            cliente,
            "_request",
            return_value=([{"id": 1, "content": "x"}], {}),
        ) as requisicao:
            solucoes = cliente.solucoes_ticket("123")
        self.assertEqual(len(solucoes), 1)
        self.assertEqual(requisicao.call_args.args[0], "GET")
        self.assertEqual(
            requisicao.call_args.args[1],
            "Ticket/123/ITILSolution",
        )

    def test_resposta_invalida_de_solucoes_falha_fechado(self):
        cliente = gc.GLPIClient("https://exemplo.invalid/apirest.php", "u", "a")
        cliente.session_token = "sessao"
        with patch.object(cliente, "_request", return_value=({"id": 1}, {})):
            with self.assertRaises(gc.GLPIError):
                cliente.solucoes_ticket("123")


if __name__ == "__main__":
    unittest.main()
