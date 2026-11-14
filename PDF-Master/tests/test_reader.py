"""Tests for reader and validation."""
import pytest
from pypdf import PdfWriter

from core.pdf_reader import get_document_info, open_pdf
from utils.error_handler import InvalidPDFError, PasswordRequiredError, ValidationError, WrongPasswordError
from utils.validation import parse_page_ranges, validate_pdf_path
from tests.helpers import make_pdf


def test_document_info_pages_and_orientation(tmp_path):
    pdf = make_pdf(tmp_path / "a.pdf", sizes=[(595, 842), (595, 842), (842, 595)])
    info = get_document_info(pdf)
    assert info.page_count == 3
    assert [p.orientation for p in info.pages] == ["portrait", "portrait", "landscape"]
    assert info.size_bytes == pdf.stat().st_size and not info.encrypted


def test_page_rotation_swaps_displayed_size(tmp_path):
    src = make_pdf(tmp_path / "a.pdf")
    w = PdfWriter(clone_from=str(src))
    w.pages[0].rotate(90)
    out = tmp_path / "r.pdf"
    w.write(str(out))
    info = get_document_info(out)
    assert info.pages[0].orientation == "landscape" and info.pages[0].rotation == 90


def test_rejects_non_pdf_and_corrupt(tmp_path):
    txt = tmp_path / "x.pdf"
    txt.write_text("hello")
    with pytest.raises(InvalidPDFError):
        validate_pdf_path(txt)
    with pytest.raises(ValidationError):
        validate_pdf_path(tmp_path / "missing.pdf")
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"%PDF-1.4\n garbage garbage")
    with pytest.raises(InvalidPDFError):
        open_pdf(bad)
    empty = tmp_path / "empty.pdf"
    empty.write_bytes(b"")
    with pytest.raises(InvalidPDFError):
        validate_pdf_path(empty)


def test_password_flow(tmp_path):
    src = make_pdf(tmp_path / "a.pdf")
    w = PdfWriter(clone_from=str(src))
    w.encrypt("secret", algorithm="AES-256")
    enc = tmp_path / "enc.pdf"
    w.write(str(enc))
    with pytest.raises(PasswordRequiredError):
        open_pdf(enc)
    with pytest.raises(WrongPasswordError):
        open_pdf(enc, "nope")
    assert len(open_pdf(enc, "secret").pages) == 1


def test_parse_page_ranges():
    assert parse_page_ranges("1-3, 5", 10) == [0, 1, 2, 4]
    assert parse_page_ranges("8-", 10) == [7, 8, 9]
    assert parse_page_ranges("3,3,2", 10) == [1, 2]
    for bad in ("", "0", "11", "5-2", "a", "1-x"):
        with pytest.raises(ValidationError):
            parse_page_ranges(bad, 10)
