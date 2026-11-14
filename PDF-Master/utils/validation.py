"""File type, path, and PDF validity checks."""
from __future__ import annotations

from pathlib import Path

from app.config import PDF_EXTENSION, SUPPORTED_IMAGE_EXTENSIONS
from utils.error_handler import InvalidPDFError, ValidationError


def validate_pdf_path(path: str | Path) -> Path:
    """Check existence, type and the %PDF header. Does not parse the whole file."""
    p = Path(path)
    if not p.exists():
        raise ValidationError(f"File not found: {p.name}")
    if not p.is_file():
        raise ValidationError(f"Not a file: {p.name}")
    if p.suffix.lower() != PDF_EXTENSION:
        raise ValidationError(f"{p.name} is not a PDF file.")
    if p.stat().st_size == 0:
        raise InvalidPDFError(f"{p.name} is empty.")
    with p.open("rb") as fh:
        head = fh.read(1024)
    if b"%PDF-" not in head:
        raise InvalidPDFError(f"{p.name} is not a valid PDF or it is damaged.")
    return p


def validate_image_path(path: str | Path) -> Path:
    p = Path(path)
    if not p.is_file():
        raise ValidationError(f"Image not found: {p.name}")
    if p.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        raise ValidationError(f"{p.name}: unsupported image type.")
    return p


def validate_output_dir(path: str | Path) -> Path:
    p = Path(path)
    if not p.is_dir():
        raise ValidationError("The output folder does not exist.")
    return p


def parse_page_ranges(text: str, total_pages: int) -> list[int]:
    """Parse '1-3, 5, 8-' (1-based, inclusive) into sorted unique 0-based indices.

    Raises ValidationError on bad syntax or pages outside 1..total_pages.
    """
    if total_pages < 1:
        raise ValidationError("The document has no pages.")
    result: set[int] = set()
    parts = [t.strip() for t in text.split(",") if t.strip()]
    if not parts:
        raise ValidationError("Enter at least one page or range, for example 1-3, 5.")
    for part in parts:
        try:
            if "-" in part:
                a, b = (s.strip() for s in part.split("-", 1))
                start = int(a) if a else 1
                end = int(b) if b else total_pages
            else:
                start = end = int(part)
        except ValueError:
            raise ValidationError(f"'{part}' is not a valid page or range.") from None
        if start < 1 or end > total_pages:
            raise ValidationError(f"Page range '{part}' is outside 1-{total_pages}.")
        if start > end:
            raise ValidationError(f"Range '{part}' is backwards.")
        result.update(range(start - 1, end))
    return sorted(result)
