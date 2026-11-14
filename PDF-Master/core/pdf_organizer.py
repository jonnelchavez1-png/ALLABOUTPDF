"""Reorder, delete, duplicate, extract pages from a pending page plan."""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable, Sequence

from pypdf import PdfReader, PdfWriter

from core.pdf_exporter import export_writer
from core.pdf_reader import open_pdf
from utils.error_handler import ValidationError


@dataclass(frozen=True)
class PlanEntry:
    """One output page: which source page it comes from and the EXTRA rotation applied to it."""
    page_index: int
    rotation: int = 0
    source: int = 0


class PagePlan:
    """Pending document state. The source files are never touched; the UI previews this plan
    and the exporter turns exactly this plan into a PDF. Supports undo/redo."""

    def __init__(self, entries: Sequence[PlanEntry], original_count: int | None = None) -> None:
        self._entries: list[PlanEntry] = list(entries)
        self._original = [e for e in self._entries]
        self.original_count = original_count if original_count is not None else len(self._entries)
        self._undo: list[list[PlanEntry]] = []
        self._redo: list[list[PlanEntry]] = []

    # ---- construction -------------------------------------------------
    @classmethod
    def from_counts(cls, page_counts: Sequence[int]) -> "PagePlan":
        """One entry per page of each source, in order (single doc or a merge sequence)."""
        entries = [PlanEntry(i, 0, s) for s, n in enumerate(page_counts) for i in range(n)]
        return cls(entries, original_count=sum(page_counts))

    # ---- reading ------------------------------------------------------
    @property
    def entries(self) -> list[PlanEntry]:
        return list(self._entries)

    @property
    def page_count(self) -> int:
        return len(self._entries)

    @property
    def is_modified(self) -> bool:
        return self._entries != self._original

    def removed_pages(self, source: int = 0) -> list[int]:
        """0-based source pages that will NOT appear in the output (for the delete preview)."""
        kept = {e.page_index for e in self._entries if e.source == source}
        all_pages = {e.page_index for e in self._original if e.source == source}
        return sorted(all_pages - kept)

    # ---- editing ------------------------------------------------------
    def _check(self, positions: Iterable[int]) -> list[int]:
        pos = sorted(set(positions))
        if not pos:
            raise ValidationError("Select at least one page first.")
        if pos[0] < 0 or pos[-1] >= len(self._entries):
            raise ValidationError("Selected page does not exist.")
        return pos

    def _commit(self, new_entries: list[PlanEntry]) -> None:
        self._undo.append(self._entries)
        self._entries = new_entries
        self._redo.clear()

    def rotate(self, positions: Iterable[int], degrees: int) -> None:
        from core.pdf_rotator import normalize_rotation
        delta = normalize_rotation(degrees)
        pos = set(self._check(positions))
        self._commit([replace(e, rotation=(e.rotation + delta) % 360) if i in pos else e
                      for i, e in enumerate(self._entries)])

    def delete(self, positions: Iterable[int]) -> None:
        pos = set(self._check(positions))
        if len(pos) >= len(self._entries):
            raise ValidationError("You cannot delete every page of the document.")
        self._commit([e for i, e in enumerate(self._entries) if i not in pos])

    def duplicate(self, positions: Iterable[int]) -> None:
        """Insert a copy of each selected page directly after itself (rotation is copied)."""
        pos = set(self._check(positions))
        out: list[PlanEntry] = []
        for i, e in enumerate(self._entries):
            out.append(e)
            if i in pos:
                out.append(e)
        self._commit(out)

    def move(self, positions: Iterable[int], to: int) -> None:
        """Move the selected pages, keeping their relative order, so they sit before the page
        currently at position `to` (use page_count to move to the end)."""
        pos = self._check(positions)
        if not 0 <= to <= len(self._entries):
            raise ValidationError("Invalid drop position.")
        block = [self._entries[i] for i in pos]
        rest = [e for i, e in enumerate(self._entries) if i not in set(pos)]
        insert_at = to - sum(1 for i in pos if i < to)
        self._commit(rest[:insert_at] + block + rest[insert_at:])

    def extract(self, positions: Iterable[int]) -> "PagePlan":
        """A NEW plan holding just the selected pages (this plan is unchanged)."""
        pos = self._check(positions)
        return PagePlan([self._entries[i] for i in pos], original_count=self.original_count)

    def reset(self) -> None:
        if self.is_modified:
            self._commit(list(self._original))

    # ---- undo / redo --------------------------------------------------
    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def undo(self) -> None:
        if self._undo:
            self._redo.append(self._entries)
            self._entries = self._undo.pop()

    def redo(self) -> None:
        if self._redo:
            self._undo.append(self._entries)
            self._entries = self._redo.pop()


def build_writer(plan: PagePlan, readers: Sequence[PdfReader]) -> PdfWriter:
    """Turn a plan into a PdfWriter. Source readers are only read, never modified."""
    writer = PdfWriter()
    for e in plan.entries:
        if e.source >= len(readers) or e.page_index >= len(readers[e.source].pages):
            raise ValidationError("The page plan refers to a page that does not exist.")
        page = writer.add_page(readers[e.source].pages[e.page_index])
        if e.rotation:
            page.rotate(e.rotation)
    return writer


def apply_plan(src: str | Path, dest: str | Path, plan: PagePlan, password: str | None = None,
               overwrite: bool = False) -> Path:
    """Export the pending arrangement of a single document."""
    reader = open_pdf(src, password)
    if plan.original_count != len(reader.pages):
        raise ValidationError("The document changed since it was loaded. Re-open it and try again.")
    return export_writer(build_writer(plan, [reader]), dest, overwrite=overwrite,
                         expected_pages=plan.page_count, protect=[Path(src)])
