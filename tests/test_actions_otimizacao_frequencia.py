#!/usr/bin/env python3
"""Teste estatico do lote A3-1 (deduplicacao de gatilhos workflow_run de alta
frequencia em dashboard.yml e estatistica.yml): confirma, so por leitura dos
YAML, que os schedules e o workflow_dispatch permanecem intactos, que a lista
de workflow_run ficou exatamente com os upstreams esperados, e que
concurrency/cancel-in-progress nao mudaram.

Nenhum workflow e executado, nenhuma rede e usada -- so leitura de YAML.
"""
from __future__ import annotations

import unittest
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
WORKFLOWS = RAIZ / ".github" / "workflows"


def carregar_yaml(caminho: Path) -> dict:
    with caminho.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def bloco_on(doc: dict) -> dict:
    # YAML 1.1: a chave "on" e interpretada como booleano True pelo PyYAML.
    if "on" in doc:
        return doc["on"]
    return doc[True]


class TestDashboardGatilhos(unittest.TestCase):
    def setUp(self):
        self.doc = carregar_yaml(WORKFLOWS / "dashboard.yml")
        self.on = bloco_on(self.doc)

    def test_schedule_inalterado(self):
        schedule = self.on["schedule"]
        self.assertEqual(len(schedule), 1)
        self.assertEqual(schedule[0]["cron"], "*/30 * * * *")

    def test_workflow_dispatch_presente(self):
        self.assertIn("workflow_dispatch", self.on)

    def test_workflow_run_upstreams_exatos(self):
        upstreams = self.on["workflow_run"]["workflows"]
        self.assertEqual(
            upstreams,
            [
                "Comparar modelos (lote)",
                "Multimodelo - reclassificacao",
                "Transformer fine-tuning (BERTimbau)",
            ],
        )

    def test_upstreams_removidos_nao_aparecem(self):
        upstreams = self.on["workflow_run"]["workflows"]
        self.assertNotIn("Etapa 1 - classificacao progressiva", upstreams)
        self.assertNotIn("Multimodelo - classificacao completa", upstreams)

    def test_concurrency_inalterada(self):
        self.assertEqual(self.doc["concurrency"]["group"], "escrita-planilha")
        self.assertEqual(self.doc["concurrency"]["cancel-in-progress"], False)


class TestEstatisticaGatilhos(unittest.TestCase):
    def setUp(self):
        self.doc = carregar_yaml(WORKFLOWS / "estatistica.yml")
        self.on = bloco_on(self.doc)

    def test_schedule_inalterado(self):
        schedule = self.on["schedule"]
        self.assertEqual(len(schedule), 1)
        self.assertEqual(schedule[0]["cron"], "30 */6 * * *")

    def test_workflow_dispatch_presente(self):
        self.assertIn("workflow_dispatch", self.on)

    def test_workflow_run_upstreams_exatos(self):
        upstreams = self.on["workflow_run"]["workflows"]
        self.assertEqual(
            upstreams,
            [
                "Comparar modelos (lote)",
            ],
        )

    def test_upstream_removido_nao_aparece(self):
        upstreams = self.on["workflow_run"]["workflows"]
        self.assertNotIn("Multimodelo - classificacao completa", upstreams)
        # Removido para eliminar a corrida com o cron de 6h: os dois disparos
        # legitimos calculavam docs/dados/estatistica.json quase ao mesmo
        # tempo a partir de estados diferentes, gerando conflito de push que
        # o commit estatistica.yml nao pode resolver automaticamente.
        self.assertNotIn("Transformer fine-tuning (BERTimbau)", upstreams)

    def test_concurrency_inalterada(self):
        self.assertEqual(self.doc["concurrency"]["group"], "escrita-planilha")
        self.assertEqual(self.doc["concurrency"]["cancel-in-progress"], False)


if __name__ == "__main__":
    unittest.main()
