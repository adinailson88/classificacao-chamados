from __future__ import annotations

import unittest
from pathlib import Path

import yaml


CAMINHO = (Path(__file__).resolve().parents[1] / ".github" / "workflows" /
           "sincronizar_correcoes_glpi.yml")


def secao_on(doc: dict) -> dict:
    return doc.get("on") or doc.get(True) or {}


class WorkflowSincronizarGlpiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texto = CAMINHO.read_text(encoding="utf-8")
        cls.doc = yaml.safe_load(cls.texto)
        cls.on = secao_on(cls.doc)

    def test_somente_disparo_manual(self):
        self.assertEqual(set(self.on), {"workflow_dispatch"})

    def test_dry_run_e_padrao(self):
        modo = self.on["workflow_dispatch"]["inputs"]["modo"]
        self.assertEqual(modo["default"], "dry-run")
        self.assertEqual(modo["options"], ["dry-run", "aplicar"])

    def test_permissoes_globais_somente_leitura(self):
        self.assertEqual(self.doc["permissions"], {"contents": "read"})

    def test_aplicacao_usa_ambiente_protegido(self):
        self.assertEqual(self.doc["jobs"]["aplicar"]["environment"], "glpi-producao")

    def test_aplicacao_exige_dois_gates_literais(self):
        run = self.doc["jobs"]["aplicar"]["steps"][0]["run"]
        self.assertIn('test "$CONFIRMACAO" = "APLICAR_GLPI"', run)
        self.assertIn('test "$HABILITAR_ESCRITA_GLPI" = "SIM"', run)

    def test_sem_cron_e_sem_push(self):
        self.assertNotIn("schedule", self.on)
        self.assertNotIn("git push", self.texto)

    def test_parametros_de_usuario_entram_por_env(self):
        blocos = "\n".join(
            str(step.get("run", ""))
            for job in self.doc["jobs"].values()
            for step in job.get("steps", [])
        )
        self.assertNotIn("${{ inputs.", blocos)
        self.assertIn('--ids "$INPUT_IDS"', blocos)
        self.assertIn('--limite "$INPUT_LIMITE"', blocos)


if __name__ == "__main__":
    unittest.main()
