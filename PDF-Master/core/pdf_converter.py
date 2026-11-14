"""Images to PDF and PDF to images."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import img2pdf
from PIL import Image, ImageOps

from core.pdf_exporter import export_writer
from core.pdf_rotator import normalize_rotation
from utils.error_handler import DependencyMissingError, PasswordRequiredError, ValidationError, WrongPasswordError
from utils.file_handler import safe_filename, temp_workdir, unique_path
from utils.validation import validate_image_path, validate_pdf_path

# page sizes in millimetres (portrait)
PAGE_SIZES_MM = {"A4": (210.0, 297.0), "A3": (297.0, 420.0), "A5": (148.0, 210.0),
                 "Letter": (215.9, 279.4), "Legal": (215.9, 355.6)}
DEFAULT_DPI = 96.0   # img2pdf's assumption for images without DPI metadata


@dataclass(frozen=True)
class ImageItem:
    path: Path
    rotation: int = 0          # extra clockwise rotation: 0/90/180/270


@dataclass(frozen=True)
class LayoutOptions:
    page_size: str = "A4"      # a key of PAGE_SIZES_MM, or "fit" (page = image size)
    orientation: str = "auto"  # "auto" | "portrait" | "landscape"
    margin_mm: float = 10.0


@dataclass(frozen=True)
class PageLayout:
    """Where one image lands on its page, in points with origin at the top-left (drives the preview)."""
    page_width: float
    page_height: float
    x: float
    y: float
    width: float
    height: float


def _pt(mm: float) -> float:
    return mm * 72.0 / 25.4


def _validate_options(o: LayoutOptions) -> None:
    if o.page_size != "fit" and o.page_size not in PAGE_SIZES_MM:
        raise ValidationError("Unknown page size.")
    if o.orientation not in ("auto", "portrait", "landscape"):
        raise ValidationError("Unknown page orientation.")
    if not 0 <= o.margin_mm <= 50:
        raise ValidationError("Margin must be between 0 and 50 mm.")


def image_pixel_size(item: ImageItem) -> tuple[int, int, float]:
    """(width, height, dpi) AFTER EXIF orientation and the item's rotation."""
    with Image.open(validate_image_path(item.path)) as im:
        im = ImageOps.exif_transpose(im)
        w, h = im.size
        dpi = float((im.info.get("dpi") or (DEFAULT_DPI,))[0]) or DEFAULT_DPI
    if normalize_rotation(item.rotation) in (90, 270):
        w, h = h, w
    return w, h, (dpi if dpi >= 1 else DEFAULT_DPI)


def compute_layout(img_w: int, img_h: int, dpi: float, options: LayoutOptions) -> PageLayout:
    """Page and image rectangle for one image. Aspect ratio is always preserved."""
    _validate_options(options)
    margin = _pt(options.margin_mm)
    nat_w, nat_h = img_w * 72.0 / dpi, img_h * 72.0 / dpi
    if options.page_size == "fit":
        return PageLayout(nat_w + 2 * margin, nat_h + 2 * margin, margin, margin, nat_w, nat_h)
    pw, ph = (_pt(v) for v in PAGE_SIZES_MM[options.page_size])
    landscape = (img_w > img_h) if options.orientation == "auto" else options.orientation == "landscape"
    if landscape:
        pw, ph = ph, pw
    box_w, box_h = max(pw - 2 * margin, 1.0), max(ph - 2 * margin, 1.0)
    scale = min(box_w / nat_w, box_h / nat_h)
    w, h = nat_w * scale, nat_h * scale
    return PageLayout(pw, ph, (pw - w) / 2, (ph - h) / 2, w, h)


def plan_image_pages(items: Sequence[ImageItem], options: LayoutOptions) -> list[PageLayout]:
    """Expected pages, in order, for the Image-to-PDF preview."""
    if not items:
        raise ValidationError("Add at least one image.")
    return [compute_layout(*image_pixel_size(i)[:2], image_pixel_size(i)[2], options) for i in items]


def _prepare(item: ImageItem, workdir: Path, n: int) -> str:
    """Return a path img2pdf can embed. The original is passed through untouched whenever possible."""
    rot = normalize_rotation(item.rotation)
    src = validate_image_path(item.path)
    with Image.open(src) as im:
        exif_fix = im.getexif().get(0x0112, 1) not in (0, 1)
        simple = (rot == 0 and not exif_fix)
        if simple and src.suffix.lower() in (".jpg", ".jpeg", ".png") and im.mode in ("RGB", "L"):
            return str(src)
        if simple and src.suffix.lower() in (".tif", ".tiff"):
            return str(src)
        im = ImageOps.exif_transpose(im)
        if rot:
            im = im.rotate(-rot, expand=True)       # PIL rotates counter-clockwise
        if im.mode in ("RGBA", "LA", "P"):
            rgba = im.convert("RGBA")
            bg = Image.new("RGB", rgba.size, (255, 255, 255))
            bg.paste(rgba, mask=rgba.split()[-1])
            im = bg
        elif im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        out = workdir / f"img_{n:04d}.png"
        im.save(out, "PNG")
    return str(out)


def images_to_pdf(items: Sequence[ImageItem], dest: str | Path, options: LayoutOptions = LayoutOptions(),
                  overwrite: bool = False) -> Path:
    """Build one PDF with one page per image (multi-frame TIFFs add several pages)."""
    if not items:
        raise ValidationError("Add at least one image.")
    _validate_options(options)
    margin = _pt(options.margin_mm)
    with temp_workdir() as work:
        paths = [_prepare(it, work, n) for n, it in enumerate(items)]
        if options.page_size == "fit":
            layout = img2pdf.get_layout_fun(None, None, (margin, margin), img2pdf.FitMode.into, True)
        else:
            pw, ph = (_pt(v) for v in PAGE_SIZES_MM[options.page_size])
            if options.orientation == "landscape":
                pw, ph = ph, pw
            layout = img2pdf.get_layout_fun((pw, ph), None, (margin, margin), img2pdf.FitMode.into,
                                            options.orientation == "auto")
        try:
            data = img2pdf.convert(paths, layout_fun=layout)
        except Exception as exc:
            raise ValidationError("One of the images could not be converted to PDF.") from exc
        # Route through the shared safe exporter (temp file, validation, no overwrite).
        from pypdf import PdfReader, PdfWriter
        import io
        reader = PdfReader(io.BytesIO(data))
        writer = PdfWriter(clone_from=reader)
        return export_writer(writer, dest, overwrite=overwrite, expected_pages=len(reader.pages))


def pdf_to_images(src: str | Path, out_dir: str | Path, pages: Sequence[int] | None = None, fmt: str = "png",
                  dpi: int = 150, jpeg_quality: int = 90, password: str | None = None) -> list[Path]:
    """Export pages (0-based, all by default) as PNG/JPEG using PyMuPDF.

    NOTE: written against the PyMuPDF API but NOT run in the development sandbox (PyMuPDF unavailable).
    """
    fmt = fmt.lower().replace("jpg", "jpeg")
    if fmt not in ("png", "jpeg"):
        raise ValidationError("Choose PNG or JPEG.")
    if not 36 <= dpi <= 600:
        raise ValidationError("Resolution must be between 36 and 600 DPI.")
    out_dir = Path(out_dir)
    if not out_dir.is_dir():
        raise ValidationError("The output folder does not exist.")
    try:
        import fitz
    except ImportError as exc:
        raise DependencyMissingError("PyMuPDF is required to export pages as images.") from exc
    src = validate_pdf_path(src)
    doc = fitz.open(str(src))
    try:
        if doc.needs_pass and not doc.authenticate(password or ""):
            raise WrongPasswordError() if password else PasswordRequiredError()
        chosen = list(range(doc.page_count)) if pages is None else list(pages)
        if not chosen or any(not 0 <= p < doc.page_count for p in chosen):
            raise ValidationError("Selected page does not exist.")
        zoom = dpi / 72.0
        ext = "jpg" if fmt == "jpeg" else "png"
        results = []
        for p in chosen:
            pix = doc[p].get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            data = pix.tobytes("jpeg", jpg_quality=jpeg_quality) if fmt == "jpeg" else pix.tobytes("png")
            target = unique_path(out_dir / f"{safe_filename(src.stem)}_page{p + 1}.{ext}")
            target.write_bytes(data)
            results.append(target)
        return results
    finally:
        doc.close()
