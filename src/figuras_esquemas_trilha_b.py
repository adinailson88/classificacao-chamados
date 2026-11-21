#!/usr/bin/env python3
"""Figuras esquematicas da Trilha B (estrutura do modelo, tokens, calculo, ciclo).

Gera PNG (300 dpi) e SVG editavel de quatro esquemas, com cores fixas e a mesma
tipografia das demais figuras. Os numeros das Figuras 7 e 8 sao ilustrativos e
dizem isso na propria figura; nenhum dado de chamado entra nestes esquemas.

Uso: python src/figuras_esquemas_trilha_b.py docs/trilha_b/figuras
"""

from __future__ import annotations

import sys
from pathlib import Path

CORES = {  # (preenchimento, borda, titulo, subtitulo)
    "cinza": ("#F1EFE8", "#5F5E5A", "#2C2C2A", "#5F5E5A"),
    "verde": ("#E1F5EE", "#0F6E56", "#085041", "#0F6E56"),
    "roxo": ("#EEEDFE", "#534AB7", "#3C3489", "#534AB7"),
}
TRACO = "#5F5E5A"


def _preparar(altura: float):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "serif", "svg.fonttype": "none"})
    fig = plt.figure(figsize=(6.8, altura / 100))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 680)
    ax.set_ylim(altura, 0)
    ax.axis("off")
    return fig, ax


def caixa(ax, x, y, w, h, titulo, sub=None, cor="cinza", borda=0.8, fs=10):
    from matplotlib.patches import FancyBboxPatch
    fc, ec, ct, cs = CORES[cor]
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=7",
                                fc=fc, ec=ec, lw=borda))
    if sub:
        ax.text(x + w / 2, y + h * 0.36, titulo, ha="center", va="center", fontsize=fs,
                fontweight="bold", color=ct)
        ax.text(x + w / 2, y + h * 0.70, sub, ha="center", va="center", fontsize=8.6, color=cs)
    else:
        ax.text(x + w / 2, y + h / 2, titulo, ha="center", va="center", fontsize=10,
                fontweight="bold", color=ct)


def chip(ax, x, y, w, texto, cor="cinza", h=24, alpha=1.0, fs=8.4):
    from matplotlib.colors import to_rgba
    from matplotlib.patches import FancyBboxPatch
    fc, ec, ct, _ = CORES[cor]
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=4",
                                fc=to_rgba(fc, alpha), ec=ec, lw=0.6))
    ax.text(x + w / 2, y + h / 2, texto, ha="center", va="center", fontsize=fs, color=ct)


def seta(ax, x1, y1, x2, y2, cor=TRACO):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", lw=0.9, color=cor, shrinkA=0, shrinkB=0,
                                mutation_scale=9))


def texto(ax, x, y, s, ha="left", fs=8.6, bold=False, cor="#2C2C2A", style="normal"):
    ax.text(x, y, s, ha=ha, va="center", fontsize=fs, color=cor,
            fontweight="bold" if bold else "normal", fontstyle=style)


def salvar(fig, saida: Path, nome: str) -> None:
    saida.mkdir(parents=True, exist_ok=True)
    fig.savefig(saida / f"{nome}.png", dpi=300)
    fig.savefig(saida / f"{nome}.svg")
    import matplotlib.pyplot as plt
    plt.close(fig)


def estrutura_modelo(saida: Path) -> None:
    fig, ax = _preparar(545)
    caixa(ax, 170, 30, 340, 56, "Texto do chamado", "título e descrição do GLPI e da O.S.M.")
    caixa(ax, 40, 150, 190, 56, "TF-IDF de palavras", "1 e 2 palavras seguidas", "verde")
    caixa(ax, 250, 150, 190, 56, "TF-IDF de caracteres", "pedaços de 2 a 5 letras", "verde")
    caixa(ax, 460, 150, 190, 56, "Embedding e5", "vetor denso de 768 números", "roxo")
    caixa(ax, 170, 270, 340, 56, "Concatenação", "um vetor longo por chamado")
    caixa(ax, 170, 370, 340, 56, "LinearSVC e softmax", "uma nota por categoria (39)", "roxo")
    caixa(ax, 170, 460, 340, 44, "Categoria prevista e confiança")
    for a in ((270, 86, 150, 148), (340, 86, 345, 148), (410, 86, 540, 148),
              (135, 206, 250, 268), (345, 206, 340, 268), (555, 206, 430, 268),
              (340, 326, 340, 368), (340, 426, 340, 458)):
        seta(ax, *a)
    chip(ax, 60, 522, 10, "", "verde", h=10)
    texto(ax, 78, 527, "contagem de termos do texto")
    chip(ax, 290, 522, 10, "", "roxo", h=10)
    texto(ax, 308, 527, "rede pré-treinada ou classificador aprendido")
    salvar(fig, saida, "figura_6_estrutura_modelo")


def tokens_exemplo(saida: Path) -> None:
    fig, ax = _preparar(430)
    texto(ax, 340, 22, "\"ar condicionado da sala 12 pingando\"", "center", 10, True)
    texto(ax, 135, 52, "Palavras", "center", 10, True)
    texto(ax, 50, 76, "palavras sozinhas")
    for x, y, w, t in ((50, 86, 30, "ar"), (86, 86, 92, "condicionado"), (184, 86, 40, "sala"),
                       (50, 116, 28, "12"), (84, 116, 66, "pingando")):
        chip(ax, x, y, w, t, "verde")
    texto(ax, 50, 166, "pares vizinhos")
    for x, y, w, t in ((50, 176, 112, "ar condicionado"), (50, 206, 124, "condicionado sala"),
                       (50, 236, 59, "sala 12"), (115, 236, 86, "12 pingando")):
        chip(ax, x, y, w, t, "verde")

    texto(ax, 345, 52, "Caracteres", "center", 10, True)
    texto(ax, 262, 76, "trigramas de \"pingando\"")
    for i, t in enumerate(("pin", "ing", "nga", "gan", "and", "ndo")):
        chip(ax, 262 + (i % 3) * 40, 86 + (i // 3) * 30, 34, t, "cinza")
    texto(ax, 262, 166, "com erro: \"pingano\"")
    for i, t in enumerate(("pin", "ing", "nga", "gan", "ano")):
        chip(ax, 262 + i * 40, 176, 34, t, "verde" if i < 4 else "cinza")
    texto(ax, 262, 222, "4 de 5 pedaços iguais aos corretos")
    texto(ax, 262, 242, "(há também pedaços de 2, 4 e 5)")

    texto(ax, 555, 52, "Embedding e5", "center", 10, True)
    texto(ax, 474, 76, "tokens (exemplo ilustrativo)")
    for x, y, w, t in ((474, 86, 27, "ar"), (507, 86, 73, "condicion"), (586, 86, 33, "ado"),
                       (474, 116, 27, "da"), (507, 116, 40, "sala"), (553, 116, 28, "12"),
                       (587, 116, 40, "ping"), (474, 146, 40, "ando")):
        chip(ax, x, y, w, t, "roxo")
    seta(ax, 555, 176, 555, 198)
    caixa(ax, 474, 200, 176, 44, "Transformer", "cada token vê os outros", "roxo")
    seta(ax, 555, 244, 555, 264)
    for i, a in enumerate((0.9, 0.3, 0.6, 0.2, 0.8, 0.4, 1.0, 0.25, 0.7, 0.35, 0.85, 0.5)):
        chip(ax, 474 + i * 13, 268, 10, "", "roxo", h=16, alpha=a)
    texto(ax, 474, 304, "média dos tokens: 768 números")

    seta(ax, 135, 272, 135, 330)
    seta(ax, 345, 252, 345, 330)
    seta(ax, 555, 318, 555, 330)
    caixa(ax, 40, 332, 610, 40, "um único vetor por chamado: palavras, caracteres e embedding lado a lado")
    texto(ax, 340, 400, "Esquema ilustrativo: a quebra em tokens e os valores do vetor são exemplos, "
          "não saídas reais do modelo.", "center", 7.8, style="italic")
    salvar(fig, saida, "figura_7_tokens_exemplo")


def calculo_categoria(saida: Path) -> None:
    fig, ax = _preparar(410)
    texto(ax, 390, 30, "pesos aprendidos (w) em cada categoria", "center")
    texto(ax, 40, 56, "valor do termo")
    texto(ax, 40, 72, "no chamado (x)")
    colunas = ((230, "Aplicação", "cupinicida"), (340, "Estrutura >", "Forro"),
               (450, "Climatização", "(exemplo)"))
    for x, l1, l2 in colunas:
        caixa(ax, x, 46, 100, 44, l1, l2, fs=9)
    termos = (("cupim", 0.5, 60, 118), ("forro", 0.3, 36, 152), ("sala", 0.2, 24, 186))
    for nome, v, larg, yc in termos:
        texto(ax, 40, yc, nome)
        chip(ax, 96, yc - 7, larg, "", "verde", h=14)
        texto(ax, 96 + larg + 6, yc, f"{v:.1f}".replace(".", ","))
        texto(ax, 214, yc, "×", "center")
    pesos = (((2.0, "verde", 1.0), (-0.4, "coral", 0.45), (-0.5, "coral", 0.55)),
             ((0.3, "verde", 0.4), (1.8, "verde", 0.9), (-0.2, "coral", 0.35)),
             ((0.0, "cinza", 0.5), (0.1, "verde", 0.3), (0.3, "verde", 0.4)))
    base = {"verde": "#1D9E75", "coral": "#D85A30", "cinza": "#888780"}
    from matplotlib.colors import to_rgba
    from matplotlib.patches import FancyBboxPatch

    def celula(x, y, v, cor, a):
        ax.add_patch(FancyBboxPatch((x, y), 100, 28, boxstyle="round,pad=0,rounding_size=4",
                                    fc=to_rgba(base[cor], a), ec=base[cor], lw=0.5))
        rot = "0,0" if v == 0 else f"{v:+.1f}".replace(".", ",").replace("-", "−")
        texto(ax, x + 50, y + 14, rot, "center")

    for i, linha in enumerate(pesos):
        for (x, _, _), (v, cor, a) in zip(colunas, linha):
            celula(x, 104 + i * 34, v, cor, a)
    texto(ax, 40, 220, "ajuste da categoria (b)")
    for (x, _, _), (v, a) in zip(colunas, ((-0.6, 0.35), (-0.5, 0.3), (-0.7, 0.4))):
        celula(x, 206, v, "coral", a)
    texto(ax, 40, 261, "nota (soma)", bold=True)
    for k, ((x, _, _), nota) in enumerate(zip(colunas, ("0,49", "−0,14", "−0,95"))):
        caixa(ax, x, 244, 100, 34, nota, None, "roxo", borda=2.0 if k == 0 else 0.8)
        seta(ax, x + 50, 280, x + 50, 294)
    texto(ax, 40, 306, "probabilidade", bold=True)
    texto(ax, 40, 322, "(softmax das notas)")
    for x, larg, p, cor in ((236, 51, "0,565", "roxo"), (346, 27, "0,301", "cinza"),
                            (456, 12, "0,134", "cinza")):
        chip(ax, x, 304, larg, "", cor, h=18)
        texto(ax, x + larg + 6, 313, p)
    texto(ax, 390, 360, "a maior vence: Aplicação cupinicida, com confiança 0,565", "center", 10, True)
    texto(ax, 340, 392, "Esquema ilustrativo com 3 categorias; os valores foram escolhidos para a conta fechar "
          "e não vêm do modelo treinado.", "center", 7.8, style="italic")
    salvar(fig, saida, "figura_8_calculo_categoria")


def ciclo_aprendizado(saida: Path) -> None:
    fig, ax = _preparar(500)
    caixa(ax, 60, 30, 200, 56, "Chamados novos", "do trimestre")
    caixa(ax, 60, 120, 200, 56, "Modelo atual", "prediz e dá a confiança", "roxo")
    caixa(ax, 60, 210, 200, 56, "Limiar de risco", "meta de 10% de erro", "roxo")
    caixa(ax, 60, 300, 200, 56, "Automatiza", "confiança acima do limiar")
    caixa(ax, 380, 210, 240, 56, "Revisão humana", "confiança abaixo do limiar", "verde")
    caixa(ax, 380, 300, 240, 56, "Memória validada", "auditoria e revisões", "verde")
    caixa(ax, 380, 390, 240, 56, "Retreino trimestral", "gera o novo modelo", "roxo")
    for a in ((160, 86, 160, 118), (160, 176, 160, 208), (160, 266, 160, 298),
              (260, 238, 378, 238), (500, 266, 500, 298), (500, 356, 500, 388)):
        seta(ax, *a)
    ax.plot([620, 650, 650], [418, 418, 148], color=TRACO, lw=0.9, solid_capstyle="butt")
    seta(ax, 650, 148, 262, 148)
    texto(ax, 456, 136, "o novo modelo substitui o anterior", "center")
    chip(ax, 60, 468, 10, "", "roxo", h=10)
    texto(ax, 78, 473, "etapa automática")
    chip(ax, 210, 468, 10, "", "verde", h=10)
    texto(ax, 228, 473, "etapa com decisão humana")
    salvar(fig, saida, "figura_9_ciclo_aprendizado")


def main() -> int:
    saida = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/trilha_b/figuras")
    for f in (estrutura_modelo, tokens_exemplo, calculo_categoria, ciclo_aprendizado):
        f(saida)
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
