import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth
from pypdf import PdfReader, PdfWriter
from pathlib import Path


# ─────────────────────────────────────────────
# Fonts
# ─────────────────────────────────────────────

def _register_fonts():
    font_dir = Path("static/fonts")
    regular = font_dir / "NotoSansDevanagari-Regular.ttf"
    bold = font_dir / "NotoSansDevanagari-Bold.ttf"

    if regular.exists():
        try:
            pdfmetrics.registerFont(TTFont("NotoDeva", str(regular)))
            if bold.exists():
                pdfmetrics.registerFont(TTFont("NotoDeva-Bold", str(bold)))
            return True
        except Exception:
            return False
    return False


HAS_DEVANAGARI_FONT = _register_fonts()


def _pick_font(requested):
    if HAS_DEVANAGARI_FONT and requested in ("Helvetica", "Times-Roman", "Courier"):
        return "NotoDeva"
    return requested


# ─────────────────────────────────────────────
# Low-level draw helpers
# ─────────────────────────────────────────────

def _draw_text(c, text, x, y, font, size, alignment="left", width=0):
    """Draw a single line of text with the given alignment."""
    font = _pick_font(font)
    c.setFont(font, size)

    if alignment == "center" and width:
        c.drawCentredString(x + width / 2, y, text)
    elif alignment == "right" and width:
        c.drawRightString(x + width, y, text)
    else:
        c.drawString(x, y, text)


def _wrap_line(text, font, size, max_width):
    """
    Break a long string into lines that fit within max_width.
    Handles both word-wrapping and character-wrapping for long words.
    """
    if not text:
        return [""]

    words = text.split(" ")
    lines = []
    current = ""

    for word in words:
        test = (current + " " + word).strip() if current else word
        if stringWidth(test, font, size) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)

            # Word itself might be longer than the width → split by chars
            if stringWidth(word, font, size) > max_width:
                buf = ""
                for ch in word:
                    if stringWidth(buf + ch, font, size) <= max_width:
                        buf += ch
                    else:
                        lines.append(buf)
                        buf = ch
                current = buf
            else:
                current = word

    if current:
        lines.append(current)

    return lines or [""]


def _draw_wrapped(c, text, x, y, width, height, font, size, line_height=None):
    """
    Draw multi-line text inside a box.
    • Respects \n in the source text.
    • Wraps long lines automatically.
    • Grows DOWNWARD from (x, y_top) — because y is the top of the box.
    • If height == 0 → no limit (draw everything).
    """
    if not text:
        return

    if line_height is None:
        line_height = size * 1.5

    font = _pick_font(font)
    c.setFont(font, size)

    # Split by real newlines first, then wrap each paragraph
    paragraphs = str(text).split("\n")
    all_lines = []
    for para in paragraphs:
        all_lines.extend(_wrap_line(para, font, size, width))

    # Optional limit
    if height and height > 0:
        max_lines = int(height // line_height)
        all_lines = all_lines[:max_lines]

    # Draw from top → down (y is the TOP baseline)
    for i, line in enumerate(all_lines):
        c.drawString(x, y - (i * line_height), line)


# ─────────────────────────────────────────────
# Main generator
# ─────────────────────────────────────────────

# Fields that should always be treated as multi-line wrapped text
WRAPPED_FIELDS = {"body", "subject", "recipient", "signature"}


def generate_letter_pdf(letter_pad, field_values, output_path=None):
    """
    Overlay dynamic text onto the uploaded letter pad PDF.
    All text fields automatically wrap if they are long.
    """
    positions = {p.field_name: p for p in letter_pad.positions.all()}

    page_w = float(letter_pad.page_width) if letter_pad.page_width else A4[0]
    page_h = float(letter_pad.page_height) if letter_pad.page_height else A4[1]
    if page_w <= 1 or page_h <= 1:
        page_w, page_h = A4

    # ── Build overlay ──
    overlay_buffer = io.BytesIO()
    c = canvas.Canvas(overlay_buffer, pagesize=(page_w, page_h))

    for field_name, value in field_values.items():
        pos = positions.get(field_name)
        if not pos or not value:
            continue

        text = str(value)
        has_newline = "\n" in text

        # Decide whether to wrap
        if field_name in WRAPPED_FIELDS or has_newline:
            _draw_wrapped(
                c,
                text,
                pos.x,
                pos.y,
                pos.width if pos.width else 300,
                pos.height if pos.height else 0,
                pos.font_name,
                pos.font_size,
            )
        else:
            # Single-line fields: if it fits, draw normally
            _draw_text(
                c,
                text,
                pos.x,
                pos.y,
                pos.font_name,
                pos.font_size,
                alignment=pos.alignment,
                width=pos.width,
            )

    c.showPage()
    c.save()
    overlay_buffer.seek(0)

    # ── Merge ──
    base_reader = PdfReader(letter_pad.pdf_file.path)
    overlay_reader = PdfReader(overlay_buffer)

    if len(base_reader.pages) == 0:
        raise ValueError("Uploaded letter pad PDF has no pages.")
    if len(overlay_reader.pages) == 0:
        raise ValueError("Overlay PDF was generated with no pages.")

    writer = PdfWriter()
    base_page = base_reader.pages[0]
    overlay_page = overlay_reader.pages[0]
    base_page.merge_page(overlay_page)
    writer.add_page(base_page)

    for extra in base_reader.pages[1:]:
        writer.add_page(extra)

    out_buffer = io.BytesIO()
    writer.write(out_buffer)
    out_buffer.seek(0)

    if output_path:
        with open(output_path, "wb") as f:
            f.write(out_buffer.read())
        out_buffer.seek(0)

    return out_buffer.getvalue()