"""Testes offline da fila e da escrita protegida no GLPI."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import aplicar_correcoes_glpi as app  # noqa: E402
import glpi_client as gc  # noqa: E402


class ClienteFalso:
    def __init__(self, categoria=1, tipo=2, existe=True, falha_put=False, posterior=None):
        self.categoria = categoria
        self.tipo = tipo
        self.existe = existe
        self.falha_put = falha_put
        self.posterior = posterior
        self.puts = []
        self.leituras = 0

    def ticket(self, ticket_id):
        self.leituras += 1
        if not self.existe:
            return None
        categoria = self.posterior if self.puts and self.posterior is not None else self.categoria
        return {"id": int(ticket_id), "itilcategories_id": categoria, "type": self.tipo}

    def corrigir_ticket(self, ticket_id, categoria_id):
        self.puts.append((ticket_id, categoria_id))
        if self.falha_put:
            raise gc.GLPIError("PUT falhou")
        self.categoria = categoria_id
        return [{"id": int(ticket_id)}]


CATEGORIAS = [
    {"id": 1, "completename": "Origem", "is_request": 1, "is_incident": 1},
    {"id": 2, "completename": "Destino", "is_request": 1, "is_incident": 0},
]


def linha(**mudancas):
    base = {"id_chamado": "123", "categoria_glpi_planilha": "Origem",
            "categoria_correta": "Destino", "situacao_validacao": "ELEGIVEL",
            "aprovado_glpi": True, "status_glpi": ""}
    base.update(mudancas)
    return base


def executar(cliente=None, categorias=None, registro=None, aplicar=False):
    por_nome, por_id = app.mapa_categorias(CATEGORIAS if categorias is None else categorias)
    return app.executar_linha(registro or linha(), cliente or ClienteFalso(),
                              por_nome, por_id, aplicar=aplicar)


class TesteAplicacao(unittest.TestCase):
    def test_aprovacao_false(self):
        cliente = ClienteFalso()
        self.assertEqual(executar(cliente, registro=linha(aprovado_glpi=False), aplicar=True)["status_glpi"], "")
        self.assertEqual(cliente.puts, [])

    def test_texto_true_nao_substitui_checkbox(self):
        cliente = ClienteFalso()
        self.assertEqual(executar(cliente, registro=linha(aprovado_glpi="TRUE"), aplicar=True)["status_glpi"], "")
        self.assertEqual(cliente.puts, [])

    def test_conflito(self):
        self.assertEqual(executar(registro=linha(situacao_validacao="CONFLITO"), aplicar=True)["status_glpi"],
                         "BLOQUEADO_VALIDACAO")

    def test_ticket_inexistente(self):
        self.assertEqual(executar(ClienteFalso(existe=False), aplicar=True)["status_glpi"], "ERRO")

    def test_categoria_inexistente(self):
        self.assertEqual(executar(categorias=CATEGORIAS[:1], aplicar=True)["status_glpi"],
                         "BLOQUEADO_CATEGORIA")

    def test_categoria_ambigua(self):
        cats = CATEGORIAS + [dict(CATEGORIAS[1], id=3)]
        self.assertEqual(executar(categorias=cats, aplicar=True)["status_glpi"], "BLOQUEADO_CATEGORIA")

    def test_correspondencia_exata(self):
        self.assertEqual(executar(registro=linha(categoria_correta="destino"), aplicar=True)["status_glpi"],
                         "BLOQUEADO_CATEGORIA")

    def test_ja_corrigido(self):
        cliente = ClienteFalso(categoria=2)
        self.assertEqual(executar(cliente, aplicar=True)["status_glpi"], "JA_APLICADO")
        self.assertEqual(cliente.puts, [])

    def test_divergencia_depois_da_aprovacao(self):
        cliente = ClienteFalso(categoria=3)
        self.assertEqual(executar(cliente, aplicar=True)["status_glpi"], "BLOQUEADO_DIVERGENCIA")
        self.assertEqual(cliente.puts, [])

    def test_fonte_humana_alterada_depois_da_aprovacao(self):
        cliente = ClienteFalso()
        por_nome, por_id = app.mapa_categorias(CATEGORIAS)
        resultado = app.executar_linha(linha(), cliente, por_nome, por_id,
                                       aplicar=True, fonte_valida=False)
        self.assertEqual(resultado["status_glpi"], "BLOQUEADO_VALIDACAO")
        self.assertEqual(cliente.puts, [])

    def test_tipo_incompativel(self):
        cliente = ClienteFalso(tipo=1)
        self.assertEqual(executar(cliente, aplicar=True)["status_glpi"], "BLOQUEADO_TIPO")
        self.assertEqual(cliente.puts, [])

    def test_dry_run(self):
        cliente = ClienteFalso()
        self.assertEqual(executar(cliente)["status_glpi"], "DRY_RUN")
        self.assertEqual(cliente.puts, [])

    def test_put_e_get_posterior(self):
        cliente = ClienteFalso()
        self.assertEqual(executar(cliente, aplicar=True)["status_glpi"], "APLICADO")
        self.assertEqual(cliente.puts, [("123", 2)])

    def test_falha_put(self):
        cliente = ClienteFalso(falha_put=True)
        self.assertEqual(executar(cliente, aplicar=True)["status_glpi"], "ERRO")
        self.assertEqual(cliente.leituras, 2)

    def test_get_posterior_divergente(self):
        self.assertEqual(executar(ClienteFalso(posterior=1), aplicar=True)["status_glpi"], "ERRO")

    def test_resposta_put_invalida_ainda_faz_get(self):
        cliente = ClienteFalso()
        cliente.corrigir_ticket = lambda ticket_id, categoria_id: None
        self.assertEqual(executar(cliente, aplicar=True)["status_glpi"], "ERRO")
        self.assertEqual(cliente.leituras, 2)

    def test_idempotencia(self):
        cliente = ClienteFalso()
        primeira = executar(cliente, aplicar=True)
        segunda = executar(cliente, registro=primeira, aplicar=True)
        self.assertEqual(segunda["status_glpi"], "APLICADO")
        self.assertEqual(len(cliente.puts), 1)

    def test_tokens_nao_aparecem_em_erro_http(self):
        cliente = gc.GLPIClient("https://exemplo.invalid/apirest.php", "user-secreto", "app-secreto")
        with patch.object(gc, "urlopen", side_effect=gc.URLError("user-secreto app-secreto")):
            with self.assertRaises(gc.GLPIError) as contexto:
                cliente._request("GET", "initSession", auth=False)
        self.assertNotIn("secreto", str(contexto.exception))

    def test_paginacao_categorias_respeita_content_range(self):
        cliente = gc.GLPIClient("https://exemplo.invalid/apirest.php", "u", "a")
        paginas = [([{"id": n} for n in range(50)], {"Content-Range": "0-49/75"}),
                   ([{"id": n} for n in range(50, 75)], {"Content-Range": "50-74/75"})]
        with patch.object(cliente, "_request", side_effect=paginas) as requisicao:
            self.assertEqual(len(cliente.categorias()), 75)
        self.assertIn("range=50-149", requisicao.call_args_list[1].args[1])


if __name__ == "__main__":
    unittest.main()
