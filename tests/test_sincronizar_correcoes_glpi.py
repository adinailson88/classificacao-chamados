import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import sincronizar_correcoes_glpi as sg  # noqa: E402


class WorksheetFake:
    def __init__(self, valores):
        self.valores = valores
        self.updates = []

    def get_values(self, _range, **_kwargs):
        return self.valores

    def row_values(self, linha):
        return self.valores[linha - 1]

    def update(self, **kwargs):
        self.updates.append(kwargs)


def fila(aprovado="SIM"):
    return sg.Correcao(
        linha=2, id_chamado="123", categoria_anterior="Eletrica > Instalacoes",
        categoria_correta="Eletrica > Iluminacao", validado_em="",
        aprovado=aprovado, workflow_executado_em="", sincronizado_em="",
        resultado="PENDENTE", run_url="")


class ClienteFake:
    def __init__(self, categorias=(10, 10)):
        self.categorias = list(categorias)
        self.puts = []

    def obter_chamado(self, _id):
        atual = self.categorias.pop(0) if len(self.categorias) > 1 else self.categorias[0]
        return {"id": 123, "itilcategories_id": atual}

    def atualizar_categoria(self, chamado, categoria_id):
        self.puts.append((chamado, categoria_id))
        self.categorias[-1] = categoria_id


class SincronizacaoGlpiTest(unittest.TestCase):
    def test_url_exige_https_e_completa_apirest(self):
        self.assertEqual(sg.url_api("https://glpi.exemplo"),
                         "https://glpi.exemplo/apirest.php")
        self.assertEqual(sg.url_api("https://glpi.exemplo/apirest.php/"),
                         "https://glpi.exemplo/apirest.php")
        with self.assertRaises(sg.ErroSincronizacao):
            sg.url_api("http://glpi.exemplo")

    def test_fila_rejeita_id_duplicado(self):
        ws = WorksheetFake([
            ["ID Chamado", "Categoria anterior", "Categoria correta", "Validado em",
             "Aprovado para GLPI", "Workflow executado em", "Sincronizado em",
             "Resultado", "Run ID/URL"],
            ["123", "A", "B"], [123.0, "A", "B"],
        ])
        with self.assertRaisesRegex(sg.ErroSincronizacao, "ID duplicado"):
            sg.ler_fila(ws)

    def test_fonte_exige_m_errado_e_mesmas_categorias(self):
        c = fila()
        fonte = {"123": {"categoria_anterior": c.categoria_anterior,
                          "conferencia_glpi": "Errado",
                          "categoria_correta": c.categoria_correta}}
        self.assertIsNone(sg.validar_fonte(c, fonte))
        fonte["123"]["conferencia_glpi"] = "Correto"
        self.assertEqual(sg.validar_fonte(c, fonte), "M NAO ESTA COMO ERRADO")

    def test_catalogo_usa_nome_exato_ativo_e_rejeita_duplicata(self):
        itens = [
            {"id": 1, "completename": "A > B", "is_active": 1},
            {"id": 2, "completename": "A > B", "is_active": 1},
            {"id": 3, "completename": "A > C", "is_active": 0},
            {"id": 4, "completename": "A > D", "is_active": 1},
        ]
        por_nome, por_id = sg.indexar_categorias(itens)
        self.assertNotIn("A > B", por_nome)
        self.assertNotIn("A > C", por_nome)
        self.assertEqual(por_nome["A > D"], 4)
        self.assertEqual(por_id[1], "A > B")

    def test_dry_run_nao_escreve_no_glpi_nem_na_planilha(self):
        c = fila()
        fonte = {"123": {"categoria_anterior": c.categoria_anterior,
                          "conferencia_glpi": "Errado",
                          "categoria_correta": c.categoria_correta}}
        cliente = ClienteFake((10,))
        ws = WorksheetFake([])
        r = sg.processar(c, fonte, cliente,
                         {c.categoria_correta: 20}, {10: c.categoria_anterior},
                         False, ws, "run")
        self.assertEqual(r.resultado, "DRY-RUN OK")
        self.assertEqual(cliente.puts, [])
        self.assertEqual(ws.updates, [])

    def test_aplicar_rele_e_verifica_categoria(self):
        c = fila()
        fonte = {"123": {"categoria_anterior": c.categoria_anterior,
                          "conferencia_glpi": "Errado",
                          "categoria_correta": c.categoria_correta}}
        cliente = ClienteFake((10, 10, 20))
        ws = WorksheetFake([
            [], ["123", c.categoria_anterior, c.categoria_correta, "", "SIM", "", "", "PENDENTE"]
        ])
        r = sg.processar(c, fonte, cliente,
                         {c.categoria_correta: 20},
                         {10: c.categoria_anterior, 20: c.categoria_correta},
                         True, ws, "run")
        self.assertEqual(r.resultado, "ATUALIZADO")
        self.assertEqual(cliente.puts, [("123", 20)])
        self.assertTrue(r.sincronizado_em)

    def test_aplicar_filtra_apenas_aprovados(self):
        correcoes = [fila("SIM"), sg.Correcao(**{**fila("NAO").__dict__, "id_chamado": "124"})]
        self.assertEqual([c.id_chamado for c in sg.selecionar(correcoes, set(), True, 0)],
                         ["123"])

    def test_main_bloqueia_aplicacao_sem_confirmacao_literal(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(sg.ErroSincronizacao, "confirmacao"):
                sg.main(["--aplicar"])

    def test_conflito_impede_put(self):
        c = fila()
        fonte = {"123": {"categoria_anterior": c.categoria_anterior,
                          "conferencia_glpi": "Errado",
                          "categoria_correta": c.categoria_correta}}
        cliente = ClienteFake((30,))
        ws = WorksheetFake([])
        r = sg.processar(c, fonte, cliente,
                         {c.categoria_correta: 20},
                         {10: c.categoria_anterior, 30: "Outra > Categoria"},
                         False, ws, "run")
        self.assertEqual(r.resultado, "CONFLITO - GLPI ALTERADO APOS VALIDACAO")
        self.assertEqual(cliente.puts, [])


if __name__ == "__main__":
    unittest.main()
