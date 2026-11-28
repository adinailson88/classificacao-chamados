from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import cascata_llm as cl  # noqa: E402

CATS = ["Elétrica > Instalações elétricas", "Climatização > Ar condicionado split"]


class MascaraTest(unittest.TestCase):
    def test_remove_dados_pessoais(self):
        t = cl.mascarar("Falar com ana@ufsb.edu.br ou (73) 99988-7766, CPF 123.456.789-09, proc 123456789")
        for trecho in ("ana@", "99988", "123.456", "123456789"):
            self.assertNotIn(trecho, t)

    def test_preserva_texto_tecnico(self):
        self.assertEqual(cl.mascarar("Ar  condicionado\n sala 12"), "Ar condicionado sala 12")


class RespostaTest(unittest.TestCase):
    def test_aceita_categoria_da_lista(self):
        self.assertEqual(cl.interpretar_resposta('{"categoria": "%s"}' % CATS[0], CATS), CATS[0])

    def test_rejeita_categoria_fora_da_lista_ou_lixo(self):
        self.assertIsNone(cl.interpretar_resposta('{"categoria": "Outra"}', CATS))
        self.assertIsNone(cl.interpretar_resposta("sem json", CATS))


class ResumoTest(unittest.TestCase):
    def test_resumo(self):
        itens = [
            {"previsto": "A", "referencia_humana": "A", "llm": "B"},
            {"previsto": "A", "referencia_humana": "B", "llm": "B"},
            {"previsto": "A", "referencia_humana": "B", "llm": None},
        ]
        r = cl.resumir(itens)
        self.assertEqual(r["llm_acerta_e_modelo_erra"], 1)
        self.assertEqual(r["modelo_acerta_e_llm_erra"], 1)
        self.assertEqual(r["respostas_validas"], 2)


if __name__ == "__main__":
    unittest.main()
