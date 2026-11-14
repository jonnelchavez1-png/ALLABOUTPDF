"""Tests for the pending page plan: rotate, move, delete, duplicate, extract, undo/redo, export."""
import pytest
from pypdf import PdfReader

from core.pdf_organizer import PagePlan, apply_plan
from core.pdf_rotator import rotate_pdf, rotated_size
from utils.error_handler import ValidationError
from tests.helpers import make_pdf, page_texts


def _doc(tmp_path, n=5):
    return make_pdf(tmp_path / "src.pdf", sizes=[(595, 842)] * n)


def test_rotate_only_selected_and_original_untouched(tmp_path):
    src = make_pdf(tmp_path / "src.pdf", sizes=[(595, 842), (595, 842), (842, 595)])
    before = src.read_bytes()
    plan = PagePlan.from_counts([3])
    plan.rotate([1], 90)
    assert [e.rotation for e in plan.entries] == [0, 90, 0]
    out = apply_plan(src, tmp_path / "out.pdf", plan)
    pages = PdfReader(str(out)).pages
    assert [p.rotation for p in pages] == [0, 90, 0]
    assert src.read_bytes() == before                      # original untouched
    assert rotated_size(595, 842, 90) == (842, 595)        # preview geometry matches


def test_rotation_adds_to_existing_rotation_and_reverses(tmp_path):
    plan = PagePlan.from_counts([2])
    plan.rotate([0], 90)
    plan.rotate([0], 270)
    assert plan.entries[0].rotation == 0
    plan.rotate([0], -90)
    assert plan.entries[0].rotation == 270


def test_move_reorders_and_export_matches(tmp_path):
    src = _doc(tmp_path)
    plan = PagePlan.from_counts([5])
    plan.move([0], 3)            # page 1 goes before current page 4 -> 2,3,1,4,5
    assert [e.page_index for e in plan.entries] == [1, 2, 0, 3, 4]
    plan.move([3, 4], 0)         # block to front, order kept
    assert [e.page_index for e in plan.entries] == [3, 4, 1, 2, 0]
    plan.move([0], 5)            # to the very end
    assert [e.page_index for e in plan.entries] == [4, 1, 2, 0, 3]
    out = apply_plan(src, tmp_path / "o.pdf", plan)
    assert [t.split()[-1] for t in page_texts(out)] == ["5", "2", "3", "1", "4"]


def test_delete_updates_count_and_reports_removed(tmp_path):
    src = _doc(tmp_path)
    plan = PagePlan.from_counts([5])
    plan.delete([1, 3])
    assert plan.page_count == 3 and plan.removed_pages() == [1, 3]
    out = apply_plan(src, tmp_path / "o.pdf", plan)
    assert len(PdfReader(str(out)).pages) == 3
    with pytest.raises(ValidationError):
        plan.delete([0, 1, 2])   # cannot delete everything


def test_duplicate_and_extract():
    plan = PagePlan.from_counts([3])
    plan.rotate([1], 90)
    plan.duplicate([1])
    assert [(e.page_index, e.rotation) for e in plan.entries] == [(0, 0), (1, 90), (1, 90), (2, 0)]
    sub = plan.extract([0, 3])
    assert [e.page_index for e in sub.entries] == [0, 2] and plan.page_count == 4


def test_undo_redo_and_reset():
    plan = PagePlan.from_counts([4])
    plan.delete([0])
    plan.rotate([0], 90)
    plan.undo()
    assert plan.entries[0].rotation == 0 and plan.page_count == 3
    plan.undo()
    assert plan.page_count == 4 and not plan.is_modified and not plan.can_undo
    plan.redo()
    assert plan.page_count == 3
    plan.reset()
    assert plan.page_count == 4 and not plan.is_modified
    plan.undo()   # reset itself is undoable
    assert plan.page_count == 3


def test_invalid_selections():
    plan = PagePlan.from_counts([3])
    for call in (lambda: plan.rotate([], 90), lambda: plan.delete([9]), lambda: plan.move([0], 99),
                 lambda: plan.rotate([0], 45)):
        with pytest.raises(ValidationError):
            call()


def test_export_never_overwrites_original_or_existing(tmp_path):
    src = _doc(tmp_path, 2)
    plan = PagePlan.from_counts([2])
    plan.rotate([0], 90)
    out = apply_plan(src, src, plan)             # destination == original
    assert out != src and out.exists() and len(PdfReader(str(src)).pages) == 2
    out2 = apply_plan(src, out, plan)            # destination already exists
    assert out2 not in (src, out)


def test_rotate_pdf_helper(tmp_path):
    src = _doc(tmp_path, 3)
    out = rotate_pdf(src, tmp_path / "r.pdf", [0, 2], 180)
    assert [p.rotation for p in PdfReader(str(out)).pages] == [180, 0, 180]


def test_stale_plan_rejected(tmp_path):
    src = _doc(tmp_path, 3)
    with pytest.raises(ValidationError):
        apply_plan(src, tmp_path / "o.pdf", PagePlan.from_counts([5]))
