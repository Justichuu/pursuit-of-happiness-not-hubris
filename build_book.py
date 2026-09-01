"""Build a trade-paperback PDF from BOOK.md, with a product-release gate."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import validate


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "BOOK.md"
OUTPUT_DIR = ROOT / "release"
PAGE_W = 6 * 72
PAGE_H = 9 * 72
MARGIN_X = 54
MARGIN_TOP = 64
MARGIN_BOTTOM = 56
BODY_SIZE = 11
BODY_LEAD = 15
TITLE = "The Pursuit of Happiness over Hubris"
SHORT_TITLE = "Happiness over Hubris"

# Adobe Times-Roman widths for ASCII 32-126, in thousandths of an em.
TIMES_WIDTHS = (
    250, 333, 408, 500, 500, 833, 778, 180, 333, 333, 500, 564, 250, 333,
    250, 278, 500, 500, 500, 500, 500, 500, 500, 500, 500, 500, 278, 278,
    564, 564, 564, 444, 921, 722, 667, 667, 722, 611, 556, 722, 722, 333,
    389, 722, 611, 889, 722, 722, 556, 722, 667, 556, 611, 722, 722, 944,
    722, 722, 611, 333, 278, 333, 469, 500, 333, 444, 500, 444, 500, 444,
    333, 500, 500, 278, 278, 500, 278, 778, 500, 500, 500, 500, 333, 389,
    278, 500, 500, 722, 500, 500, 444, 480, 200, 480, 541,
)
QUOTE_WIDTH = 333
IRONY_MARK = "\u2e2e"
RIGHT_QUOTE = "\u2019"
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
BOLD = re.compile(r"\*\*([^*]+)\*\*")
ITALIC = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)|_([^_]+)_")


def text_width(text: str, size: float) -> float:
    """Return the rendered width of text in Times-Roman at size."""
    total = 0
    for char in text:
        if char in {IRONY_MARK, "?"}:
            total += TIMES_WIDTHS[ord("?") - 32]
        elif char in {RIGHT_QUOTE, "'"}:
            total += QUOTE_WIDTH
        else:
            code = ord(char)
            if 32 <= code <= 126:
                total += TIMES_WIDTHS[code - 32]
            else:
                total += 500
    return total * size / 1000.0


def wrap_text(text: str, size: float, width: float) -> List[str]:
    """Wrap a single paragraph on spaces to fit width."""
    words = text.split()
    if not words:
        return []
    lines = []
    current: List[str] = []
    current_w = 0.0
    for word in words:
        word_w = text_width(word, size)
        space_w = text_width(" ", size) if current else 0.0
        if current and current_w + space_w + word_w > width:
            lines.append(" ".join(current))
            current = [word]
            current_w = word_w
        else:
            current.append(word)
            current_w += space_w + word_w
    if current:
        lines.append(" ".join(current))
    return lines


def visible_text(text: str) -> str:
    """Strip markdown markers that should not appear in the book PDF."""
    text = LINK.sub(r"\1", text)
    text = BOLD.sub(r"\1", text)
    text = ITALIC.sub(lambda match: match.group(1) or match.group(2), text)
    return text.replace("`", "")


def heading_block(line: str) -> Optional[Tuple[str, str]]:
    """Return a heading block if the line is a markdown heading."""
    if line.startswith("# "):
        return ("title", visible_text(line[2:].strip()))
    if line.startswith("## "):
        return ("chapter", visible_text(line[3:].strip()))
    if line.startswith("### "):
        return ("section", visible_text(line[4:].strip()))
    return None


def special_block(line: str) -> Optional[Tuple[str, str]]:
    """Return a labeled structural block, or None for ordinary prose."""
    stripped = line.strip()
    if stripped == validate.STRICT_VOICES:
        return ("rule", "Voices: separated.")
    if stripped in validate.VOICE_MARKERS:
        return ("voice", validate.VOICE_MARKERS[stripped])
    if line.startswith("- "):
        return ("item", visible_text(line[2:].strip()))
    if line.startswith("Status:"):
        return ("status", stripped)
    if line.startswith("By "):
        return ("author", visible_text(line[3:].strip()))
    return None


def parse_blocks(markdown: str) -> List[Tuple[str, str]]:
    """Turn BOOK.md into layout blocks: kind and visible text."""
    body = COMMENT.sub("", markdown)
    blocks: List[Tuple[str, str]] = []
    paragraph: List[str] = []
    quote: List[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            blocks.append(("body", visible_text(" ".join(paragraph))))
            paragraph.clear()

    def flush_quote() -> None:
        if quote:
            blocks.append(("quote", visible_text(" ".join(quote))))
            quote.clear()

    for raw in body.splitlines():
        line = raw.rstrip()
        if line.startswith("```"):
            flush_paragraph()
            flush_quote()
            continue
        if line.startswith(">"):
            flush_paragraph()
            quote.append(line[1:].strip())
            continue
        flush_quote()
        if not line.strip():
            flush_paragraph()
            continue
        heading = heading_block(line)
        if heading:
            flush_paragraph()
            blocks.append(heading)
            continue
        special = special_block(line)
        if special:
            flush_paragraph()
            blocks.append(special)
            continue
        paragraph.append(line.strip())
    flush_quote()
    flush_paragraph()
    return blocks


def pdf_escape(text: str) -> str:
    """Encode visible text as a WinAnsi PDF literal, minus the irony mark."""
    out = []
    for char in text:
        if char == IRONY_MARK:
            out.append("\x00")
            continue
        if char == RIGHT_QUOTE:
            out.append(chr(0x92))
            continue
        code = ord(char)
        if char in "\\()":
            out.append("\\" + char)
        elif 32 <= code <= 126:
            out.append(char)
        else:
            out.append("?")
    return "".join(out)


def text_ops(x: float, y: float, text: str, font: str, size: float) -> str:
    """Return PDF operators that draw one baseline of text."""
    ops = []
    cursor = x
    run: List[str] = []

    def flush_run() -> None:
        """Paint the current ordinary-text run and advance the cursor."""
        nonlocal cursor
        if not run:
            return
        chunk = "".join(run)
        ops.append(
            f"BT /{font} {size:g} Tf 1 0 0 1 {cursor:.2f} {y:.2f} Tm "
            f"({pdf_escape(chunk)}) Tj ET\n"
        )
        cursor += text_width(chunk, size)
        run.clear()

    for char in text:
        if char == IRONY_MARK:
            flush_run()
            mark_w = text_width("?", size)
            ops.append(
                f"q 1 0 0 1 {cursor + mark_w:.2f} {y:.2f} cm "
                f"-1 0 0 1 0 0 cm BT /{font} {size:g} Tf 0 0 Td "
                f"(?) Tj ET Q\n"
            )
            cursor += mark_w
        else:
            run.append(char)
    flush_run()
    return "".join(ops)


class BookPdf:
    """Accumulate trade-size pages and write a PDF 1.4 file."""

    def __init__(self, draft: bool) -> None:
        self.draft = draft
        self.pages: List[str] = []
        self.stream = ""
        self.y = PAGE_H - MARGIN_TOP
        self.chapter = TITLE
        self.page_no = 0
        self.folio = 0

    def content_width(self) -> float:
        """Return the inner width of the text block."""
        return PAGE_W - (MARGIN_X * 2)

    def new_page(self, numbered: bool = True) -> None:
        """Close the current page if any and open a new one."""
        if self.stream:
            self.pages.append(self.stream)
            self.stream = ""
        self.page_no += 1
        if numbered:
            self.folio += 1
        self.y = PAGE_H - MARGIN_TOP
        if self.draft:
            self.stream += (
                "0.88 g BT /F2 28 Tf 1 0 0 1 90 320 Tm "
                "(DRAFT NOT A PRODUCT RELEASE) Tj ET 0 g\n"
            )
        if numbered and self.folio:
            self.stream += text_ops(
                PAGE_W / 2 - text_width(str(self.folio), 9) / 2,
                32,
                str(self.folio),
                "F1",
                9,
            )
            running = SHORT_TITLE if self.page_no % 2 == 0 else self.chapter
            running = running[:42]
            self.stream += text_ops(
                MARGIN_X,
                PAGE_H - 36,
                running,
                "F1",
                8,
            )

    def ensure_space(self, need: float) -> None:
        """Start a new numbered page when the remaining space is too small."""
        if self.y - need < MARGIN_BOTTOM:
            self.new_page(True)

    def add_lines(
        self,
        lines: List[str],
        font: str,
        size: float,
        lead: float,
        indent: float = 0.0,
    ) -> None:
        """Paint wrapped lines and advance the cursor."""
        for line in lines:
            self.ensure_space(lead)
            self.stream += text_ops(
                MARGIN_X + indent,
                self.y,
                line,
                font,
                size,
            )
            self.y -= lead

    def add_gap(self, amount: float) -> None:
        """Add vertical space, moving to a new page if needed."""
        self.ensure_space(amount)
        self.y -= amount

    def close(self) -> None:
        """Flush the last open page."""
        if self.stream:
            self.pages.append(self.stream)
            self.stream = ""


def layout_front_matter(pdf: BookPdf, blocks: List[Tuple[str, str]]) -> None:
    """Lay out the title page, verso notice, and contents."""
    pdf.new_page(False)
    pdf.y = PAGE_H - 180
    pdf.add_lines(wrap_text(TITLE.upper(), 18, pdf.content_width()), "F2", 18, 22)
    pdf.add_gap(18)
    pdf.add_lines(["Justichuu"], "F1", 14, 18)
    pdf.add_gap(28)
    status = "Living public draft"
    for kind, text in blocks:
        if kind == "status":
            status = text
            break
    pdf.add_lines(wrap_text(status, 11, pdf.content_width()), "F3", 11, 14)
    if pdf.draft:
        pdf.add_gap(16)
        note = "This PDF is a layout draft. It is not a product release."
        pdf.add_lines(wrap_text(note, 11, pdf.content_width()), "F2", 11, 14)

    pdf.new_page(False)
    pdf.add_lines(["A cut is not an ending"], "F2", 14, 18)
    pdf.add_gap(10)
    verso = (
        "A product release is a numbered cut of BOOK.md, allowed only after "
        "Justichuu fills every reserved slot and changes the status line to "
        "product release. This file is generated from the public markdown. "
        "The living draft can continue after a cut. Original text is offered "
        "under CC BY-SA 4.0. See LICENSE.md."
    )
    if pdf.draft:
        verso = (
            "NOT A PRODUCT RELEASE. Reserved slots are still unwritten, or "
            "the status line is still a living public draft. " + verso
        )
    pdf.add_lines(wrap_text(verso, 11, pdf.content_width()), "F1", 11, 15)
    pdf.new_page(True)
    pdf.add_lines(["Contents"], "F2", 16, 22)
    pdf.add_gap(8)
    for kind, text in blocks:
        if kind == "chapter":
            pdf.add_lines([text], "F1", 11, 16)


def layout_block(pdf: BookPdf, kind: str, text: str) -> None:
    """Lay out one body block on the current page sequence."""
    if kind == "section":
        pdf.add_gap(10)
        pdf.add_lines(wrap_text(text, 13, pdf.content_width()), "F2", 13, 17)
        pdf.add_gap(6)
        return
    if kind == "rule":
        pdf.add_lines([text], "F3", 10, 13)
        pdf.add_gap(6)
        return
    if kind == "voice":
        pdf.add_gap(8)
        pdf.add_lines([f"Voice: {text}"], "F2", 9, 12)
        pdf.add_gap(4)
        return
    if kind == "quote":
        width = pdf.content_width() - 18
        pdf.add_lines(wrap_text(text, 11, width), "F3", 11, 15, 18)
        pdf.add_gap(6)
        return
    if kind == "item":
        width = pdf.content_width() - 12
        pdf.add_lines(
            wrap_text(f"- {text}", BODY_SIZE, width),
            "F1",
            BODY_SIZE,
            BODY_LEAD,
            12,
        )
        return
    pdf.add_lines(wrap_text(text, BODY_SIZE, pdf.content_width()), "F1", BODY_SIZE, BODY_LEAD)
    pdf.add_gap(6)


def layout_book(blocks: List[Tuple[str, str]], draft: bool) -> BookPdf:
    """Place parsed blocks onto trade pages."""
    pdf = BookPdf(draft)
    layout_front_matter(pdf, blocks)
    for kind, text in blocks:
        if kind in {"title", "author", "status"}:
            continue
        if kind == "chapter":
            pdf.chapter = text
            pdf.new_page(True)
            pdf.y = PAGE_H - 140
            pdf.add_lines(wrap_text(text, 16, pdf.content_width()), "F2", 16, 20)
            pdf.add_gap(16)
            continue
        layout_block(pdf, kind, text)
    pdf.close()
    return pdf


def _pdf_objects(pdf: BookPdf) -> Tuple[List[bytes], int]:
    """Return PDF object bytes and the catalog object number."""
    objects: List[bytes] = []

    def add_text(data: str) -> int:
        objects.append(data.encode("latin-1", errors="replace"))
        return len(objects)

    def add_bytes(data: bytes) -> int:
        objects.append(data)
        return len(objects)

    font_ids = {
        name: add_text(
            f"<< /Type /Font /Subtype /Type1 /BaseFont {base} "
            f"/Encoding /WinAnsiEncoding >>"
        )
        for name, base in (
            ("F1", "/Times-Roman"),
            ("F2", "/Times-Bold"),
            ("F3", "/Times-Italic"),
        )
    }
    page_ids = []
    for stream in pdf.pages:
        raw = stream.encode("latin-1", errors="replace")
        contents_id = add_bytes(
            f"<< /Length {len(raw)} >>\nstream\n".encode("ascii")
            + raw
            + b"\nendstream"
        )
        resources = " ".join(
            f"/{name} {ident} 0 R" for name, ident in font_ids.items()
        )
        page_ids.append(
            add_text(
                f"<< /Type /Page /Parent 0 0 R "
                f"/MediaBox [0 0 {PAGE_W} {PAGE_H}] "
                f"/Resources << /Font << {resources} >> >> "
                f"/Contents {contents_id} 0 R >>"
            )
        )
    pages_id = add_text(
        "<< /Type /Pages /Count "
        f"{len(page_ids)} /Kids ["
        + " ".join(f"{item} 0 R" for item in page_ids)
        + "] >>"
    )
    for page_id in page_ids:
        objects[page_id - 1] = objects[page_id - 1].replace(
            b"/Parent 0 0 R",
            f"/Parent {pages_id} 0 R".encode("ascii"),
        )
    catalog_id = add_text(f"<< /Type /Catalog /Pages {pages_id} 0 R >>")
    return objects, catalog_id


def write_pdf(pdf: BookPdf, path: Path) -> None:
    """Write a finished BookPdf to path as PDF 1.4."""
    objects, catalog_id = _pdf_objects(pdf)
    buf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(buf))
        buf.extend(f"{index} 0 obj\n".encode("ascii"))
        buf.extend(obj)
        buf.extend(b"\nendobj\n")
    xref = len(buf)
    buf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    buf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        buf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    buf.extend(
        (
            f"trailer << /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n"
        ).encode("ascii")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(buf)


def product_filename(version: str) -> str:
    """Return the product PDF filename for a version string."""
    return f"pursuit-of-happiness-over-hubris-v{version}.pdf"


def draft_filename() -> str:
    """Return the marked draft PDF filename."""
    return "pursuit-of-happiness-over-hubris-DRAFT.pdf"


def build(argv: List[str]) -> int:
    """Build a draft or product PDF according to argv."""
    release = "--release" in argv
    if release:
        code = validate.main(["--release"])
        if code != 0:
            print("Product PDF refused: validate.py --release failed.")
            return code
        version = validate.product_version()
        if not version:
            print("Product PDF refused: no product version.")
            return 1
        name = product_filename(version)
        draft = False
    else:
        name = draft_filename()
        draft = True
        if validate.main([]) != 0:
            print("Draft PDF refused: validate.py failed.")
            return 1

    markdown = SOURCE.read_text(encoding="utf-8")
    blocks = parse_blocks(markdown)
    pdf = layout_book(blocks, draft)
    target = OUTPUT_DIR / name
    write_pdf(pdf, target)
    kind = "product" if release else "draft"
    print(f"Wrote {kind} PDF: {target.relative_to(ROOT).as_posix()}")
    return 0


def main(argv: List[str]) -> int:
    """CLI entry for the book PDF builder."""
    return build(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
