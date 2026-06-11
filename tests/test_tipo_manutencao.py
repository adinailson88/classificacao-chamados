import sys
import types
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

sys.modules.setdefault("planilha", types.SimpleNamespace())
sys.modules.setdefault("tempo", types.SimpleNamespace(agora_bahia=lambda: "2026-06-11T00:00:00-03:00"))

from exportar_dashboard import tipo_manutencao  # noqa: E402


class TipoManutencaoTest(unittest.TestCase):
    def test_categoria_preventiva_com_separador(self):
        self.assertEqual(
            tipo_manutencao("Manutenção Preventiva > Gerador > Inspeção"),
            "Preventiva",
        )

    def test_categoria_preventiva_sem_espaco_antes_do_separador(self):
        self.assertEqual(
            tipo_manutencao("Manutencao Preventiva>Ar-condicionado"),
            "Preventiva",
        )

    def test_categoria_corretiva_quando_nao_tem_prefixo(self):
        self.assertEqual(
            tipo_manutencao("Elétrica > Iluminação > Lâmpada queimada"),
            "Corretiva",
        )

    def test_categoria_vazia_e_corretiva(self):
        self.assertEqual(tipo_manutencao(""), "Corretiva")


if __name__ == "__main__":
    unittest.main()
