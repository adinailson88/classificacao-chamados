from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import corte_b as cb  # noqa: E402


def reg(id_, hist, m, q="", titulo="t", desc="d"):
    return {"id": id_, "titulo": titulo, "descricao_glpi": desc,
            "titulo_osm": "", "descricao_osm": "",
            "categoria_historica": hist, "conferencia_glpi": m,
            "categoria_manual": q}


TEMPORAL = {
    "1": {"data_abertura": "2020-01-10 08:00", "campus": "Campus A"},
    "2": {"data_abertura": "2026-07-31 23:00", "campus": "Campus B"},
    "3": {"data_abertura": "2026-08-01 00:05", "campus": "Campus A"},
}


def corte_valido():
    return cb.montar_corte([
        reg("1", "Cat A", "Correto"),
        reg("2", "Cat B", "Errado", "Cat A"),
        reg("3", "Cat A", "Correto"),
    ], TEMPORAL)


class TestCorteB(unittest.TestCase):
    def test_periodo_respeita_o_corte_inclusive_no_ultimo_dia(self):
        periodos = {r["id_chamado"]: r["periodo"] for r in corte_valido()}
        self.assertEqual(periodos, {"1": "historico", "2": "historico",
                                    "3": "prospectivo"})

    def test_referencia_e_fonte_seguem_m_e_q(self):
        por_id = {r["id_chamado"]: r for r in corte_valido()}
        self.assertEqual(por_id["1"]["referencia_humana"], "Cat A")
        self.assertEqual(por_id["1"]["fonte_referencia"], "conferencia_glpi")
        self.assertEqual(por_id["2"]["referencia_humana"], "Cat A")
        self.assertEqual(por_id["2"]["fonte_referencia"], "manual")

    def test_corte_valido_fica_apto(self):
        r = cb.montar_relatorio(corte_valido(), "2026-07-31", "CORTE_B_X")
        self.assertEqual(r["status"], "apto_para_congelar")
        self.assertEqual(r["corpus"]["linhas"], 3)
        self.assertEqual(r["corpus"]["alteracoes_do_rotulo_historico"], 1)
        self.assertEqual(r["temporal"]["por_periodo"],
                         {"historico": 2, "prospectivo": 1})
        self.assertEqual(r["campus"], {"Campus A": 2, "Campus B": 1})

    def test_data_ou_campus_ausente_bloqueia(self):
        corte = cb.montar_corte([reg("9", "Cat A", "Correto")], {})
        p = cb.problemas_do_corte(corte)
        self.assertEqual(p["linhas_sem_data_valida"], 1)
        self.assertEqual(p["linhas_sem_campus"], 1)
        r = cb.montar_relatorio(corte, "2026-07-31", "X")
        self.assertEqual(r["status"], "bloqueado")

    def test_sem_referencia_e_id_duplicado_bloqueiam(self):
        corte = cb.montar_corte([
            reg("1", "Cat A", ""),
            reg("1", "Cat A", "Correto"),
        ], TEMPORAL)
        p = cb.problemas_do_corte(corte)
        self.assertEqual(p["linhas_sem_referencia"], 1)
        self.assertEqual(p["ids_duplicados"], 1)

    def test_data_invalida_nao_vira_periodo(self):
        corte = cb.montar_corte(
            [reg("1", "Cat A", "Correto")],
            {"1": {"data_abertura": "ontem", "campus": "Campus A"}})
        self.assertEqual(corte[0]["periodo"], "")

    def test_hash_entrada_muda_com_o_texto_e_a_referencia_nao(self):
        base = corte_valido()
        outro = cb.montar_corte([
            reg("1", "Cat A", "Correto", titulo="outro"),
            reg("2", "Cat B", "Errado", "Cat A"),
            reg("3", "Cat A", "Correto"),
        ], TEMPORAL)
        a, b = cb.impressoes_digitais(base), cb.impressoes_digitais(outro)
        self.assertNotEqual(a["hash_entrada_modelo"], b["hash_entrada_modelo"])
        self.assertEqual(a["hash_referencia"], b["hash_referencia"])
        self.assertNotEqual(a["hash_corte"], b["hash_corte"])

    def test_hash_e_estavel_e_independe_da_ordem_de_entrada(self):
        regs = [reg("1", "Cat A", "Correto"), reg("2", "Cat B", "Errado", "Cat A"),
                reg("3", "Cat A", "Correto")]
        h1 = cb.impressoes_digitais(cb.montar_corte(regs, TEMPORAL))
        h2 = cb.impressoes_digitais(cb.montar_corte(list(reversed(regs)), TEMPORAL))
        self.assertEqual(h1, h2)

    def test_relatorio_nao_publica_texto_nem_ids(self):
        corte = cb.montar_corte([
            reg("12345", "Cat A", "Correto", titulo="SEGREDO-TITULO",
                desc="SEGREDO-DESCRICAO")], {"12345": {
                    "data_abertura": "2020-01-10 08:00", "campus": "Campus A"}})
        r = cb.montar_relatorio(corte, "2026-07-31", "X")
        texto = json.dumps(r, ensure_ascii=False) + cb.renderizar_markdown(r)
        for proibido in ("SEGREDO-TITULO", "SEGREDO-DESCRICAO", "12345"):
            self.assertNotIn(proibido, texto)

    def test_nao_grava_sobre_artefato_do_artigo_congelado(self):
        with tempfile.TemporaryDirectory() as d:
            raiz = Path(d)
            alvo = cb.RAIZ / "docs" / "dados" / "retreino_canonico.json"
            manifesto = raiz / "m.json"
            manifesto.write_text(json.dumps({"arquivos": [
                {"path": "docs/dados/retreino_canonico.json"}]}), encoding="utf-8")
            with self.assertRaises(RuntimeError):
                cb.garantir_fora_do_congelado(alvo, manifesto)
            cb.garantir_fora_do_congelado(cb.SAIDA_JSON_PADRAO, manifesto)

    def test_saidas_padrao_ficam_fora_dos_protegidos_reais(self):
        cb.garantir_fora_do_congelado(cb.SAIDA_JSON_PADRAO)
        cb.garantir_fora_do_congelado(cb.SAIDA_MD_PADRAO)

    def test_snapshot_recusa_sobrescrever_aba_existente(self):
        class Aba:
            title = "CORTE_B_20261030"

        class Planilha:
            def worksheets(self):
                return [Aba()]

        with self.assertRaises(RuntimeError):
            cb.gravar_snapshot(Planilha(), "CORTE_B_20261030", corte_valido())


if __name__ == "__main__":
    unittest.main()
