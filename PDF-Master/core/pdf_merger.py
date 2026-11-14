"""Merge multiple PDFs in a given order."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from core.pdf_exporter import export_writer
from core.pdf_organizer import PagePlan, build_writer
from core.pdf_reader import open_pdf
from utils.error_handler import ValidationError


@dataclass(frozen=True)
class MergeSource:
    path: Path
    password: str | None = None


def build_merge_plan(sources: Sequence[MergeSource]) -> PagePlan:
    """The exact page sequence the merged document will have (drives the merge preview)."""
    if len(sources) < 2:
        raise ValidationError("Add at least two PDFs to merge.")
    counts = [len(open_pdf(s.path, s.password).pages) for s in sources]
    return PagePlan.from_counts(counts)


def expected_page_count(sources: Sequence[MergeSource]) -> int:
    return build_merge_plan(sources).page_count


def merge_pdfs(sources: Sequence[MergeSource], dest: str | Path, overwrite: bool = False) -> Path:
    readers = [open_pdf(s.path, s.password) for s in sources]
    if len(readers) < 2:
        raise ValidationError("Add at least two PDFs to merge.")
    plan = PagePlan.from_counts([len(r.pages) for r in readers])
    return export_writer(build_writer(plan, readers), dest, overwrite=overwrite,
                         expected_pages=plan.page_count, protect=[s.path for s in sources])
