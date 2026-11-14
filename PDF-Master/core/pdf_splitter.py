"""Split by ranges, intervals, or every page."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from pypdf import PdfWriter

from core.pdf_exporter import export_writer
from core.pdf_reader import open_pdf
from utils.error_handler import ValidationError
from utils.file_handler import safe_filename
from utils.validation import parse_page_ranges


@dataclass(frozen=True)
class SplitOutput:
    """One planned output document: 0-based source pages, in order."""
    pages: tuple[int, ...]

    @property
    def label(self) -> str:
        """Human label such as '1-3' or '5' (1-based)."""
        p = self.pages
        if len(p) == 1:
            return str(p[0] + 1)
        if list(p) == list(range(p[0], p[0] + len(p))):
            return f"{p[0] + 1}-{p[-1] + 1}"
        return "_".join(str(i + 1) for i in p)


def plan_ranges(text: str, total_pages: int) -> list[SplitOutput]:
    """'1-3, 5, 8-' -> three outputs: pages 1-3, page 5, pages 8-end."""
    outputs = []
    for part in (t.strip() for t in text.split(",") if t.strip()):
        outputs.append(SplitOutput(tuple(parse_page_ranges(part, total_pages))))
    if not outputs:
        raise ValidationError("Enter at least one page or range, for example 1-3, 5.")
    return outputs


def plan_every_page(total_pages: int) -> list[SplitOutput]:
    return [SplitOutput((i,)) for i in range(total_pages)]


def plan_interval(total_pages: int, every: int) -> list[SplitOutput]:
    """Chunks of `every` pages; the last chunk may be shorter."""
    if every < 1:
        raise ValidationError("The interval must be at least 1 page.")
    return [SplitOutput(tuple(range(s, min(s + every, total_pages)))) for s in range(0, total_pages, every)]


def plan_extract(indices: Sequence[int], total_pages: int) -> list[SplitOutput]:
    """One output holding the selected pages (selection order kept, duplicates removed)."""
    seen: list[int] = []
    for i in indices:
        if not 0 <= i < total_pages:
            raise ValidationError("Selected page does not exist.")
        if i not in seen:
            seen.append(i)
    if not seen:
        raise ValidationError("Select at least one page first.")
    return [SplitOutput(tuple(seen))]


def split_pdf(src: str | Path, outputs: Sequence[SplitOutput], out_dir: str | Path,
              stem: str | None = None, password: str | None = None, overwrite: bool = False) -> list[Path]:
    """Create every planned output. If one fails, files already written are kept and the error raised."""
    src = Path(src)
    reader = open_pdf(src, password)
    total = len(reader.pages)
    out_dir = Path(out_dir)
    if not out_dir.is_dir():
        raise ValidationError("The output folder does not exist.")
    if not outputs:
        raise ValidationError("Nothing to split.")
    for o in outputs:
        if any(not 0 <= p < total for p in o.pages):
            raise ValidationError("The split plan refers to a page that does not exist.")
    base = safe_filename(stem or src.stem)
    results = []
    for n, o in enumerate(outputs, start=1):
        writer = PdfWriter()
        for p in o.pages:
            writer.add_page(reader.pages[p])
        name = f"{base}_part{n}_p{o.label}.pdf"
        results.append(export_writer(writer, out_dir / name, overwrite=overwrite,
                                     expected_pages=len(o.pages), protect=[src]))
    return results
