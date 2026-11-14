"""Tests for image -> PDF (and PDF -> image when PyMuPDF is installed)."""
import pytest
from pypdf import PdfReader

from core.pdf_converter import ImageItem, LayoutOptions, images_to_pdf, pdf_to_images, plan_image_pages
from utils.error_handler import ValidationError
from tests.helpers import make_image, make_pdf


def _size(pdf, i=0):
    box = PdfReader(str(pdf)).pages[i].mediabox
    return float(box.width), float(box.height)


def test_mixed_formats_one_page_each(tmp_path):
    items = [ImageItem(make_image(tmp_path / "a.jpg", (400, 300))),
             ImageItem(make_image(tmp_path / "b.png", (300, 500))),
             ImageItem(make_image(tmp_path / "c.bmp", (200, 200))),
             ImageItem(make_image(tmp_path / "d.png", (300, 300), mode="RGBA"))]
    out = images_to_pdf(items, tmp_path / "o.pdf")
    assert len(PdfReader(str(out)).pages) == 4


def test_preview_layout_matches_output_page_size(tmp_path):
    items = [ImageItem(make_image(tmp_path / "land.png", (800, 400))),
             ImageItem(make_image(tmp_path / "port.png", (400, 800)))]
    opts = LayoutOptions("A4", "auto", 10)
    layouts = plan_image_pages(items, opts)
    out = images_to_pdf(items, tmp_path / "o.pdf", opts)
    for i, lay in enumerate(layouts):
        w, h = _size(out, i)
        assert abs(w - lay.page_width) < 1 and abs(h - lay.page_height) < 1
        assert lay.x >= 28 and lay.y >= 28 and lay.x + lay.width <= lay.page_width - 28 + 0.01
        assert abs(lay.width / lay.height - items_ratio(i)) < 0.01   # aspect preserved


def items_ratio(i):
    return 2.0 if i == 0 else 0.5


def test_rotation_changes_planned_page(tmp_path):
    img = make_image(tmp_path / "p.png", (400, 800))
    opts = LayoutOptions("A4", "auto", 10)
    upright = plan_image_pages([ImageItem(img)], opts)[0]
    turned = plan_image_pages([ImageItem(img, 90)], opts)[0]
    assert upright.page_width < upright.page_height and turned.page_width > turned.page_height
    out = images_to_pdf([ImageItem(img, 90)], tmp_path / "o.pdf", opts)
    w, h = _size(out)
    assert w > h


def test_fixed_orientation_and_fit_page(tmp_path):
    img = make_image(tmp_path / "p.png", (400, 800))
    out = images_to_pdf([ImageItem(img)], tmp_path / "l.pdf", LayoutOptions("Letter", "landscape", 5))
    w, h = _size(out)
    assert w > h and abs(w - 792) < 1
    lay = plan_image_pages([ImageItem(img)], LayoutOptions("fit", "auto", 0))[0]
    out2 = images_to_pdf([ImageItem(img)], tmp_path / "f.pdf", LayoutOptions("fit", "auto", 0))
    assert abs(_size(out2)[0] - lay.page_width) < 1 and abs(_size(out2)[1] - lay.page_height) < 1


def test_errors(tmp_path):
    with pytest.raises(ValidationError):
        images_to_pdf([], tmp_path / "o.pdf")
    txt = tmp_path / "x.txt"
    txt.write_text("no")
    with pytest.raises(ValidationError):
        images_to_pdf([ImageItem(txt)], tmp_path / "o.pdf")
    fake = tmp_path / "fake.png"
    fake.write_bytes(b"not an image")
    with pytest.raises(Exception):
        images_to_pdf([ImageItem(fake)], tmp_path / "o.pdf")
    assert not (tmp_path / "o.pdf").exists()
    with pytest.raises(ValidationError):
        images_to_pdf([ImageItem(make_image(tmp_path / "a.png"))], tmp_path / "o.pdf", LayoutOptions("A9"))


def test_pdf_to_images_when_pymupdf_available(tmp_path):
    pytest.importorskip("fitz")
    src = make_pdf(tmp_path / "a.pdf", [(595, 842)] * 2)
    out_dir = tmp_path / "img"
    out_dir.mkdir()
    files = pdf_to_images(src, out_dir, [1], "png", 100)
    assert len(files) == 1 and files[0].suffix == ".png"
