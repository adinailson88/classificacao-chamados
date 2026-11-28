import json, sys, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

B = "docs/dados/trilha_b/"
OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "serif", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})

# ---- Figura 2: custo x acuracia (Tabela 2)
modelos = [("tfidf_embedding", 217.97, 0.8307), ("LinearSVC com caracteres", 150.72, 0.8280), ("LinearSVC", 26.85, 0.8241),
           ("SGD", 27.14, 0.8096), ("Regressão Logística", 62.83, 0.8079), ("Extra Trees", 95.17, 0.8054),
           ("Random Forest", 81.57, 0.7923), ("Embeddings e5", 31.14, 0.7554), ("Naive Bayes", 20.82, 0.7222), ("LSTM", 766.55, 0.7067)]
fig, ax = plt.subplots(figsize=(6.2, 3.8))
for nome, t, a in modelos:
    principal = nome == "tfidf_embedding"
    ax.scatter(t, a, s=46 if principal else 28, color="#1f4e79" if principal else "#7f7f7f", zorder=3)
    dx, dy, ha = 1.08, 0.0012, "left"
    if nome in ("SGD",): dy = -0.0042
    if nome in ("Regressão Logística",): dy = 0.0016
    if nome in ("LinearSVC",): dx, ha, dy = 0.93, "right", 0.0012
    if nome in ("Naive Bayes",): dx, ha, dy = 0.93, "right", 0.0
    if nome in ("Embeddings e5",): dx, ha, dy = 0.93, "right", 0.0
    if nome == "Extra Trees": dy = -0.0042
    if nome == "tfidf_embedding": dx, ha, dy = 1.0, "center", 0.0032
    if nome == "LinearSVC com caracteres": dx, ha, dy = 0.93, "right", -0.0035
    ax.annotate(nome, (t * dx, a + dy), ha=ha, fontsize=7.5)
ax.set_xscale("log")
ax.set_xlabel("Tempo de treino sobre a base completa (s, escala logarítmica)")
ax.set_ylabel("Acurácia contra a referência revisada")
ax.set_xlim(12, 1300)
from matplotlib.ticker import FuncFormatter
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.2f}".replace(".", ",")))
ax.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(OUT + "/figura_2_custo_acuracia.png", dpi=300)
plt.close(fig)

# ---- Figura 3: confiabilidade do tfidf_embedding
m = json.load(open(B + "calibracao_candidatos.json", encoding="utf-8"))["modelos"]
t = [a for a in m if a["modelo"] == "tfidf_embedding"][0]
fig, axs = plt.subplots(1, 2, figsize=(6.6, 3.3), sharey=True)
for ax, chave, titulo in ((axs[0], "bruta", "Escore bruto"), (axs[1], "calibrada", "Após calibração isotônica")):
    pts = [(f["confianca_media"], f["acuracia"], f["n"]) for f in t[chave]["confiabilidade"] if f["n"] and f["confianca_media"] is not None]
    ax.plot([0, 1], [0, 1], color="#999999", lw=0.8, ls="--")
    ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=[max(8, p[2] / 25) for p in pts], color="#1f4e79", alpha=0.85, zorder=3)
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color="#1f4e79", lw=0.8)
    ax.set_title(f"{titulo} (ECE = {t[chave]['ece']:.4f})".replace(".", ","), fontsize=8.5)
    ax.set_xlabel("Confiança média da faixa")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.grid(alpha=0.25)
axs[0].set_ylabel("Acurácia observada na faixa")
fig.tight_layout()
fig.savefig(OUT + "/figura_3_confiabilidade.png", dpi=300)
plt.close(fig)

# ---- Figura 4: controle de risco (alvo 10%)
c = json.load(open(B + "controle_risco.json", encoding="utf-8"))["cenarios"]
rot = {"iid_grupos": "Aleatório\npor grupo", "prospectivo": "Prospectivo"}
nomes, ctrl, ing, cob = [], [], [], []
for s in c:
    a = s["alvos"]["0.1"]
    n = s["cenario"]
    nomes.append(n)
    ctrl.append(a["controlado"]["erro"] * 100 if a["controlado"]["erro"] is not None else float("nan"))
    ing.append(a["ingenuo"]["erro"] * 100)
    cob.append(a["controlado"]["cobertura"] * 100)
print(nomes)
import numpy as np
x = np.arange(len(nomes))
fig, ax = plt.subplots(figsize=(6.8, 3.6))
ax.bar(x - 0.2, ing, 0.38, color="#c0504d", label="Limiar ingênuo")
ax.bar(x + 0.2, ctrl, 0.38, color="#1f4e79", label="Limiar com garantia (Learn-then-Test)")
ax.axhline(10, color="black", lw=0.9, ls="--")
ax.text(len(nomes) - 0.5, 10.25, "alvo de 10%", ha="right", fontsize=7.5)
ax.set_xticks(x)
curto = {"iid_grupos": "Aleatório", "prospectivo": "Prospectivo", "origem_rolante_2022": "Origem 2022", "origem_rolante_2023": "Origem 2023",
         "origem_rolante_2024": "Origem 2024", "origem_rolante_2025": "Origem 2025", "origem_rolante_2026": "Origem 2026",
         "origem_para_Campus Jorge Amado": "Reit.→JA", "origem_para_Campus Paulo Freire": "Reit.→PF", "origem_para_Campus Sosígenes Costa": "Reit.→SC",
         "deixa_um_campus_fora_Reitoria": "Sem Reit.", "deixa_um_campus_fora_Campus Jorge Amado": "Sem JA",
         "deixa_um_campus_fora_Campus Paulo Freire": "Sem PF", "deixa_um_campus_fora_Campus Sosígenes Costa": "Sem SC"}
ax.set_xticklabels([curto[n] for n in nomes], rotation=45, ha="right", fontsize=7.5)
ax.set_ylim(0, 13.5)
ax.set_ylabel("Erro entre os automatizados (%)")
ax.legend(fontsize=7.5, frameon=False, loc="upper center", ncol=2)
ax.grid(axis="y", alpha=0.25)
fig.tight_layout()
fig.savefig(OUT + "/figura_4_controle_risco.png", dpi=300)
plt.close(fig)
print("ok")
