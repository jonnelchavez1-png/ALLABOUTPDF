"""Tests for splitter."""
import pytest

from core.pdf_splitter import plan_every_page, plan_extract, plan_interval, plan_ranges, split_pdf
from utils.error_handler import ValidationError
from tests.helpers import make_pdf, page_texts


def test_plans():
    assert [o.pages for o in plan_ranges("1-3, 5, 8-", 9)] == [(0, 1, 2), (4,), (7, 8)]
    assert [o.label for o in plan_ranges("1-3, 5", 9)] == ["1-3", "5"]
    assert [o.pages for o in plan_interval(7, 3)] == [(0, 1, 2), (3, 4, 5), (6,)]
    assert len(plan_every_page(4)) == 4
    assert plan_extract([4, 1, 4], 6)[0].pages == (4, 1)
    for bad in (lambda: plan_interval(5, 0), lambda: plan_extract([], 5), lambda: plan_extract([9], 5),
                lambda: plan_ranges("9", 5)):
        with pytest.raises(ValidationError):
            bad()


def test_split_outputs_match_plan(tmp_path):
    src = make_pdf(tmp_path / "doc.pdf", [(595, 842)] * 6)
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    files = split_pdf(src, plan_ranges("1-2, 4, 6", 6), out_dir)
    assert len(files) == 3
    assert [[t.split()[-1] for t in page_texts(f)] for f in files] == [["1", "2"], ["4"], ["6"]]


def test_split_every_page_and_no_overwrite(tmp_path):
    src = make_pdf(tmp_path / "doc.pdf", [(595, 842)] * 3)
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    first = split_pdf(src, plan_every_page(3), out_dir)
    second = split_pdf(src, plan_every_page(3), out_dir)
    assert len(set(first + second)) == 6                 # second run got unique names


def test_split_missing_folder(tmp_path):
    src = make_pdf(tmp_path / "doc.pdf")
    with pytest.raises(ValidationError):
        split_pdf(src, plan_every_page(1), tmp_path / "nope")
