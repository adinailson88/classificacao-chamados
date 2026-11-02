import re, sys
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

s = open("artigo_rap.txt", encoding="utf-8").read()
parts = re.split(r"^@(\w+)\n", s, flags=re.M)
blocks = [(parts[i], parts[i + 1].strip()) for i in range(1, len(parts), 2)]

pop = {"A": 11303, "B": 2275, "C": 560}
modelo = (0.93 * pop["A"] + 0.47 * pop["B"] + 0.76 * pop["C"]) / sum(pop.values())

TAB = {
    "TABELA1": ("Tabela 1. Concordância com o histórico, acurácia contra a referência revisada e reclassificação automática, por modelo (n = 14.357)",
                ["Modelo", "Concordância com o histórico", "Acurácia contra a referência", "Corrigidos", "Prejudicados", "Ganho líquido"],
                [["tfidf_embedding", "0,8057", "0,8307", "448", "2.294", "−1.846"],
                 ["LinearSVC sobre caracteres", "0,8027", "0,8280", "450", "2.334", "−1.884"],
                 ["LinearSVC", "0,7976", "0,8241", "457", "2.397", "−1.940"],
                 ["Naive Bayes", "0,7083", "0,7222", "320", "3.723", "−3.403"],
                 ["LSTM bidirecional", "0,6848", "0,7067", "376", "4.002", "−3.626"]],
                "Fonte: elaboração própria. Corrigidos e prejudicados contam os registros em que a predição diverge do histórico e coincide, respectivamente, com a referência ou com o histórico."),
    "TABELA2": ("Tabela 2. Automação seletiva com limiar com garantia (Learn-then-Test) e limiar convencional, em 14 cenários de mudança de distribuição",
                ["Erro-alvo", "Limiar", "Cobertura", "Erro no teste", "Resultado"],
                [["10%", "Com garantia", "42% a 68%", "1,4% a 9,3%", "Nenhuma violação nos 14 cenários"],
                 ["10%", "Convencional", "61% a 75%", "10,2% e 11,0% nos dois cenários excedidos", "Excedeu o alvo em 2 de 14 cenários"],
                 ["5%", "Com garantia", "25,0% a 35,9%", "1,1% a 2,0%", "Certificado em 3 de 14 cenários"],
                 ["5%", "Convencional", "47% a 58%", "não reportado", "Violou o alvo em até 32,5% das reamostragens"]],
                "Fonte: elaboração própria."),
    "TABELA3": ("Tabela 3. Concordância do segundo avaliador cego com a referência revisada, com o histórico e com o modelo principal",
                ["Estrato", "Chamados na população", "Amostra", "Com a referência", "Com o histórico", "Com o modelo"],
                [["A (histórico confirmado, modelo acertou)", "11.303", "100", "93%", "93%", "93%"],
                 ["B (histórico confirmado, modelo errou)", "2.275", "100", "26%", "26%", "47%"],
                 ["C (histórico substituído)", "560", "100", "80%", "10%", "76%"],
                 ["Ponderada pela população", "14.138", "300", "81,7%", "78,9%", ("%.1f%%" % (modelo * 100)).replace(".", ",")]],
                "Fonte: elaboração própria. Os 217 chamados pré-triados ficaram fora do sorteio."),
}

d = Document()
sec = d.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
sec.top_margin, sec.bottom_margin, sec.left_margin, sec.right_margin = Cm(3), Cm(2), Cm(3), Cm(2)
st = d.styles["Normal"]
st.font.name = "Times New Roman"
st.font.size = Pt(12)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")


def par(text="", bold=False, italic=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=True, size=12, spacing=1.5, hanging=False, keep=False):
    p = d.add_paragraph()
    f = p.paragraph_format
    f.alignment = align
    f.line_spacing = spacing
    f.space_after = Pt(6)
    if hanging:
        f.left_indent = Cm(1.25)
        f.first_line_indent = Cm(-1.25)
    elif indent:
        f.first_line_indent = Cm(1.25)
    if keep:
        f.keep_with_next = True
    r = p.add_run(text)
    r.bold, r.italic = bold, italic
    r.font.size = Pt(size)
    r.font.name = "Times New Roman"
    return p


def borda(cell, **kw):
    tcPr = cell._tc.get_or_add_tcPr()
    b = OxmlElement("w:tcBorders")
    for edge, val in kw.items():
        el = OxmlElement("w:" + edge)
        el.set(qn("w:val"), val)
        el.set(qn("w:sz"), "6")
        el.set(qn("w:color"), "000000")
        b.append(el)
    tcPr.append(b)


def tabela(k):
    cap, head, rows, nota = TAB[k]
    par(cap, bold=True, indent=False, align=WD_ALIGN_PARAGRAPH.LEFT, size=10, spacing=1.15, keep=True)
    t = d.add_table(rows=1 + len(rows), cols=len(head))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, h in enumerate(head):
        c = t.rows[0].cells[j]
        c.text = ""
        r = c.paragraphs[0].add_run(h)
        r.bold, r.font.size = True, Pt(10)
        borda(c, top="single", bottom="single")
    for i, row in enumerate(rows, 1):
        for j, v in enumerate(row):
            c = t.rows[i].cells[j]
            c.text = ""
            r = c.paragraphs[0].add_run(v)
            r.font.size = Pt(10)
            if i == len(rows):
                borda(c, bottom="single")
    par(nota, indent=False, align=WD_ALIGN_PARAGRAPH.LEFT, size=10, spacing=1.15)


for k, v in blocks:
    if k in ("TITULO_PT", "TITULO_EN"):
        par(v, bold=True, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
    elif k == "RESUMO":
        par("Resumo", bold=True, indent=False, align=WD_ALIGN_PARAGRAPH.LEFT, keep=True)
        par(v)
    elif k == "PALAVRAS":
        p = par("", indent=False)
        r = p.add_run("Palavras-chave: ")
        r.bold = True
        p.add_run(v)
    elif k == "ABSTRACT":
        par("Abstract", bold=True, indent=False, align=WD_ALIGN_PARAGRAPH.LEFT, keep=True)
        par(v)
    elif k == "KEYWORDS":
        p = par("", indent=False)
        r = p.add_run("Keywords: ")
        r.bold = True
        p.add_run(v)
    elif k == "H1":
        par(v, bold=True, indent=False, align=WD_ALIGN_PARAGRAPH.LEFT, keep=True)
    elif k == "H2":
        par(v, bold=True, italic=True, indent=False, align=WD_ALIGN_PARAGRAPH.LEFT, keep=True)
    elif k == "P":
        par(v)
    elif k in TAB:
        tabela(k)
    elif k == "REFERENCIAS":
        par("Referências", bold=True, indent=False, align=WD_ALIGN_PARAGRAPH.LEFT, keep=True)
        for line in v.split("\n"):
            par(line.strip(), hanging=True, align=WD_ALIGN_PARAGRAPH.LEFT)

d.core_properties.author = ""
d.core_properties.title = ""
out = sys.argv[1]
d.save(out)
txt = "\n".join(p.text for p in d.paragraphs)
tab = " ".join(c.text for t in d.tables for r in t.rows for c in r.cells)
print("palavras (parágrafos):", len(txt.split()), "| tabelas:", len(tab.split()), "| total:", len(txt.split()) + len(tab.split()))
