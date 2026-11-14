"""Tests for merger."""
import pytest
from pypdf import PdfReader

from core.pdf_merger import MergeSource, build_merge_plan, expected_page_count, merge_pdfs
from utils.error_handler import InvalidPDFError, ValidationError
from tests.helpers import make_pdf, page_texts


def test_merge_order_and_count(tmp_path):
    a = make_pdf(tmp_path / "a.pdf", [(595, 842)] * 2, "A")
    b = make_pdf(tmp_path / "b.pdf", [(842, 595)], "B")
    c = make_pdf(tmp_path / "c.pdf", [(595, 842)] * 3, "C")
    seq = [MergeSource(c), MergeSource(a), MergeSource(b)]
    assert expected_page_count(seq) == 6
    plan = build_merge_plan(seq)
    assert [(e.source, e.page_index) for e in plan.entries][:4] == [(0, 0), (0, 1), (0, 2), (1, 0)]
    out = merge_pdfs(seq, tmp_path / "m.pdf")
    texts = page_texts(out)
    assert [t.split()[0] for t in texts] == ["C", "C", "C", "A", "A", "B"]
    assert len(PdfReader(str(out)).pages) == 6
    assert PdfReader(str(out)).pages[5].mediabox.width == 842   # landscape page preserved


def test_merge_needs_two_and_rejects_bad_file(tmp_path):
    a = make_pdf(tmp_path / "a.pdf")
    with pytest.raises(ValidationError):
        merge_pdfs([MergeSource(a)], tmp_path / "m.pdf")
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"%PDF-1.4 nonsense")
    with pytest.raises(InvalidPDFError):
        merge_pdfs([MergeSource(a), MergeSource(bad)], tmp_path / "m.pdf")
    assert not (tmp_path / "m.pdf").exists()                      # nothing half-written


def test_merge_does_not_modify_sources_or_leave_temp_files(tmp_path):
    a = make_pdf(tmp_path / "a.pdf", label="A")
    b = make_pdf(tmp_path / "b.pdf", label="B")
    before = (a.read_bytes(), b.read_bytes())
    merge_pdfs([MergeSource(a), MergeSource(b)], tmp_path / "m.pdf")
    assert (a.read_bytes(), b.read_bytes()) == before
    assert not [p for p in tmp_path.iterdir() if p.name.endswith(".tmp")]
