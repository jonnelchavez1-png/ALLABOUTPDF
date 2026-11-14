"""Open PDFs, read metadata and page info, handle passwords."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import DependencyError, PdfReadError, PyPdfError

from utils.error_handler import (
    DependencyMissingError,
    InvalidPDFError,
    PasswordRequiredError,
    WrongPasswordError,
)
from utils.validation import validate_pdf_path

_META_KEYS = ("title", "author", "subject", "keywords", "creator", "producer")


@dataclass(frozen=True)
class PageInfo:
    index: int          # 0-based
    width: float        # points, as displayed (rotation applied)
    height: float
    rotation: int       # the page's own /Rotate value (0/90/180/270)

    @property
    def orientation(self) -> str:
        return "landscape" if self.width > self.height else "portrait"


@dataclass
class DocumentInfo:
    path: Path
    page_count: int
    size_bytes: int
    encrypted: bool
    metadata: dict = field(default_factory=dict)
    pages: list[PageInfo] = field(default_factory=list)


def is_encrypted(path: str | Path) -> bool:
    p = validate_pdf_path(path)
    try:
        return bool(PdfReader(str(p)).is_encrypted)
    except (PdfReadError, PyPdfError) as exc:
        raise InvalidPDFError() from exc


def open_pdf(path: str | Path, password: str | None = None) -> PdfReader:
    """Open (and if needed decrypt) a PDF. Never tries to bypass protection."""
    p = validate_pdf_path(path)
    try:
        reader = PdfReader(str(p))
        if reader.is_encrypted:
            if reader.decrypt(password or "") == 0:   # PasswordType.NOT_DECRYPTED
                raise WrongPasswordError() if password else PasswordRequiredError()
        len(reader.pages)  # forces the page tree to parse; surfaces damaged files here
    except DependencyError as exc:
        raise DependencyMissingError("Opening this protected PDF needs the 'cryptography' package.") from exc
    except (PdfReadError, PyPdfError, ValueError, KeyError, AttributeError, RecursionError) as exc:
        raise InvalidPDFError(f"{p.name} is not a valid PDF or it is damaged.") from exc
    return reader


def read_metadata(reader: PdfReader) -> dict:
    meta = reader.metadata
    out = {}
    for key in _META_KEYS:
        value = getattr(meta, key, None) if meta else None
        out[key] = str(value) if value else ""
    return out


def page_info(reader: PdfReader, index: int) -> PageInfo:
    page = reader.pages[index]
    w, h = float(page.mediabox.width), float(page.mediabox.height)
    rot = int(page.rotation or 0) % 360
    if rot in (90, 270):
        w, h = h, w
    return PageInfo(index=index, width=round(w, 2), height=round(h, 2), rotation=rot)


def get_document_info(path: str | Path, password: str | None = None) -> DocumentInfo:
    p = validate_pdf_path(path)
    reader = open_pdf(p, password)
    count = len(reader.pages)
    return DocumentInfo(
        path=p,
        page_count=count,
        size_bytes=p.stat().st_size,
        encrypted=bool(reader.is_encrypted),
        metadata=read_metadata(reader),
        pages=[page_info(reader, i) for i in range(count)],
    )


def render_page_png(path: str | Path, index: int, zoom: float = 1.0, rotation: int = 0,
                    password: str | None = None) -> bytes:
    """Render one page to PNG bytes with PyMuPDF (lazy import). NOT testable without PyMuPDF.

    `rotation` is an extra clockwise rotation (0/90/180/270) for live previews: the PDF is untouched.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise DependencyMissingError("PyMuPDF is required to render page previews.") from exc
    doc = fitz.open(str(validate_pdf_path(path)))
    try:
        if doc.needs_pass and not doc.authenticate(password or ""):
            raise WrongPasswordError() if password else PasswordRequiredError()
        page = doc[index]
        matrix = fitz.Matrix(zoom, zoom).prerotate(rotation % 360)
        return page.get_pixmap(matrix=matrix, alpha=False).tobytes("png")
    finally:
        doc.close()
