"""Tests for compressor: only measured sizes are ever reported."""
import pytest
from pypdf import PdfReader

from core.pdf_compressor import compress_pdf
from utils.error_handler import ValidationError
from tests.helpers import make_noisy_jpeg_pdf, make_pdf


def test_image_compression_reports_real_sizes(tmp_path):
    src = make_noisy_jpeg_pdf(tmp_path / "big.pdf")
    original = src.read_bytes()
    res = compress_pdf(src, tmp_path / "small.pdf", "strong")
    assert res.output_path.exists()
    assert res.original_size == len(original)
    assert res.output_size == res.output_path.stat().st_size      # measured, not estimated
    assert res.smaller and res.saved_bytes > 0 and res.images_recompressed >= 1
    assert res.saved_percent == round(100 * res.saved_bytes / res.original_size, 1)
    assert len(PdfReader(str(res.output_path)).pages) == 1
    assert src.read_bytes() == original                           # original untouched


def test_basic_is_lossless_text_survives(tmp_path):
    src = make_pdf(tmp_path / "t.pdf", [(595, 842)] * 3)
    res = compress_pdf(src, tmp_path / "t2.pdf", "basic")
    assert res.images_recompressed == 0
    assert "page 2" in PdfReader(str(res.output_path)).pages[1].extract_text()


def test_growth_is_reported_honestly(tmp_path):
    src = make_pdf(tmp_path / "t.pdf")
    res = compress_pdf(src, tmp_path / "t2.pdf", "basic")
    assert res.smaller == (res.output_size < res.original_size)   # never claims a saving that isn't there


def test_bad_settings(tmp_path):
    src = make_pdf(tmp_path / "t.pdf")
    with pytest.raises(ValidationError):
        compress_pdf(src, tmp_path / "o.pdf", "ultra")
    with pytest.raises(ValidationError):
        compress_pdf(src, tmp_path / "o.pdf", "balanced", jpeg_quality=0)
