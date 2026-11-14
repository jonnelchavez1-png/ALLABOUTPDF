"""Optimize and compress; report actual size results only."""
from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfWriter

from core.pdf_exporter import export_writer
from core.pdf_reader import open_pdf
from utils.error_handler import ValidationError
from utils.logger import get_logger

log = get_logger("compressor")

# name -> (jpeg quality or None for lossless only, max image side in pixels or None)
PRESETS = {
    "basic": (None, None),      # lossless: compress content streams + merge duplicate objects
    "balanced": (75, 2000),     # recompress JPEG-able images, downscale very large ones
    "strong": (55, 1400),       # smaller file, visibly softer images
}

PRESET_HELP = {
    "basic": "Lossless. Text, vector art and images are unchanged. Usually a small saving.",
    "balanced": "Recompresses photos at good quality and shrinks oversized images. Text stays sharp.",
    "strong": "Smallest file. Photos and scans get softer; fine detail may be lost.",
}


@dataclass(frozen=True)
class CompressionResult:
    output_path: Path
    original_size: int      # bytes, measured
    output_size: int        # bytes, measured
    images_recompressed: int
    images_skipped: int

    @property
    def saved_bytes(self) -> int:
        return self.original_size - self.output_size

    @property
    def smaller(self) -> bool:
        return self.output_size < self.original_size

    @property
    def saved_percent(self) -> float:
        """Real reduction vs the original (negative if the file grew)."""
        return round(100.0 * self.saved_bytes / self.original_size, 1) if self.original_size else 0.0


def _recompress_images(writer: PdfWriter, quality: int, max_side: int | None) -> tuple[int, int]:
    done = skipped = 0
    for page in writer.pages:
        try:
            images = list(page.images)
        except Exception:
            log.warning("could not list images on a page")
            continue
        for img in images:
            try:
                pil = img.image
                if pil.mode not in ("RGB", "L"):   # alpha/palette/CMYK: leave untouched
                    skipped += 1
                    continue
                if max_side and max(pil.size) > max_side:
                    scale = max_side / max(pil.size)
                    pil = pil.resize((max(1, round(pil.width * scale)), max(1, round(pil.height * scale))))
                img.replace(pil, quality=quality)
                done += 1
            except Exception:
                skipped += 1
                log.warning("image skipped during compression", exc_info=True)
    return done, skipped


def compress_pdf(src: str | Path, dest: str | Path, preset: str = "balanced", password: str | None = None,
                 jpeg_quality: int | None = None, max_image_side: int | None = None,
                 overwrite: bool = False) -> CompressionResult:
    """Write a compressed copy and report the MEASURED sizes. The original is never modified.

    Custom `jpeg_quality` (1-95) / `max_image_side` override the preset.
    """
    if preset not in PRESETS:
        raise ValidationError("Unknown compression level.")
    src = Path(src)
    reader = open_pdf(src, password)
    quality, side = PRESETS[preset]
    quality = jpeg_quality if jpeg_quality is not None else quality
    side = max_image_side if max_image_side is not None else side
    if quality is not None and not 1 <= quality <= 95:
        raise ValidationError("Image quality must be between 1 and 95.")

    writer = PdfWriter(clone_from=reader)
    done = skipped = 0
    if quality is not None:
        done, skipped = _recompress_images(writer, quality, side)
    for page in writer.pages:
        page.compress_content_streams()
    try:                                   # pypdf 7 renamed the keyword
        writer.compress_identical_objects(remove_duplicates=True, remove_orphans=True)
    except TypeError:
        writer.compress_identical_objects(remove_identicals=True, remove_orphans=True)

    out = export_writer(writer, dest, overwrite=overwrite, expected_pages=len(reader.pages), protect=[src])
    return CompressionResult(out, src.stat().st_size, out.stat().st_size, done, skipped)
