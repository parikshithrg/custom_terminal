"""Render the tracked R.7 owner-review Markdown into a polished PDF only."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


INK = colors.HexColor("#18212B")
NAVY = colors.HexColor("#16324F")
TEAL = colors.HexColor("#167D7F")
PALE = colors.HexColor("#EAF3F4")
MUTED = colors.HexColor("#617181")
LINE = colors.HexColor("#CAD5DD")
ALERT = colors.HexColor("#A13D32")


def _inline(text: str) -> str:
    value = html.escape(text.strip())
    value = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", value)
    return value


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "CoverTitle", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=25, leading=30, textColor=NAVY, alignment=TA_LEFT,
            spaceAfter=16,
        ),
        "subtitle": ParagraphStyle(
            "CoverMeta", parent=base["BodyText"], fontSize=10.2, leading=15,
            textColor=MUTED, spaceAfter=6,
        ),
        "alert": ParagraphStyle(
            "Alert", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=10.5, leading=15, textColor=ALERT, backColor=colors.HexColor("#FCEDEA"),
            borderColor=colors.HexColor("#E4B8B1"), borderWidth=0.8,
            borderPadding=10, spaceBefore=18, spaceAfter=14,
        ),
        "h1": ParagraphStyle(
            "H1", parent=base["Heading1"], fontName="Helvetica-Bold",
            fontSize=17, leading=21, textColor=NAVY, spaceBefore=7, spaceAfter=10,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "H2", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=12, leading=15, textColor=TEAL, spaceBefore=8, spaceAfter=5,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["BodyText"], fontName="Helvetica",
            fontSize=9.2, leading=13.2, textColor=INK, spaceAfter=7,
        ),
        "bullet": ParagraphStyle(
            "Bullet", parent=base["BodyText"], fontName="Helvetica",
            fontSize=9.1, leading=13, leftIndent=12, firstLineIndent=-7,
            bulletIndent=3, textColor=INK, spaceAfter=4,
        ),
        "code": ParagraphStyle(
            "Code", parent=base["Code"], fontName="Courier", fontSize=7.5,
            leading=10, leftIndent=8, rightIndent=8, backColor=colors.HexColor("#F3F6F8"),
            borderPadding=6, spaceAfter=8,
        ),
        "table_head": ParagraphStyle(
            "TableHead", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=7.8, leading=10, textColor=colors.white,
        ),
        "table_cell": ParagraphStyle(
            "TableCell", parent=base["BodyText"], fontName="Helvetica",
            fontSize=7.6, leading=10, textColor=INK,
        ),
    }


def _table(rows: list[list[str]], styles, width: float):
    columns = max(len(row) for row in rows)
    normalized = [row + [""] * (columns - len(row)) for row in rows]
    data = []
    for row_index, row in enumerate(normalized):
        style = styles["table_head"] if row_index == 0 else styles["table_cell"]
        data.append([Paragraph(_inline(cell), style) for cell in row])
    if columns == 2:
        widths = [width * 0.28, width * 0.72]
    elif columns == 3:
        widths = [width * 0.22, width * 0.24, width * 0.54]
    else:
        widths = [width / columns] * columns
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
    ]))
    return table


def _story(markdown: str, doc_width: float):
    styles = _styles()
    story = [Spacer(1, 31 * mm)]
    lines = markdown.splitlines()
    paragraph: list[str] = []
    in_code = False
    code_lines: list[str] = []
    in_list = False

    def flush_paragraph():
        if paragraph:
            text = " ".join(item.strip() for item in paragraph)
            style = styles["alert"] if text.startswith("NO MARKET ANALYSIS") else styles["body"]
            story.append(Paragraph(_inline(text), style))
            paragraph.clear()

    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped == "```":
            flush_paragraph()
            if in_code:
                story.append(Paragraph("<br/>".join(html.escape(x) for x in code_lines), styles["code"]))
                code_lines.clear()
            in_code = not in_code
            index += 1
            continue
        if in_code:
            code_lines.append(line)
            index += 1
            continue
        if stripped == "[PAGE BREAK]":
            flush_paragraph(); story.append(PageBreak()); in_list = False; index += 1; continue
        if stripped.startswith("|"):
            flush_paragraph()
            table_lines = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            rows = [[cell.strip() for cell in row.strip("|").split("|")] for row in table_lines]
            if len(rows) > 1 and all(set(cell) <= {"-", ":"} for cell in rows[1]):
                rows.pop(1)
            story.extend([_table(rows, styles, doc_width), Spacer(1, 7)])
            continue
        if not stripped:
            flush_paragraph(); in_list = False; index += 1; continue
        if stripped.startswith("# "):
            flush_paragraph(); story.append(Paragraph(_inline(stripped[2:]), styles["title"])); in_list = False; index += 1; continue
        if stripped.startswith("## "):
            flush_paragraph(); story.append(Paragraph(_inline(stripped[3:]), styles["h1"])); in_list = False; index += 1; continue
        if stripped.startswith("### "):
            flush_paragraph(); story.append(Paragraph(_inline(stripped[4:]), styles["h2"])); in_list = False; index += 1; continue
        if stripped.startswith("- "):
            flush_paragraph()
            if not in_list:
                story.append(Spacer(1, 2.5 * mm))
            story.append(Paragraph(_inline(stripped[2:]), styles["bullet"], bulletText="-"))
            in_list = True
            index += 1; continue
        if re.match(r"^\d+\. ", stripped):
            flush_paragraph()
            if not in_list:
                story.append(Spacer(1, 2.5 * mm))
            number, value = stripped.split(". ", 1)
            story.append(Paragraph(_inline(value), styles["bullet"], bulletText=f"{number}."))
            in_list = True
            index += 1; continue
        if in_list:
            story.append(Spacer(1, 2.5 * mm))
        in_list = False
        paragraph.append(stripped.rstrip("  "))
        index += 1
    flush_paragraph()
    return story


def _page(canvas, doc):
    canvas.saveState()
    width, height = A4
    if doc.page > 1:
        canvas.setStrokeColor(LINE)
        canvas.line(20 * mm, height - 16 * mm, width - 20 * mm, height - 16 * mm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(20 * mm, height - 12.5 * mm, "MARKET SYSTEM DEVELOPMENT - STATUS REVIEW")
        canvas.drawRightString(width - 20 * mm, 11 * mm, f"Page {doc.page}")
    canvas.restoreState()


def render(source: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output), pagesize=A4, rightMargin=20 * mm, leftMargin=20 * mm,
        topMargin=21 * mm, bottomMargin=18 * mm,
        title="Market System Development - Status and Pre-Research Review",
        author="custom_terminal project",
        subject="R.7 owner-review status report; research remains blocked",
    )
    story = _story(source.read_text(encoding="utf-8"), doc.width)
    doc.build(story, onFirstPage=_page, onLaterPages=_page)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    render(args.source, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
