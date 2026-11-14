"""Safe file operations and unique output names."""
from __future__ import annotations

import os
import re
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


def safe_filename(name: str, default: str = "output") -> str:
    """Strip characters that are illegal on Windows and avoid reserved names."""
    cleaned = _INVALID.sub("_", name).strip().strip(".")
    if not cleaned or cleaned.split(".")[0].upper() in _RESERVED:
        return default
    return cleaned[:150]


def unique_path(path: str | Path) -> Path:
    """Return `path`, or 'name (2).ext', 'name (3).ext'... if it already exists."""
    p = Path(path)
    if not p.exists():
        return p
    n = 2
    while True:
        candidate = p.with_name(f"{p.stem} ({n}){p.suffix}")
        if not candidate.exists():
            return candidate
        n += 1


def atomic_move(src: Path, dest: Path) -> None:
    """Move a finished temp file to its final place (same-volume replace when possible)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.replace(src, dest)
    except OSError:
        shutil.move(str(src), str(dest))


@contextmanager
def temp_workdir(prefix: str = "pdfmaster_") -> Iterator[Path]:
    """Temporary folder that is always removed, even if processing fails."""
    d = Path(tempfile.mkdtemp(prefix=prefix))
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)
