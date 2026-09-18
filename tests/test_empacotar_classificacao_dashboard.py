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

            manifesto = empacotar(config, origem, destino)

            self.assertEqual(len(manifesto["arquivos"]), 1)
            self.assertEqual(manifesto["ausentes"], ["registros_lstm.json"])
            self.assertFalse(manifesto["contem_id_chamado"])
            self.assertFalse(manifesto["contem_texto_chamado"])
            self.assertEqual(manifesto["arquivos"][0]["registros"], 1)
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


if __name__ == "__main__":
    unittest.main()
