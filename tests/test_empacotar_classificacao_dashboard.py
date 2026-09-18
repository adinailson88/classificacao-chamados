import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from empacotar_classificacao_dashboard import empacotar  # noqa: E402


class EmpacotarClassificacaoDashboardTest(unittest.TestCase):
    def test_copia_jsons_sanitizados_e_registra_hash(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            origem = base / "docs" / "dados"
            destino = base / "artefatos"
            origem.mkdir(parents=True)
            config = base / "config.json"
            config.write_text(json.dumps({"multimodelo": {
                "modelos_leves": ["linear_svc"], "modelos_pesados": ["lstm"]
            }}), encoding="utf-8")
            payload = [{"l": "2", "o": "Elétrica", "p": "Elétrica", "c": 0.97}]
            bruto = json.dumps(payload, ensure_ascii=False)
            (origem / "registros_linear_svc.json").write_text(bruto, encoding="utf-8")
            (origem / "registros_modelos_auditoria.json").write_text(json.dumps({
                "modelos": {"linear_svc": {
                    "registros_brutos": 3,
                    "ids_unicos": 1,
                    "duplicados_descartados": 2,
                    "ids_fora_base_descartados": 0,
                    "ids_invalidos": 0,
                    "ids_esperados": 1,
                    "status": "valido_completo",
                }, "lstm": {
                    "registros_brutos": 0,
                    "ids_unicos": 0,
                    "duplicados_descartados": 0,
                    "ids_fora_base_descartados": 0,
                    "ids_invalidos": 0,
                    "ids_esperados": 1,
                    "status": "ausente",
                }}
            }), encoding="utf-8")

            manifesto = empacotar(config, origem, destino)

            self.assertEqual(len(manifesto["arquivos"]), 1)
            self.assertEqual(manifesto["ausentes"], ["registros_lstm.json"])
            self.assertFalse(manifesto["contem_id_chamado"])
            self.assertFalse(manifesto["contem_texto_chamado"])
            self.assertEqual(manifesto["arquivos"][0]["registros"], 1)
            self.assertEqual(manifesto["arquivos"][0]["registros_brutos"], 3)
            self.assertEqual(manifesto["arquivos"][0]["duplicados_descartados"], 2)
            self.assertEqual(manifesto["arquivos"][0]["status"], "valido_completo")
            esperado = hashlib.sha256(bruto.encode("utf-8")).hexdigest()
            self.assertEqual(manifesto["arquivos"][0]["sha256"], esperado)
            self.assertEqual(
                json.loads((destino / "registros_linear_svc.json").read_text(encoding="utf-8")),
                payload,
            )

    def test_rejeita_nome_de_modelo_que_possa_escapar_do_diretorio(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            config = base / "config.json"
            config.write_text(json.dumps({"multimodelo": {
                "modelos_leves": ["../segredo"], "modelos_pesados": []
            }}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "modelo invalido"):
                empacotar(config, base / "origem", base / "destino")

    def test_bloqueia_id_real_no_json_publico(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            origem = base / "origem"
            origem.mkdir()
            config = base / "config.json"
            config.write_text(json.dumps({"multimodelo": {
                "modelos_leves": ["linear_svc"], "modelos_pesados": []
            }}), encoding="utf-8")
            (origem / "registros_linear_svc.json").write_text(
                json.dumps([{"l": "2", "id_chamado": "123"}]), encoding="utf-8")
            (origem / "registros_modelos_auditoria.json").write_text(json.dumps({
                "modelos": {"linear_svc": {"ids_unicos": 1, "ids_invalidos": 0}}
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "campo nao permitido"):
                empacotar(config, origem, base / "destino")

    def test_aceita_modelo_ausente_quando_auditoria_confirma_zero(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            origem = base / "origem"
            origem.mkdir()
            config = base / "config.json"
            config.write_text(json.dumps({"multimodelo": {
                "modelos_leves": [], "modelos_pesados": ["transformer_ft"]
            }}), encoding="utf-8")
            (origem / "registros_modelos_auditoria.json").write_text(json.dumps({
                "modelos": {"transformer_ft": {
                    "ids_unicos": 0, "ids_invalidos": 0, "status": "ausente"
                }}
            }), encoding="utf-8")
            manifesto = empacotar(config, origem, base / "destino")
            self.assertEqual(manifesto["arquivos"], [])
            self.assertEqual(manifesto["ausentes"], ["registros_transformer_ft.json"])


if __name__ == "__main__":
    unittest.main()
