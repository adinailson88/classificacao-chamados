"""Testes offline do diagnóstico somente leitura dos 69 Tickets históricos."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import diagnosticar_descricoes_glpi as diag  # noqa: E402


class ClienteDiagnosticoFalso:
    def __init__(self, ticket=None):
        self.ticket_resposta = ticket
        self.chamadas = []

    def ticket(self, ticket_id):
        self.chamadas.append(("GET_TICKET", ticket_id))
        return self.ticket_resposta


class TesteDiagnosticoDescricoes(unittest.TestCase):
    def test_lista_tem_69_ids_unicos(self):
        self.assertEqual(len(diag.IDS_69), 69)
        self.assertEqual(len(set(diag.IDS_69)), 69)

    def test_ticket_nao_encontrado(self):
        cliente = ClienteDiagnosticoFalso(ticket=None)
        resultado = diag.diagnosticar_ticket(cliente, "123")
        self.assertEqual(resultado["status"], "NAO_ENCONTRADO")
        self.assertEqual(cliente.chamadas, [("GET_TICKET", "123")])

    def test_recupera_content_e_solution_do_ticket_911(self):
        cliente = ClienteDiagnosticoFalso(
            ticket={
                "id": 123,
                "content": "Descrição original",
                "solution": "Solução original",
            }
        )
        resultado = diag.diagnosticar_ticket(cliente, "123")
        self.assertEqual(resultado["status"], "RECUPERADO")
        self.assertEqual(resultado["descricao"], "Descrição original")
        self.assertEqual(resultado["solucao"], "Solução original")
        self.assertEqual(
            resultado["descricao_composta"],
            "Descrição - Descrição original\n\nSolução - Solução original",
        )
        self.assertEqual(cliente.chamadas, [("GET_TICKET", "123")])

    def test_sem_solucao_ainda_recupera_descricao(self):
        cliente = ClienteDiagnosticoFalso(
            ticket={"id": 123, "content": "Descrição", "solution": ""}
        )
        resultado = diag.diagnosticar_ticket(cliente, "123")
        self.assertEqual(resultado["status"], "RECUPERADO")
        self.assertEqual(
            resultado["descricao_composta"],
            "Descrição - Descrição\n\nSolução - ",
        )

    def test_sem_descricao_nao_compõe_coluna_d(self):
        cliente = ClienteDiagnosticoFalso(
            ticket={"id": 123, "content": "", "solution": "Solução"}
        )
        resultado = diag.diagnosticar_ticket(cliente, "123")
        self.assertEqual(resultado["status"], "SEM_DESCRICAO")
        self.assertEqual(resultado["descricao_composta"], "")

    def test_id_de_resposta_divergente_falha_fechado(self):
        cliente = ClienteDiagnosticoFalso(
            ticket={"id": 999, "content": "x", "solution": "y"}
        )
        resultado = diag.diagnosticar_ticket(cliente, "123")
        self.assertEqual(resultado["status"], "RESPOSTA_TICKET_INVALIDA")


if __name__ == "__main__":
    unittest.main()
