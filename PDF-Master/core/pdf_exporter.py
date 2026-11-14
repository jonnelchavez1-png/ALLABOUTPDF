"""Safe export: temp file, validation, no overwrite."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader, PdfWriter

from utils.error_handler import ExportError, ValidationError
from utils.file_handler import atomic_move, unique_path
from utils.logger import get_logger

log = get_logger("exporter")


def _same_file(a: Path, b: Path) -> bool:
    try:
        return a.resolve() == b.resolve() or (a.exists() and b.exists() and os.path.samefile(a, b))
    except OSError:
        return False


def validate_output(path: Path, expected_pages: int | None = None, password: str | None = None) -> int:
    """Re-open a generated PDF and check it. Returns its page count."""
    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted and reader.decrypt(password or "") == 0:
            raise ExportError("The generated file could not be verified.")
        count = len(reader.pages)
    except ExportError:
        raise
    except Exception as exc:  # any parse failure means the output is bad
        raise ExportError("The generated PDF failed validation and was discarded.") from exc
    if expected_pages is not None and count != expected_pages:
        raise ExportError(f"The generated PDF has {count} pages but {expected_pages} were expected.")
    return count


def resolve_destination(dest: str | Path, overwrite: bool = False, protect: Iterable[Path] = ()) -> Path:
    dest = Path(dest)
    if dest.suffix.lower() != ".pdf":
        dest = dest.with_suffix(".pdf")
    if not dest.parent.is_dir():
        raise ValidationError("The output folder does not exist.")
    protected = [Path(p) for p in protect]
    if overwrite and any(_same_file(dest, p) for p in protected):
        raise ExportError("Refusing to overwrite the original file. Choose a different name.")
    if dest.exists() and not overwrite:
        dest = unique_path(dest)
    elif not overwrite and any(_same_file(dest, p) for p in protected):
        dest = unique_path(dest)
    return dest


def export_writer(writer: PdfWriter, dest: str | Path, *, overwrite: bool = False,
                  expected_pages: int | None = None, protect: Iterable[Path] = (),
                  password: str | None = None) -> Path:
    """Write to a temp file next to `dest`, validate it, then move it into place.

    Never overwrites an existing file unless `overwrite=True`, and never the `protect`ed originals.
    On any failure the temp file is removed and ExportError is raised.
    """
    final = resolve_destination(dest, overwrite, protect)
    tmp = final.with_name(f".{final.stem}.{os.getpid()}.tmp")
    try:
        with tmp.open("wb") as fh:
            writer.write(fh)
        validate_output(tmp, expected_pages, password)
        atomic_move(tmp, final)
    except ExportError:
        raise
    except Exception as exc:
        log.exception("export failed")
        raise ExportError() from exc
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
    return final


def write_metadata_copy(src: str | Path, dest: str | Path, metadata: dict, password: str | None = None,
                        overwrite: bool = False) -> Path:
    """Save a copy of `src` with edited metadata (keys: title, author, subject, keywords)."""
    from core.pdf_reader import open_pdf
    reader = open_pdf(src, password)
    writer = PdfWriter(clone_from=reader)
    allowed = {"title": "/Title", "author": "/Author", "subject": "/Subject", "keywords": "/Keywords"}
    writer.add_metadata({allowed[k]: str(v) for k, v in metadata.items() if k in allowed})
    return export_writer(writer, dest, overwrite=overwrite, expected_pages=len(reader.pages),
                         protect=[Path(src)])
