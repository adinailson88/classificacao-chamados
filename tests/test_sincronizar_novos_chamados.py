import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import types  # noqa: E402

sys.modules.setdefault("gspread", types.ModuleType("gspread"))
import sincronizar_novos_chamados as s  # noqa: E402

CAB = ["id", "titulo", "categoria", "descricao", "solucao"]


class SelecionarNovosTest(unittest.TestCase):
    def test_insere_so_novo_com_categoria_conhecida(self):
        origem = [CAB,
                  ["1", "ja existe", "Elétrica > Iluminação", "d", ""],
                  ["2026100001", "novo", "Elétrica > Iluminação", "troca", "feito"],
                  ["2019010001", "projeto", "Projeto > Arquitetônico", "d", ""],
                  ["2026100002", "sem categoria", "", "d", ""]]
        novos, resumo = s.selecionar_novos(origem, {"1"}, {"Elétrica > Iluminação"})
        self.assertEqual([r[0] for r in novos], ["2026100001"])
        self.assertEqual(novos[0][3], "Descrição - troca\n\nHistórico / solução - feito")
        self.assertEqual(s.montar_descricao(" aberto ", ""), "aberto")
        self.assertEqual(novos[0][4:], ["", ""])
        self.assertEqual(resumo, {"ja_existentes": 1, "fora_da_taxonomia": 1, "sem_categoria": 1, "acima_do_limite": 0})

    def test_ordem_por_id_sem_duplicatas_e_limite(self):
        origem = [CAB] + [[str(2026100010 - k), "t", "C", "d", ""] for k in range(6)] + [["2026100005", "dup", "C", "d", ""]]
        novos, resumo = s.selecionar_novos(origem, set(), {"C"}, limite=4)
        self.assertEqual([r[0] for r in novos], ["2026100005", "2026100006", "2026100007", "2026100008"])
        self.assertEqual(resumo["acima_do_limite"], 2)

    def test_id_numerico_do_sheets(self):
        self.assertEqual(s.normalizar_id("2026100001.0"), "2026100001")


if __name__ == "__main__":
    unittest.main()
