"""Rotate pages; applied to the PDF only on export."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from core.pdf_exporter import export_writer
from core.pdf_organizer import PagePlan, build_writer
from core.pdf_reader import open_pdf
from utils.error_handler import ValidationError


def normalize_rotation(degrees: int) -> int:
    """Clockwise rotation folded into 0/90/180/270."""
    if degrees % 90 != 0:
        raise ValidationError("Rotation must be a multiple of 90 degrees.")
    return degrees % 360


def rotated_size(width: float, height: float, rotation: int) -> tuple[float, float]:
    """Displayed size of a page after an extra clockwise rotation (used by live previews)."""
    return (height, width) if normalize_rotation(rotation) in (90, 270) else (width, height)


def rotate_pdf(src: str | Path, dest: str | Path, pages: Iterable[int], degrees: int,
               password: str | None = None, overwrite: bool = False) -> Path:
    """Write a copy of `src` with the given 0-based pages rotated clockwise by `degrees`."""
    reader = open_pdf(src, password)
    plan = PagePlan.from_counts([len(reader.pages)])
    plan.rotate(list(pages), degrees)
    return export_writer(build_writer(plan, [reader]), dest, overwrite=overwrite,
                         expected_pages=plan.page_count, protect=[Path(src)])
