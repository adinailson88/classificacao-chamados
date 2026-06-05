#!/usr/bin/env python3
"""Gera PDFs simples dos documentos Markdown principais."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

RAIZ = Path(__file__).resolve().parents[1]


def esc(txt: str) -> str:
    return (txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def inline_md(txt: str) -> str:
    txt = esc(txt)
    txt = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", txt)
    txt = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", txt)
    txt = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", txt)
    return txt


def tabela(lines: list[str], styles):
    rows = []
    for line in lines:
        if re.match(r"^\s*\|?\s*:?-{3,}", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) > 1:
            rows.append([Paragraph(inline_md(c), styles["Cell"]) for c in cells])
    if not rows:
        return []
    col_count = max(len(r) for r in rows)
    for r in rows:
        while len(r) < col_count:
            r.append(Paragraph("", styles["Cell"]))
    tbl = Table(rows, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f0eb")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#18212a")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfd8d3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return [tbl, Spacer(1, 0.25 * cm)]


def gerar(md_path: Path, pdf_path: Path) -> None:
    raw = md_path.read_text(encoding="utf-8")
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.4 * cm,
        title=md_path.stem,
    )
    ss = getSampleStyleSheet()
    styles = {
        "H1": ParagraphStyle("H1", parent=ss["Heading1"], fontSize=17, leading=21, spaceAfter=10,
                             textColor=colors.HexColor("#0f4f49")),
        "H2": ParagraphStyle("H2", parent=ss["Heading2"], fontSize=13, leading=16, spaceBefore=8, spaceAfter=6,
                             textColor=colors.HexColor("#18212a")),
        "H3": ParagraphStyle("H3", parent=ss["Heading3"], fontSize=11, leading=14, spaceBefore=6, spaceAfter=4),
        "Body": ParagraphStyle("Body", parent=ss["BodyText"], fontSize=9.5, leading=13, spaceAfter=5),
        "Code": ParagraphStyle("Code", parent=ss["Code"], fontName="Courier", fontSize=8, leading=10,
                               backColor=colors.HexColor("#f3f5f2"), borderPadding=4, spaceAfter=5),
        "Cell": ParagraphStyle("Cell", parent=ss["BodyText"], fontSize=7.5, leading=9),
    }
    story = []
    in_code = False
    code_buf: list[str] = []
    table_buf: list[str] = []

    def flush_table():
        nonlocal table_buf
        if table_buf:
            story.extend(tabela(table_buf, styles))
            table_buf = []

    def flush_code():
        nonlocal code_buf
        if code_buf:
            story.append(Paragraph("<br/>".join(esc(x) for x in code_buf), styles["Code"]))
            code_buf = []

    for line in raw.splitlines():
        if line.startswith("```"):
            if in_code:
                flush_code()
                in_code = False
            else:
                flush_table()
                in_code = True
            continue
        if in_code:
            code_buf.append(line)
            continue
        if "|" in line and line.strip().startswith("|"):
            table_buf.append(line)
            continue
        flush_table()
        s = line.strip()
        if not s:
            story.append(Spacer(1, 0.12 * cm))
        elif s.startswith("# "):
            story.append(Paragraph(inline_md(s[2:]), styles["H1"]))
        elif s.startswith("## "):
            story.append(Paragraph(inline_md(s[3:]), styles["H2"]))
        elif s.startswith("### "):
            story.append(Paragraph(inline_md(s[4:]), styles["H3"]))
        elif s.startswith("- "):
            story.append(Paragraph("• " + inline_md(s[2:]), styles["Body"]))
        elif re.match(r"^\d+\.\s+", s):
            story.append(Paragraph(inline_md(s), styles["Body"]))
        elif s.startswith(">"):
            story.append(Paragraph("<i>" + inline_md(s.lstrip("> ").strip()) + "</i>", styles["Body"]))
        else:
            story.append(Paragraph(inline_md(s), styles["Body"]))

    flush_code()
    flush_table()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    doc.build(story)


def main() -> int:
    pares = [
        ("ESTADO_DO_ROTEIRO.md", "docs/ESTADO_DO_ROTEIRO.pdf"),
        ("DOCUMENTACAO_MODELOS_E_ESTATISTICA.md", "docs/DOCUMENTACAO_MODELOS_E_ESTATISTICA.pdf"),
    ]
    for origem, destino in pares:
        gerar(RAIZ / origem, RAIZ / destino)
        print(f"OK: {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
