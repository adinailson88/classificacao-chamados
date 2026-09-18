"""Testes offline da fila e da escrita protegida no GLPI."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import aplicar_correcoes_glpi as app  # noqa: E402
import gerar_fila_correcoes_glpi as fila  # noqa: E402
import glpi_client as gc  # noqa: E402


class ClienteFalso:
    def __init__(self, categoria=1, tipo=2, existe=True, falha_put=False, posterior=None,
                 resposta_put=None, falha_apos_gravar=False, posterior_id=None,
                 falha_get_posterior=False):
        self.categoria = categoria
        self.tipo = tipo
        self.existe = existe
        self.falha_put = falha_put
        self.posterior = posterior
        self.resposta_put = resposta_put
        self.falha_apos_gravar = falha_apos_gravar
        self.posterior_id = posterior_id
        self.falha_get_posterior = falha_get_posterior
        self.puts = []
        self.leituras = 0

    def ticket(self, ticket_id):
        self.leituras += 1
        if self.puts and self.falha_get_posterior:
            raise gc.GLPIError("Falha de leitura posterior")
        if not self.existe:
            return None
        categoria = self.posterior if self.puts and self.posterior is not None else self.categoria
        ident = self.posterior_id if self.puts and self.posterior_id is not None else int(ticket_id)
        return {"id": ident, "itilcategories_id": categoria, "type": self.tipo}

    def corrigir_ticket(self, ticket_id, categoria_id):
        self.puts.append((ticket_id, categoria_id))
        if self.falha_put:
            raise gc.GLPIError("PUT falhou")
        self.categoria = categoria_id
        if self.falha_apos_gravar:
            raise gc.GLPIError("Resposta PUT perdida")
        return self.resposta_put if self.resposta_put is not None else [{"id": int(ticket_id)}]


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

    def test_resposta_documentada_glpi_911(self):
        cliente = ClienteFalso(resposta_put=[{"123": True}])
        resultado = executar(cliente, aplicar=True)
        self.assertEqual(resultado["status_glpi"], "APLICADO")
        self.assertEqual(resultado["erro"], "")
        self.assertEqual(cliente.leituras, 2)

    def test_put_com_erro_mas_get_confirma_destino(self):
        cliente = ClienteFalso(falha_apos_gravar=True)
        resultado = executar(cliente, aplicar=True)
        self.assertEqual(resultado["status_glpi"], "APLICADO")
        self.assertIn("Resposta PUT perdida", resultado["erro"])
        self.assertIn("GET posterior confirmou", resultado["erro"])
        self.assertEqual(cliente.leituras, 2)

    def test_falha_put(self):
        cliente = ClienteFalso(falha_put=True)
        self.assertEqual(executar(cliente, aplicar=True)["status_glpi"], "ERRO")
        self.assertEqual(cliente.leituras, 2)

    def test_get_posterior_divergente(self):
        self.assertEqual(executar(ClienteFalso(posterior=1), aplicar=True)["status_glpi"], "ERRO")

    def test_get_posterior_com_id_divergente(self):
        resultado = executar(ClienteFalso(posterior_id=999), aplicar=True)
        self.assertEqual(resultado["status_glpi"], "ERRO")
        self.assertIn("Ticket", resultado["erro"])

    def test_get_posterior_categoria_desconhecida_registra_id(self):
        resultado = executar(ClienteFalso(posterior=999), aplicar=True)
        self.assertEqual(resultado["status_glpi"], "ERRO")
        self.assertEqual(resultado["categoria_api_depois"], "ID:999")

    def test_put_e_get_com_erros_preserva_ambos(self):
        resultado = executar(ClienteFalso(falha_put=True, falha_get_posterior=True), aplicar=True)
        self.assertEqual(resultado["status_glpi"], "ERRO")
        self.assertIn("PUT falhou", resultado["erro"])
        self.assertIn("Falha de leitura posterior", resultado["erro"])

    def test_resposta_put_invalida_ainda_faz_get(self):
        cliente = ClienteFalso()
        def resposta_atipica(ticket_id, categoria_id):
            cliente.puts.append((ticket_id, categoria_id))
            cliente.categoria = categoria_id
            return None
        cliente.corrigir_ticket = resposta_atipica
        resultado = executar(cliente, aplicar=True)
        self.assertEqual(resultado["status_glpi"], "APLICADO")
        self.assertIn("Resposta PUT sem confirmação", resultado["erro"])
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


class TesteLogNoExecutor(unittest.TestCase):
    def test_modo_aplicar_anexa_log_antes_de_atualizar_fila(self):
        with tempfile.TemporaryDirectory() as pasta:
            raiz = Path(pasta)
            (raiz / "config_experimento.json").write_text(
                json.dumps({"aba_principal": "PRINCIPAL"}), encoding="utf-8")
            sh = MagicMock()
            cliente = ClienteFalso()
            sessao = MagicMock()
            sessao.__enter__.return_value = cliente
            cliente.categorias = lambda: CATEGORIAS
            candidato = {"id_chamado": "123", "situacao_validacao": "ELEGIVEL",
                         "categoria_glpi_planilha": "Origem", "categoria_correta": "Destino"}
            log_ws = MagicMock()
            chamadas = []
            with (patch.object(app, "RAIZ", raiz),
                  patch.object(app.pl, "id_planilha", return_value="planilha"),
                  patch.object(app.pl, "abrir_planilha", return_value=sh),
                  patch.object(app.pl, "ler_valores", return_value=[["cabecalho"]]),
                  patch.object(fila, "ler_fila", return_value=[linha()]),
                  patch.object(fila, "selecionar_candidatos", return_value=[candidato]),
                  patch.object(fila, "preparar_log", return_value=log_ws),
                  patch.object(fila, "anexar_log", side_effect=lambda *args: chamadas.append("log")),
                  patch.object(fila, "atualizar_resultado", side_effect=lambda *args: chamadas.append("fila")),
                  patch.object(app.gc.GLPIClient, "from_env", return_value=sessao)):
                app.main(["--aplicar", "--ids", "123", "--limite", "1"])
            self.assertEqual(chamadas, ["log", "fila"])
            self.assertEqual(cliente.puts, [("123", 2)])


if __name__ == "__main__":
    unittest.main()
