import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon

plt.rcParams["font.family"] = ["Times New Roman", "DejaVu Serif"]

fig, ax = plt.subplots(figsize=(6.6, 4.8))
ax.set_xlim(0, 100)
ax.set_ylim(0, 72)
ax.axis("off")

COR = "#f2f2f2"
AZUL = "#e6eef7"
BORDA = "#333333"


def caixa(x, y, w, h, texto, fs=8.4, cor=COR):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2", fc=cor, ec=BORDA, lw=0.9))
    ax.text(x + w / 2, y + h / 2, texto, ha="center", va="center", fontsize=fs, linespacing=1.15)


def seta(x1, y1, x2, y2):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=BORDA, lw=0.9, shrinkA=0, shrinkB=0))


# linha 1: origem do rótulo
caixa(2, 54, 26, 14, "Registro do chamado\n(o solicitante escolhe\na categoria)")
caixa(37, 54, 26, 14, "Conferência e ajuste\npelo setor de manutenção\n(categoria histórica)")
caixa(72, 54, 26, 14, "Auditoria do rótulo\n(confirma ou rejeita:\nreferência revisada)")
seta(28.6, 61, 36.4, 61)
seta(63.6, 61, 71.4, 61)

# linha 2: segunda avaliação, classificadores e calibração
caixa(72, 35, 26, 12, "Segunda avaliação cega\nde 300 chamados\n(reprodutibilidade)")
seta(93, 53.6, 93, 47.4)
caixa(2, 35, 26, 12, "Classificadores\n(partições por grupo\nde texto idêntico)")
caixa(37, 35, 26, 12, "Confiança calibrada\ne limiar com garantia\nde erro-alvo")
ax.plot([77, 77, 15], [53.6, 50.5, 50.5], color=BORDA, lw=0.9, ls=(0, (4, 3)))
seta(15, 50.5, 15, 47.4)
ax.text(46, 51.0, "referência revisada (treino e avaliação)", ha="center", va="bottom", fontsize=7.4, style="italic")
seta(28.6, 41, 36.4, 41)

# decisão
ax.add_patch(Polygon([[50, 30], [62, 24], [50, 18], [38, 24]], closed=True, fc="white", ec=BORDA, lw=0.9))
ax.text(50, 24, "Confiança\n≥ limiar?", ha="center", va="center", fontsize=8.2)
seta(50, 34.6, 50, 30.4)

caixa(1, 2, 37, 13, "Decisão automática da categoria,\ncom auditoria periódica\npor amostragem", fs=8.2, cor=AZUL)
caixa(62, 2, 37, 13, "Fila de revisão humana (a\ndivergência com o histórico\nprioriza; o servidor decide)", fs=8.2, cor=AZUL)
seta(38, 24, 19, 15.4)
seta(62, 24, 81, 15.4)
ax.text(24, 21.5, "sim", fontsize=8, style="italic", ha="center")
ax.text(76, 21.5, "não", fontsize=8, style="italic", ha="center")

plt.savefig("figura_protocolo.png", dpi=300, bbox_inches="tight", facecolor="white")
print("ok")
