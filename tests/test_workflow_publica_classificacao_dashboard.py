import unittest
from pathlib import Path

import yaml


RAIZ = Path(__file__).resolve().parents[1]
WORKFLOW = RAIZ / ".github" / "workflows" / "multimodelo_classificacao.yml"


class PublicacaoPeloProdutorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        cls.steps = cls.doc["jobs"]["multimodelo"]["steps"]

    def _step(self, nome):
        return next(s for s in self.steps if s.get("name") == nome)

    def test_exporta_e_publica_depois_da_classificacao(self):
        nomes = [s.get("name") for s in self.steps]
        self.assertLess(nomes.index("Classificar por modelo"),
                        nomes.index("Renovar artefatos sanitizados do dashboard"))
        self.assertLess(nomes.index("Renovar artefatos sanitizados do dashboard"),
                        nomes.index("Publicar artefatos sanitizados do dashboard"))
        self.assertLess(nomes.index("Publicar artefatos sanitizados do dashboard"),
                        nomes.index("Persistir marcador de automacao"))

    def test_so_publica_quando_aplica_na_planilha(self):
        condicao = "${{ github.event_name == 'schedule' || github.event.inputs.aplicar == 'true' }}"
        self.assertEqual(self._step("Renovar artefatos sanitizados do dashboard")["if"], condicao)
        self.assertEqual(self._step("Publicar artefatos sanitizados do dashboard")["if"], condicao)

    def test_comandos_focados(self):
        self.assertEqual(
            self._step("Renovar artefatos sanitizados do dashboard")["run"],
            "python src/exportar_classificacao_dashboard.py",
        )
        self.assertEqual(
            self._step("Publicar artefatos sanitizados do dashboard")["run"],
            "python src/persistir_classificacao_dashboard.py",
        )


if __name__ == "__main__":
    unittest.main()
