"""Build the final report .docx from the Markdown chapter sources.

Usage:
    backend/venv/Scripts/python.exe report/build/build_docx.py

Regenerates report/build/FaceAttend-FYP-Report.docx from
report/chapters/chapter1.md .. chapter5.md and report/references/references.md
every time it is run, so the whole report can be rebuilt consistently
whenever a chapter changes. Mermaid diagrams embedded in the chapters are
rendered to PNG images (via @mermaid-js/mermaid-cli through npx) and cached
in report/build/figures/, keyed by a hash of the diagram source, so an
unchanged diagram is not re-rendered on every build.
"""

import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[2]
CHAPTERS_DIR = ROOT / "report" / "chapters"
REFERENCES_FILE = ROOT / "report" / "references" / "references.md"
FIGURES_DIR = Path(__file__).resolve().parent / "figures"
OUTPUT_FILE = Path(__file__).resolve().parent / "FaceAttend-FYP-Report.docx"

CHAPTER_FILES = [
    CHAPTERS_DIR / "chapter1.md",
    CHAPTERS_DIR / "chapter2.md",
    CHAPTERS_DIR / "chapter3.md",
    CHAPTERS_DIR / "chapter4.md",
    CHAPTERS_DIR / "chapter5.md",
]

FONT_NAME = "Times New Roman"
BODY_SIZE = Pt(12)
CODE_FONT = "Courier New"
CODE_SIZE = Pt(10)


def set_default_font(document: Document) -> None:
    style = document.styles["Normal"]
    style.font.name = FONT_NAME
    style.font.size = BODY_SIZE
    # Ensure East Asian / complex-script font fallback also uses Times New Roman
    rpr = style.element.get_or_add_rPr()
    rFonts = rpr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.append(rFonts)
    rFonts.set(qn("w:eastAsia"), FONT_NAME)


def double_space(paragraph) -> None:
    pf = paragraph.paragraph_format
    pf.line_spacing = 2.0
    pf.space_after = Pt(0)


def add_body_paragraph(document: Document, justify: bool = True):
    p = document.add_paragraph()
    double_space(p)
    if justify:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    return p


INLINE_PATTERN = re.compile(r"(\*\*.+?\*\*|`.+?`)")


def add_runs_with_inline_formatting(paragraph, text: str) -> None:
    """Split `text` on **bold** and `code` spans and add formatted runs."""
    pos = 0
    for match in INLINE_PATTERN.finditer(text):
        if match.start() > pos:
            run = paragraph.add_run(text[pos : match.start()])
            run.font.name = FONT_NAME
            run.font.size = BODY_SIZE
        token = match.group(0)
        if token.startswith("**"):
            run = paragraph.add_run(token[2:-2])
            run.font.name = FONT_NAME
            run.font.size = BODY_SIZE
            run.bold = True
        elif token.startswith("`"):
            run = paragraph.add_run(token[1:-1])
            run.font.name = CODE_FONT
            run.font.size = Pt(11)
        pos = match.end()
    if pos < len(text):
        run = paragraph.add_run(text[pos:])
        run.font.name = FONT_NAME
        run.font.size = BODY_SIZE


def add_heading(document: Document, text: str, level: int) -> None:
    p = document.add_paragraph()
    p.paragraph_format.space_before = Pt(14 if level == 1 else 10)
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.line_spacing = 1.5
    if level == 1:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        size = Pt(16)
    elif level == 2:
        size = Pt(13)
    else:
        size = Pt(12)
    run = p.add_run(text)
    run.font.name = FONT_NAME
    run.font.size = size
    run.bold = True


def add_caption(document: Document, text: str) -> None:
    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(12)
    p.paragraph_format.line_spacing = 1.0
    run = p.add_run(text)
    run.font.name = FONT_NAME
    run.font.size = BODY_SIZE
    run.italic = True


def add_code_block(document: Document, lines: list[str]) -> None:
    for line in lines:
        p = document.add_paragraph()
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.left_indent = Inches(0.3)
        run = p.add_run(line if line else " ")
        run.font.name = CODE_FONT
        run.font.size = CODE_SIZE
    # a little breathing room after the block
    spacer = document.add_paragraph()
    spacer.paragraph_format.space_after = Pt(0)
    spacer.paragraph_format.line_spacing = 1.0


def add_table(document: Document, rows: list[list[str]]) -> None:
    if not rows:
        return
    n_cols = len(rows[0])
    table = document.add_table(rows=0, cols=n_cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    for r, row_values in enumerate(rows):
        row_cells = table.add_row().cells
        for c, value in enumerate(row_values):
            cell = row_cells[c]
            cell.text = ""
            p = cell.paragraphs[0]
            p.paragraph_format.line_spacing = 1.0
            run = p.add_run(value)
            run.font.name = FONT_NAME
            run.font.size = Pt(10)
            run.bold = r == 0
    spacer = document.add_paragraph()
    spacer.paragraph_format.space_after = Pt(0)


def mermaid_hash(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]


def render_mermaid(source: str) -> Path | None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    key = mermaid_hash(source)
    png_path = FIGURES_DIR / f"{key}.png"
    if png_path.exists():
        return png_path

    mmd_path = FIGURES_DIR / f"{key}.mmd"
    mmd_path.write_text(source, encoding="utf-8")
    npx_path = shutil.which("npx") or "npx"
    try:
        result = subprocess.run(
            [npx_path, "@mermaid-js/mermaid-cli", "-i", str(mmd_path), "-o", str(png_path),
             "-b", "white", "--scale", "2"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0 or not png_path.exists():
            print(f"  WARNING: mermaid render failed for diagram {key} ({result.returncode}):", file=sys.stderr)
            print(f"  --- source ---\n{source}\n--- stderr ---\n{result.stderr[-1500:]}", file=sys.stderr)
            return None
        return png_path
    except Exception as exc:  # noqa: BLE001
        print(f"  WARNING: mermaid render raised {exc}", file=sys.stderr)
        return None
    finally:
        mmd_path.unlink(missing_ok=True)


def is_table_separator(line: str) -> bool:
    return bool(re.match(r"^\|?[\s:|-]+\|?$", line)) and "-" in line


def parse_table_row(line: str) -> list[str]:
    cells = line.strip().strip("|").split("|")
    return [c.strip() for c in cells]


def process_markdown(document: Document, text: str) -> None:
    lines = text.split("\n")
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # Fenced code block (``` ... ```), mermaid gets special image treatment
        if stripped.startswith("```"):
            lang = stripped[3:].strip()
            block_lines = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                block_lines.append(lines[i])
                i += 1
            i += 1  # skip closing fence

            if lang == "mermaid":
                png_path = render_mermaid("\n".join(block_lines))
                if png_path:
                    p = document.add_paragraph()
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run = p.add_run()
                    run.add_picture(str(png_path), width=Inches(5.5))
                else:
                    add_code_block(document, block_lines)
            else:
                add_code_block(document, block_lines)
            continue

        # Headings
        if stripped.startswith("### "):
            add_heading(document, stripped[4:], level=3)
            i += 1
            continue
        if stripped.startswith("## "):
            add_heading(document, stripped[3:], level=2)
            i += 1
            continue
        if stripped.startswith("# "):
            add_heading(document, stripped[2:], level=1)
            i += 1
            continue

        # Whole-line italic caption: *text*  (but not **bold**)
        if stripped.startswith("*") and stripped.endswith("*") and not stripped.startswith("**"):
            add_caption(document, stripped[1:-1])
            i += 1
            continue

        # Markdown table
        if stripped.startswith("|") and i + 1 < n and is_table_separator(lines[i + 1].strip()):
            header = parse_table_row(stripped)
            i += 2  # skip header and separator
            rows = [header]
            while i < n and lines[i].strip().startswith("|"):
                rows.append(parse_table_row(lines[i].strip()))
                i += 1
            add_table(document, rows)
            continue

        # Ordinary paragraph
        p = add_body_paragraph(document)
        add_runs_with_inline_formatting(p, stripped)
        i += 1


def build_references(document: Document) -> None:
    add_heading(document, "REFERENCES", level=1)
    text = REFERENCES_FILE.read_text(encoding="utf-8")
    lines = [l for l in text.split("\n") if l.strip() and not l.strip().startswith("# ")]
    for line in lines:
        p = document.add_paragraph()
        p.paragraph_format.line_spacing = 2.0
        p.paragraph_format.left_indent = Inches(0.5)
        p.paragraph_format.first_line_indent = Inches(-0.5)
        p.paragraph_format.space_after = Pt(0)
        add_runs_with_inline_formatting(p, line.strip())


def main() -> None:
    document = Document()
    set_default_font(document)

    section = document.sections[0]
    section.left_margin = Inches(1.5)
    section.right_margin = Inches(1)
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)

    for chapter_path in CHAPTER_FILES:
        print(f"Processing {chapter_path.name} ...")
        text = chapter_path.read_text(encoding="utf-8")
        process_markdown(document, text)
        document.add_page_break()

    print("Building references ...")
    build_references(document)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    document.save(OUTPUT_FILE)
    print(f"\nSaved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
