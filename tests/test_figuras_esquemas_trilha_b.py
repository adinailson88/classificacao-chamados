from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

try:
    import matplotlib  # noqa: F401
    TEM_MATPLOTLIB = True
except ImportError:  # pragma: no cover
    TEM_MATPLOTLIB = False


@unittest.skipUnless(TEM_MATPLOTLIB, "matplotlib ausente")
class EsquemasTest(unittest.TestCase):
    def test_gera_png_e_svg_das_quatro_figuras(self):
        import figuras_esquemas_trilha_b as f
        with tempfile.TemporaryDirectory() as d:
            for fn in (f.estrutura_modelo, f.tokens_exemplo, f.calculo_categoria,
                       f.ciclo_aprendizado):
                fn(Path(d))
            nomes = sorted(p.name for p in Path(d).iterdir())
        self.assertEqual(len(nomes), 8)
        self.assertTrue(all(n.endswith((".png", ".svg")) for n in nomes))


if __name__ == "__main__":
    unittest.main()
