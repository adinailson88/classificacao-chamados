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


def corpo_html(topo, fx, total, n_div, base):
    destaque = fx[0]
    linhas = "".join(
        f"<tr style='background:{'#ffffff' if i % 2 == 0 else '#f6f8fa'}'>"
        f"<td style='padding:6px 8px;color:#555'>{html.escape(str(x['id']))}</td>"
        f"<td style='padding:6px 8px'>{html.escape(x['titulo'][:60])}</td>"
        f"<td style='padding:6px 8px;color:#777'>{html.escape(x['historica'].split(' > ')[-1])}</td>"
        f"<td style='padding:6px 8px;font-weight:bold;color:#0b5394'>{html.escape(x['sugerida'].split(' > ')[-1])}</td>"
        f"<td style='padding:6px 8px;text-align:right'>{str(round(x['confianca'], 2)).replace('.', ',')}</td></tr>"
        for i, x in enumerate(topo))
    barras = "".join(
        f"<tr><td style='padding:3px 8px'>{n}</td>"
        f"<td style='padding:3px 8px;width:220px'><div style='background:#0b5394;height:12px;width:{int(200 * p)}px'></div></td>"
        f"<td style='padding:3px 8px;font-weight:bold'>{pct(p)}</td></tr>" for n, t, i, p in fx)
    return f"""<html><body style="margin:0;background:#f0f2f5;font-family:Arial,sans-serif;font-size:14px;color:#222">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:16px">
<table width="640" cellpadding="0" cellspacing="0" style="background:#fff;border:1px solid #d9dde3">
<tr><td style="background:#0b5394;color:#fff;padding:14px 18px;font-size:17px;font-weight:bold">Chamados para conferir a categoria</td></tr>
<tr><td style="padding:16px 18px">
<div style="background:#fff4d6;border-left:5px solid #e69138;padding:12px 14px;font-size:15px">
<b>Comece pelos {fx[0][1]} primeiros da lista:</b> {pct(destaque[3])} deles tinham categoria inadequada,
contra {pct(base)} na base inteira.</div>
<p style="margin:14px 0 8px">Dos {total:,} chamados avaliados, {n_div:,} divergem da categoria registrada. Abaixo, os {len(topo)} de maior confiança.
A sugestão apenas prioriza a conferência, e a decisão é do servidor.</p>
<table width="100%" cellspacing="0" style="border-collapse:collapse;font-size:13px">
<tr style="background:#e8edf3;text-align:left"><th style="padding:6px 8px">ID</th><th style="padding:6px 8px">Título</th><th style="padding:6px 8px">Registrada</th><th style="padding:6px 8px">Sugerida</th><th style="padding:6px 8px;text-align:right">Conf.</th></tr>
{linhas}</table>
<p style="margin:16px 0 4px"><b>Quanto vale conferir mais adiante na lista</b> (registros inadequados confirmados pela auditoria)</p>
<table cellspacing="0" style="font-size:13px">{barras}</table>
<p style="margin:16px 0 0;color:#555">Para corrigir, abra o chamado no GLPI e ajuste a categoria.</p>
</td></tr></table></td></tr></table></body></html>"""


def gerar_pdf(caminho, topo, fx, total, n_div, base):
    st = getSampleStyleSheet()
    doc = SimpleDocTemplate(caminho, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.2 * cm, bottomMargin=1.2 * cm)
    cel = st["BodyText"]
    cel.fontSize = 8
    cel.leading = 9.5
    caixa = Table([[Paragraph(f"<b>Comece pelos {fx[0][1]} primeiros da lista:</b> {pct(fx[0][3])} tinham categoria inadequada, "
                              f"contra {pct(base)} na base inteira.", st["BodyText"])]], colWidths=[18 * cm])
    caixa.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff4d6")),
                               ("LINEBEFORE", (0, 0), (0, -1), 4, colors.HexColor("#e69138")), ("LEFTPADDING", (0, 0), (-1, -1), 10)]))
    el = [Paragraph("Chamados para conferir a categoria", st["Title"]), caixa, Spacer(1, 0.3 * cm),
          Paragraph(f"{n_div} de {total} chamados avaliados divergem da categoria registrada. A sugestao apenas prioriza a conferencia; "
                    "a decisao e do servidor.", cel), Spacer(1, 0.2 * cm)]
    dados = [["ID", "Titulo", "Registrada", "Sugerida", "Conf."]]
    for x in topo:
        dados.append([str(x["id"]), Paragraph(html.escape(x["titulo"][:70]), cel), Paragraph(html.escape(x["historica"].split(" > ")[-1]), cel),
                      Paragraph("<b>" + html.escape(x["sugerida"].split(" > ")[-1]) + "</b>", cel), f"{x['confianca']:.2f}"])
    t = Table(dados, colWidths=[2.3 * cm, 7 * cm, 3.6 * cm, 3.6 * cm, 1.5 * cm], repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8edf3")), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f8fa")]),
                           ("FONTSIZE", (0, 0), (-1, -1), 8), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.lightgrey)]))
    d2 = [["Posicao na lista", "Divergencias", "Inadequados", "Proporcao"]] + [[n, str(tt), str(i), pct(p)] for n, tt, i, p in fx]
    t2 = Table(d2, repeatRows=1)
    t2.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8edf3")), ("FONTSIZE", (0, 0), (-1, -1), 8), ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.lightgrey)]))
    el += [t, Spacer(1, 0.4 * cm), Paragraph("<b>Quanto vale conferir mais adiante na lista</b>", cel), Spacer(1, 0.1 * cm), t2]
    doc.build(el)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--predicoes", default="docs/dados/trilha_b/predicoes_com_alternativas.csv")
    ap.add_argument("--saida", required=True)
    ap.add_argument("--topo", type=int, default=15)
    ap.add_argument("--para", default="usuario@setor.br")
    a = ap.parse_args()
    os.makedirs(a.saida, exist_ok=True)
    linhas = carregar(a.snapshot, a.predicoes)
    div = sorted((x for x in linhas if x["sugerida"] != x["historica"]), key=lambda x: -x["confianca"])
    topo = div[: a.topo]
    fx = faixas(div)
    base = sum(1 for x in linhas if x["referencia"] and x["referencia"] != x["historica"]) / len(linhas)
    corpo = corpo_html(topo, fx, len(linhas), len(div), base)
    open(os.path.join(a.saida, "email_corpo.html"), "w", encoding="utf-8").write(corpo)
    pdf = os.path.join(a.saida, "divergencias.pdf")
    gerar_pdf(pdf, topo, fx, len(linhas), len(div), base)
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
