from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import validacao_ufrn as vu  # noqa: E402

CABECALHO = '"numero";"ano";"divisao";"id_unidade_requisitante";"nome_unidade_requisitante";' \
            '"id_unidade_custo";"nome_unidade_custo";"data_cadastro";"descricao";"local";' \
            '"usuario";"status"\n'


def csv_falso(n: int = 40) -> str:
    divisoes = ["Serviços Gerais", "Instalações Elétricas e Telecomunicações", "Viário"]
    linhas = [CABECALHO]
    for i in range(n):
        d = divisoes[i % 3]
        ano = 2021 + i % 4
        linhas.append(f'"{i}";"{ano}";"{d}";"1";"U";"1";"U";"01/01/{ano}";'
                      f'"reparo numero {i} no predio principal";"sala {i}";"fulano";"FINALIZADA"\n')
    linhas.append('"900";"2025";"Viário";"1";"U";"1";"U";"01/01/2025";"curto";"x";"u";"F"\n')
    linhas.append('"901";"2025";"";"1";"U";"1";"U";"01/01/2025";"sem divisao no registro";"x";"u";"F"\n')
    return "".join(linhas)


class TestValidacaoUfrn(unittest.TestCase):
    def _linhas(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "ufrn.csv"
            p.write_text(csv_falso(), encoding="utf-8")
            return vu.ler_ufrn(p)

    def test_leitura_descarta_a_coluna_de_usuario(self):
        linhas = self._linhas()
        self.assertEqual(set(linhas[0]), set(vu.COLUNAS_USADAS))
        self.assertNotIn("usuario", linhas[0])

    def test_leitura_recusa_csv_sem_as_colunas(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.csv"
            p.write_text('"a";"b"\n"1";"2"\n', encoding="utf-8")
            with self.assertRaises(RuntimeError):
                vu.ler_ufrn(p)

    def test_amostra_estratificada_sem_curtos_sem_vazios_e_deterministica(self):
        linhas = self._linhas()
        a = vu.amostrar(linhas, por_divisao=5, ano_minimo=2022, semente=7)
        self.assertEqual(a, vu.amostrar(linhas, por_divisao=5, ano_minimo=2022, semente=7))
        por = {}
        for x in a:
            por[x["divisao"]] = por.get(x["divisao"], 0) + 1
            self.assertGreaterEqual(int(x["ano"]), 2022)
            self.assertGreaterEqual(len(x["descricao"].split()), 4)
        self.assertTrue(all(v <= 5 for v in por.values()))
        self.assertEqual(len(por), 3)
        self.assertNotIn("", por)

    def test_concordancia_usa_a_correspondencia_proposta(self):
        self.assertEqual(vu.concorda("Elétrica > Instalações elétricas",
                                     "Instalações Elétricas e Telecomunicações"), "S")
        self.assertEqual(vu.concorda("Climatização > Ar condicionado split", "Viário"), "N")
        self.assertEqual(vu.concorda("Manutenção Preventiva > Gerador", "Serviços Gerais"), "")

    def test_resumo_conta_so_o_que_tem_correspondencia(self):
        amostra = [{"divisao": "Serviços Gerais"}, {"divisao": "Viário"},
                   {"divisao": "Serviços Gerais"}]
        prev = {"m": ["Estrutura Predial > Alvenaria", "Elétrica > X",
                      "Manutenção Preventiva > Gerador"]}
        r = vu.resumir(amostra, prev)["modelos"]["m"]
        self.assertEqual(r["n_com_correspondencia"], 2)
        self.assertEqual(r["previsoes_sem_correspondencia"], 1)
        self.assertEqual(r["concordancia_com_correspondencia"], 0.5)


if __name__ == "__main__":
    unittest.main()
