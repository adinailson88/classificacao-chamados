import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from persistir_classificacao_dashboard import nomes_permitidos, persistir  # noqa: E402


class AllowlistPersistenciaTest(unittest.TestCase):
    def test_allowlist_derivada_dos_modelos(self):
        config = {"multimodelo": {
            "modelos_leves": ["linear_svc"],
            "modelos_pesados": ["lstm"],
        }}
        self.assertEqual(nomes_permitidos(config), [
            "registros_modelos_auditoria.json",
            "registros_linear_svc.json",
            "registros_lstm.json",
        ])

    def test_recusa_nome_invalido(self):
        config = {"multimodelo": {"modelos_leves": ["../../segredo"], "modelos_pesados": []}}
        with self.assertRaisesRegex(ValueError, "invalida"):
            nomes_permitidos(config)

    def test_publica_em_repositorio_limpo_e_depois_faz_noop(self):
        config = {"multimodelo": {
            "modelos_leves": ["linear_svc"],
            "modelos_pesados": ["transformer_ft"],
        }}
        registro = {"l": "2", "g": "Elétrica", "m": "Corretiva", "o": "Elétrica",
                    "p": "Elétrica", "c": 0.9, "f": "entre_70_95",
                    "e": "linear_svc", "k": 1, "v": ""}
        auditoria = {"modelos": {
            "linear_svc": {"status": "valido_completo", "ids_unicos": 1,
                           "ids_invalidos": 0},
            "transformer_ft": {"status": "ausente", "ids_unicos": 0,
                               "ids_invalidos": 0},
        }}
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            remoto = base / "remoto.git"
            trabalho = base / "trabalho"
            origem = base / "origem"
            origem.mkdir()
            (origem / "registros_linear_svc.json").write_text(
                json.dumps([registro]), encoding="utf-8")
            (origem / "registros_modelos_auditoria.json").write_text(
                json.dumps(auditoria), encoding="utf-8")
            subprocess.run(["git", "init", "--bare", "--initial-branch=main", str(remoto)],
                           check=True, capture_output=True)
            subprocess.run(["git", "clone", str(remoto), str(trabalho)],
                           check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "teste"], cwd=trabalho, check=True)
            subprocess.run(["git", "config", "user.email", "teste@example.invalid"],
                           cwd=trabalho, check=True)
            (trabalho / "README.md").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=trabalho, check=True)
            subprocess.run(["git", "commit", "-m", "base"], cwd=trabalho,
                           check=True, capture_output=True)
            subprocess.run(["git", "push", "origin", "main"], cwd=trabalho,
                           check=True, capture_output=True)

            primeiro = persistir(config, origem, "origin", "main", trabalho, 2)
            segundo = persistir(config, origem, "origin", "main", trabalho, 2)
            self.assertRegex(primeiro, r"^[0-9a-f]{40}$")
            self.assertEqual(segundo, "no-op")


if __name__ == "__main__":
    unittest.main()
