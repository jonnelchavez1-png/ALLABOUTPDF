"""Watermarks and page numbers."""
from __future__ import annotations

import io
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader, PdfWriter, Transformation
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from core.pdf_exporter import export_writer
from core.pdf_reader import open_pdf
from utils.error_handler import ValidationError

POSITIONS = ("bottom-center", "bottom-left", "bottom-right", "top-center", "top-left", "top-right")


def _font(font_path: str | None) -> str:
    """Helvetica by default (Latin text only). Pass a .ttf to support other scripts."""
    if not font_path:
        return "Helvetica"
    name = f"user_{abs(hash(font_path))}"
    if name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(name, font_path))
    return name


def _overlay(width: float, height: float, draw) -> "PdfReader":
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))
    draw(c)
    c.showPage()
    c.save()
    buf.seek(0)
    return PdfReader(buf)


def _display_to_raw(rotation: int, w: float, h: float, left: float, bottom: float) -> Transformation:
    """Map an overlay drawn in DISPLAYED coordinates onto the raw page, so it appears upright
    even on pages with a /Rotate value. (w, h) = raw mediabox size."""
    ctm = {0: (1, 0, 0, 1, 0, 0), 90: (0, 1, -1, 0, w, 0),
           180: (-1, 0, 0, -1, w, h), 270: (0, -1, 1, 0, 0, h)}[rotation % 360]
    a, b, c, d, e, f = ctm
    return Transformation(ctm=(a, b, c, d, e + left, f + bottom))


def _stamp(src, dest, make_draw, pages: Iterable[int] | None, password, overwrite) -> Path:
    reader = open_pdf(src, password)
    total = len(reader.pages)
    chosen = set(range(total)) if pages is None else set(pages)
    if any(not 0 <= i < total for i in chosen):
        raise ValidationError("Selected page does not exist.")
    writer = PdfWriter(clone_from=reader)
    for i, page in enumerate(writer.pages):
        if i not in chosen:
            continue
        rot = int(page.rotation or 0) % 360
        raw_w, raw_h = float(page.mediabox.width), float(page.mediabox.height)
        left, bottom = float(page.mediabox.left), float(page.mediabox.bottom)
        dw, dh = (raw_h, raw_w) if rot in (90, 270) else (raw_w, raw_h)
        overlay = _overlay(dw, dh, make_draw(i, dw, dh)).pages[0]
        page.merge_transformed_page(overlay, _display_to_raw(rot, raw_w, raw_h, left, bottom))
    return export_writer(writer, dest, overwrite=overwrite, expected_pages=total, protect=[Path(src)])


def add_text_watermark(src, dest, text: str, *, font_size: float = 48, opacity: float = 0.25,
                       angle: float = 45, color: tuple[float, float, float] = (0.5, 0.5, 0.5),
                       pages: Iterable[int] | None = None, font_path: str | None = None,
                       password: str | None = None, overwrite: bool = False) -> Path:
    """Centered text watermark on the chosen 0-based pages (all pages by default)."""
    if not text.strip():
        raise ValidationError("Enter the watermark text.")
    if not 0.0 < opacity <= 1.0:
        raise ValidationError("Opacity must be between 0 and 1.")
    font = _font(font_path)

    def make_draw(_i, w, h):
        def draw(c):
            c.saveState()
            c.setFillColorRGB(*color)
            c.setFillAlpha(opacity)
            c.setFont(font, font_size)
            c.translate(w / 2, h / 2)
            c.rotate(angle)
            c.drawCentredString(0, -font_size / 3, text)
            c.restoreState()
        return draw

    return _stamp(src, dest, make_draw, pages, password, overwrite)


def add_page_numbers(src, dest, *, position: str = "bottom-center", start_number: int = 1,
                     fmt: str = "{n}", font_size: float = 10, margin: float = 28,
                     pages: Iterable[int] | None = None, font_path: str | None = None,
                     password: str | None = None, overwrite: bool = False) -> Path:
    """Number pages. `fmt` may use {n} (number) and {total} (page count of the document)."""
    if position not in POSITIONS:
        raise ValidationError("Unknown page number position.")
    if "{n}" not in fmt:
        raise ValidationError("The page number format must contain {n}.")
    font = _font(font_path)
    total = len(open_pdf(src, password).pages)
    vertical, horizontal = position.split("-")

    def make_draw(i, w, h):
        label = fmt.format(n=start_number + i, total=total + start_number - 1)
        x = {"left": margin, "center": w / 2, "right": w - margin}[horizontal]
        y = margin if vertical == "bottom" else h - margin - font_size

        def draw(c):
            c.setFont(font, font_size)
            c.setFillColorRGB(0, 0, 0)
            {"left": c.drawString, "center": c.drawCentredString, "right": c.drawRightString}[horizontal](x, y, label)
        return draw

    return _stamp(src, dest, make_draw, pages, password, overwrite)
