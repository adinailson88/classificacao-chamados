import sys
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from exportar_dashboard import deduplicar_registros_modelo, normalizar_id  # noqa: E402


CAB = ["run_id", "linha_planilha", "id_chamado", "categoria_original",
       "categoria_ia", "confianca", "faixa", "executor", "acerto", "etapa", "data"]


def linha(id_chamado, posicao, prevista, data="01/01/2026 10:00"):
    return ["run", posicao, id_chamado, "Elétrica", prevista, 0.8, "", "linear_svc",
            False, 1, data]


class ExportarDashboardDedupModelosTest(unittest.TestCase):
    def test_normaliza_representacoes_numericas_do_mesmo_id(self):
        self.assertEqual(normalizar_id(1693), "1693")
        self.assertEqual(normalizar_id(1693.0), "1693")
        self.assertEqual(normalizar_id("1693"), "1693")

    def test_mantem_ultima_previsao_por_id_e_linha_atual(self):
        vals = [CAB,
                linha(1693.0, 9, "Hidrossanitária"),
                linha("1693", 99, "Elétrica", "02/01/2026 10:00"),
                linha("2000", 10, "Elétrica")]
        registros, aud = deduplicar_registros_modelo(
            vals, {"1693", "2000"}, {"1693": 2, "2000": 3}, {"2": "Correto"}, "linear_svc")

        self.assertEqual(len(registros), 2)
        self.assertEqual(registros[0]["l"], "2")
        self.assertEqual(registros[0]["p"], "Elétrica")
        self.assertNotIn("id_chamado", registros[0])
        self.assertEqual(aud["registros_brutos"], 3)
        self.assertEqual(aud["duplicados_descartados"], 1)
        self.assertEqual(aud["ids_unicos"], 2)
        self.assertEqual(aud["status"], "valido_completo")

    def test_descarta_id_fora_da_base_e_marca_parcial(self):
        vals = [CAB, linha("1", 2, "Elétrica"), linha("999", 3, "Elétrica")]
        registros, aud = deduplicar_registros_modelo(
            vals, {"1", "2"}, {"1": 2, "2": 3}, {}, "linear_svc")
        self.assertEqual(len(registros), 1)
        self.assertEqual(aud["ids_fora_base_descartados"], 1)
        self.assertEqual(aud["status"], "parcial")

    def test_bloqueia_previsao_sem_id(self):
        vals = [CAB, linha("", 2, "Elétrica")]
        with self.assertRaisesRegex(ValueError, "ID vazio/invalido"):
            deduplicar_registros_modelo(vals, {"1"}, {"1": 2}, {}, "linear_svc")

    def test_bloqueia_quando_ids_atuais_nao_foram_lidos(self):
        with self.assertRaisesRegex(RuntimeError, "IDs atuais indisponiveis"):
            deduplicar_registros_modelo([CAB], set(), {}, {}, "linear_svc")


if __name__ == "__main__":
    unittest.main()
