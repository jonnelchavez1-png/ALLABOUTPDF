"""Test helpers: build real sample PDFs and images (no binary fixtures in the repo)."""
from __future__ import annotations

import os
import random
from pathlib import Path

from PIL import Image
from reportlab.pdfgen import canvas


def make_pdf(path: Path, sizes=((595, 842),), label="Doc") -> Path:
    """One page per entry in `sizes` (width, height in points); each page says '<label> page N'."""
    c = canvas.Canvas(str(path))
    for n, (w, h) in enumerate(sizes, start=1):
        c.setPageSize((w, h))
        c.setFont("Helvetica", 24)
        c.drawString(50, h - 80, f"{label} page {n}")
        c.showPage()
    c.save()
    return path


def make_image(path: Path, size=(400, 300), color=(200, 30, 30), mode="RGB") -> Path:
    Image.new(mode, size, color if mode == "RGB" else (*color, 128)).save(path)
    return path


def make_noisy_jpeg_pdf(path: Path, px=(1800, 1800)) -> Path:
    """PDF with one large photo-like JPEG so compression has real work to do."""
    random.seed(1)
    img = Image.frombytes("RGB", px, os.urandom(px[0] * px[1] * 3)).resize(px)
    jpg = path.with_suffix(".src.jpg")
    img.save(jpg, quality=95)
    c = canvas.Canvas(str(path))
    c.drawImage(str(jpg), 20, 20, width=500, height=500)
    c.showPage()
    c.save()
    jpg.unlink()
    return path


def page_texts(pdf: Path) -> list[str]:
    from pypdf import PdfReader
    return [(p.extract_text() or "").strip() for p in PdfReader(str(pdf)).pages]
