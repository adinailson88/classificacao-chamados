import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from exportar_dashboard import exportar_registros_modelos_da_planilha  # noqa: E402


CAB = ["run_id", "linha_planilha", "id_chamado", "categoria_original",
       "categoria_ia", "confianca", "faixa", "executor", "acerto", "etapa", "data"]


class WorksheetFalsa:
    def __init__(self, valores):
        self.valores = valores

    def get_values(self, _range, value_render_option=None):
        return self.valores


class PlanilhaFalsa:
    def __init__(self, abas):
        self.abas = abas

    def worksheet(self, nome):
        if nome not in self.abas:
            raise KeyError(nome)
        return WorksheetFalsa(self.abas[nome])


class ExportacaoFocadaTest(unittest.TestCase):
    def test_publica_modelo_completo_e_modelo_ausente(self):
        config = {
            "aba_principal": "BASE",
            "multimodelo": {
                "modelos_leves": ["linear_svc"],
                "modelos_pesados": ["transformer_ft"],
                "aba_classificacao": "CLASSIF__{modelo}",
            },
        }
        sh = PlanilhaFalsa({
            "BASE": [["ID Chamado"], [101], [102]],
            "CLASSIF__linear_svc": [
                CAB,
                ["run", 2, 101, "Elétrica", "Elétrica", 0.9, "", "linear_svc", True, 1, ""],
                ["run", 3, 102, "Hidrossanitária", "Elétrica", 0.8, "", "linear_svc", False, 1, ""],
            ],
        })
        with tempfile.TemporaryDirectory() as td, patch(
            "exportar_dashboard.pl.ler_conferencias", return_value={}
        ):
            saida = Path(td)
            contagens, auditoria = exportar_registros_modelos_da_planilha(sh, config, saida)
            self.assertEqual(contagens, {"linear_svc": 2})
            self.assertEqual(auditoria["linear_svc"]["status"], "valido_completo")
            self.assertEqual(auditoria["transformer_ft"]["status"], "ausente")
            registros = json.loads((saida / "registros_linear_svc.json").read_text())
            self.assertEqual(len(registros), 2)
            self.assertNotIn("id_chamado", registros[0])
            self.assertFalse((saida / "registros_transformer_ft.json").exists())

    def test_falha_fechado_sem_ids_atuais(self):
        config = {"aba_principal": "BASE", "multimodelo": {"modelos_leves": []}}
        sh = PlanilhaFalsa({"BASE": [["ID Chamado"]]})
        with tempfile.TemporaryDirectory() as td, patch(
            "exportar_dashboard.pl.ler_conferencias", return_value={}
        ):
            with self.assertRaisesRegex(RuntimeError, "IDs atuais indisponiveis"):
                exportar_registros_modelos_da_planilha(sh, config, Path(td))


if __name__ == "__main__":
    unittest.main()
