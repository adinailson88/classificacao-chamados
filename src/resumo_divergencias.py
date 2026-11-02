"""Resumo semanal de chamados com categoria historica provavelmente inadequada.

Le as predicoes fora da dobra do modelo principal (docs/dados/trilha_b/predicoes_com_alternativas.csv),
junta com o snapshot privado do corte (id, titulo, categoria historica), ordena as divergencias por
confianca e grava um corpo de e-mail em HTML, um PDF e um rascunho .eml SEM envio.

O snapshot contem texto de chamados e nunca deve ser versionado. A saida tambem fica fora do repositorio.

Uso:
    python src/resumo_divergencias.py --snapshot snapshot_B.json --saida pasta_de_saida [--topo 30]
"""
import argparse
import csv
import html
import json
import os
from collections import defaultdict
from email.message import EmailMessage
from hashlib import sha256

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

MODELO = "tfidf_embedding"


def carregar(snapshot, predicoes):
    valores = json.load(open(snapshot, encoding="utf-8"))["values"]
    cab = valores[0]
    idx = {c: i for i, c in enumerate(cab)}
    chamados = {}
    for lin in valores[1:]:
        if not lin or not lin[0]:
            continue
        lin = lin + [""] * (len(cab) - len(lin))
        chamados[sha256(str(lin[0]).encode()).hexdigest()] = {c: lin[i] for c, i in idx.items()}
    linhas = []
    with open(predicoes, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["modelo"] != MODELO:
                continue
            c = chamados.get(r["id_sha256"])
            if not c:
                continue
            linhas.append({
                "id": c["id_chamado"], "titulo": " ".join(str(c["titulo"]).split()),
                "historica": c["categoria_historica"], "referencia": c["referencia_humana"],
                "sugerida": r["previsto"], "confianca": float(r["confianca"]),
                "periodo": c.get("periodo", ""),
            })
    return linhas


def faixas(div):
    """Proporcao de registros inadequados (pela auditoria) por posicao na lista ordenada por confianca."""
    cortes = [(0, 100, "100 primeiras"), (100, 500, "101 a 500"), (500, 1000, "501 a 1.000"), (1000, len(div), "demais")]
    saida = []
    for lo, hi, nome in cortes:
        g = div[lo:hi]
        inadequadas = sum(1 for x in g if x["referencia"] and x["referencia"] != x["historica"])
        saida.append((nome, len(g), inadequadas, (inadequadas / len(g) if g else 0.0)))
    return saida


def pct(x):
    return f"{100 * x:.1f}".replace(".", ",") + "%"


def corpo_html(topo, fx, total, n_div):
    linhas = "".join(
        f"<tr><td>{html.escape(str(x['id']))}</td><td>{html.escape(x['titulo'][:70])}</td>"
        f"<td>{html.escape(x['historica'])}</td><td>{html.escape(x['sugerida'])}</td>"
        f"<td style='text-align:right'>{str(round(x['confianca'], 2)).replace('.', ',')}</td></tr>"
        for x in topo)
    faixas_html = "".join(
        f"<tr><td>{n}</td><td style='text-align:right'>{t}</td><td style='text-align:right'>{i}</td>"
        f"<td style='text-align:right'>{pct(p)}</td></tr>" for n, t, i, p in fx)
    return f"""<html><body style="font-family:Arial,sans-serif;font-size:14px;color:#222">
<p>Prezados,</p>
<p>Segue a lista de chamados cuja categoria registrada pode estar inadequada, ordenada pela confiança do modelo.
Dos {total:,} chamados avaliados, {n_div:,} divergem da categoria registrada, e a lista abaixo traz os {len(topo)} de maior confiança.
A sugestão do modelo serve apenas para priorizar a conferência, e a decisão de alterar a categoria é do servidor.</p>
<table border="1" cellspacing="0" cellpadding="4" style="border-collapse:collapse;font-size:13px">
<tr style="background:#eee"><th>ID</th><th>Título</th><th>Categoria registrada</th><th>Categoria sugerida</th><th>Confiança</th></tr>
{linhas}</table>
<p>Referência de desempenho no corte congelado, por posição na lista (ordenada pela confiança), entre as divergências do modelo com o histórico:</p>
<table border="1" cellspacing="0" cellpadding="4" style="border-collapse:collapse;font-size:13px">
<tr style="background:#eee"><th>Posição na lista</th><th>Divergências</th><th>Registro inadequado pela auditoria</th><th>Proporção</th></tr>
{faixas_html}</table>
<p>Para corrigir, abrir o chamado no GLPI e ajustar a categoria. Chamados já conferidos podem ser ignorados.</p>
<p>Atenciosamente.</p></body></html>"""


def gerar_pdf(caminho, topo, fx, total, n_div):
    st = getSampleStyleSheet()
    doc = SimpleDocTemplate(caminho, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    el = [Paragraph("Chamados com categoria possivelmente inadequada", st["Title"]),
          Paragraph(f"{n_div} de {total} chamados avaliados divergem da categoria registrada. Lista dos {len(topo)} de maior confianca. "
                    "A sugestao serve para priorizar a conferencia; a decisao e do servidor.", st["Normal"]), Spacer(1, 0.4 * cm)]
    cel = st["BodyText"]
    cel.fontSize = 8
    cel.leading = 10
    dados = [["ID", "Titulo", "Categoria registrada", "Categoria sugerida", "Conf."]]
    for x in topo:
        dados.append([str(x["id"]), Paragraph(html.escape(x["titulo"][:80]), cel), Paragraph(html.escape(x["historica"]), cel),
                      Paragraph(html.escape(x["sugerida"]), cel), f"{x['confianca']:.2f}"])
    t = Table(dados, colWidths=[2.4 * cm, 5.2 * cm, 4.1 * cm, 4.1 * cm, 1.2 * cm], repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey), ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                           ("FONTSIZE", (0, 0), (-1, -1), 8), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    el += [t, Spacer(1, 0.5 * cm), Paragraph("Desempenho de referencia por posicao na lista (corte congelado)", st["Heading3"])]
    d2 = [["Posicao", "Divergencias", "Registro inadequado", "Proporcao"]] + [[n, str(tt), str(i), pct(p)] for n, tt, i, p in fx]
    t2 = Table(d2, repeatRows=1)
    t2.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey), ("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 8)]))
    el.append(t2)
    doc.build(el)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--predicoes", default="docs/dados/trilha_b/predicoes_com_alternativas.csv")
    ap.add_argument("--saida", required=True)
    ap.add_argument("--topo", type=int, default=30)
    ap.add_argument("--para", default="destinatarios@exemplo.invalid")
    a = ap.parse_args()
    os.makedirs(a.saida, exist_ok=True)
    linhas = carregar(a.snapshot, a.predicoes)
    div = sorted((x for x in linhas if x["sugerida"] != x["historica"]), key=lambda x: -x["confianca"])
    topo = div[: a.topo]
    fx = faixas(div)
    corpo = corpo_html(topo, fx, len(linhas), len(div))
    open(os.path.join(a.saida, "email_corpo.html"), "w", encoding="utf-8").write(corpo)
    pdf = os.path.join(a.saida, "divergencias.pdf")
    gerar_pdf(pdf, topo, fx, len(linhas), len(div))
    m = EmailMessage()
    m["Subject"] = "Chamados com categoria possivelmente inadequada para conferência"
    m["To"] = a.para
    m.set_content("Versão em HTML. Veja o anexo em PDF.")
    m.add_alternative(corpo, subtype="html")
    m.add_attachment(open(pdf, "rb").read(), maintype="application", subtype="pdf", filename="divergencias.pdf")
    open(os.path.join(a.saida, "rascunho.eml"), "wb").write(bytes(m))
    print(len(linhas), "chamados;", len(div), "divergencias;", "topo", len(topo))
    for n, t, i, p in fx:
        print(n, t, i, pct(p))


if __name__ == "__main__":
    main()
