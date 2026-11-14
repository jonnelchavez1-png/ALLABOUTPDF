"""Tests for watermark and page numbers."""
import pytest
from pypdf import PdfReader, PdfWriter

from core.pdf_watermark import add_page_numbers, add_text_watermark
from utils.error_handler import ValidationError
from tests.helpers import make_pdf


def _texts(pdf):
    return [p.extract_text() for p in PdfReader(str(pdf)).pages]


def test_watermark_on_selected_pages_only(tmp_path):
    src = make_pdf(tmp_path / "a.pdf", [(595, 842)] * 3)
    out = add_text_watermark(src, tmp_path / "w.pdf", "CONFIDENTIAL", pages=[0, 2])
    t = _texts(out)
    assert "CONFIDENTIAL" in t[0] and "CONFIDENTIAL" not in t[1] and "CONFIDENTIAL" in t[2]
    assert "page 1" in t[0]                       # original content kept


def test_page_numbers_format_and_start(tmp_path):
    src = make_pdf(tmp_path / "a.pdf", [(595, 842)] * 3)
    out = add_page_numbers(src, tmp_path / "n.pdf", fmt="Page {n} of {total}", start_number=1)
    t = _texts(out)
    assert "Page 1 of 3" in t[0] and "Page 3 of 3" in t[2]


def test_rotated_pages_still_stamped(tmp_path):
    for angle in (90, 180, 270):
        src = make_pdf(tmp_path / f"a{angle}.pdf", [(595, 842)])
        w = PdfWriter(clone_from=str(src))
        w.pages[0].rotate(angle)
        rot = tmp_path / f"rot{angle}.pdf"
        w.write(str(rot))
        out = add_text_watermark(rot, tmp_path / f"w{angle}.pdf", "DRAFT")
        assert "DRAFT" in _texts(out)[0]
        # NOTE: only presence is asserted. Upright placement on rotated pages needs a visual check.


def test_validation(tmp_path):
    src = make_pdf(tmp_path / "a.pdf")
    for call in (lambda: add_text_watermark(src, tmp_path / "w.pdf", "  "),
                 lambda: add_text_watermark(src, tmp_path / "w.pdf", "x", opacity=0),
                 lambda: add_text_watermark(src, tmp_path / "w.pdf", "x", pages=[5]),
                 lambda: add_page_numbers(src, tmp_path / "n.pdf", position="middle"),
                 lambda: add_page_numbers(src, tmp_path / "n.pdf", fmt="no number")):
        with pytest.raises(ValidationError):
            call()
