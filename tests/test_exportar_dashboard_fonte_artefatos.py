import json
import sys
import tempfile
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from exportar_dashboard import carregar_registros_modelos_de_artefatos  # noqa: E402


REGISTRO = {"l": "2", "g": "Elétrica", "m": "Corretiva", "o": "Elétrica",
            "p": "Elétrica", "c": 0.9, "f": "entre_70_95", "e": "linear_svc",
            "k": 1, "v": ""}


class FonteArtefatosDashboardTest(unittest.TestCase):
    def _gravar_auditoria(self, base, modelos):
        (base / "registros_modelos_auditoria.json").write_text(
            json.dumps({"modelos": modelos}), encoding="utf-8")

    def test_aceita_completo_e_ausente_sem_ler_planilha(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / "registros_linear_svc.json").write_text(
                json.dumps([REGISTRO]), encoding="utf-8")
            self._gravar_auditoria(base, {
                "linear_svc": {"status": "valido_completo", "ids_unicos": 1,
                               "ids_invalidos": 0},
                "transformer_ft": {"status": "ausente", "ids_unicos": 0,
                                   "ids_invalidos": 0},
            })
            contagens, auditoria = carregar_registros_modelos_de_artefatos(
                base, ["linear_svc", "transformer_ft"])
            self.assertEqual(contagens, {"linear_svc": 1})
            self.assertEqual(auditoria["transformer_ft"]["status"], "ausente")

    def test_recusa_contagem_divergente(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / "registros_linear_svc.json").write_text(
                json.dumps([REGISTRO]), encoding="utf-8")
            self._gravar_auditoria(base, {
                "linear_svc": {"status": "valido_completo", "ids_unicos": 2,
                               "ids_invalidos": 0},
            })
            with self.assertRaisesRegex(ValueError, "contagem"):
                carregar_registros_modelos_de_artefatos(base, ["linear_svc"])

    def test_recusa_id_real_no_artefato(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            registro = dict(REGISTRO, id_chamado="123")
            (base / "registros_linear_svc.json").write_text(
                json.dumps([registro]), encoding="utf-8")
            self._gravar_auditoria(base, {
                "linear_svc": {"status": "valido_completo", "ids_unicos": 1,
                               "ids_invalidos": 0},
            })
            with self.assertRaisesRegex(ValueError, "campo nao permitido"):
                carregar_registros_modelos_de_artefatos(base, ["linear_svc"])

    def test_recusa_ausente_se_arquivo_obsoleto_existir(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / "registros_transformer_ft.json").write_text("[]", encoding="utf-8")
            self._gravar_auditoria(base, {
                "transformer_ft": {"status": "ausente", "ids_unicos": 0,
                                   "ids_invalidos": 0},
            })
            with self.assertRaisesRegex(ValueError, "ausente inconsistente"):
                carregar_registros_modelos_de_artefatos(base, ["transformer_ft"])


if __name__ == "__main__":
    unittest.main()
