"""Tests for password protection / authorized unlock."""
import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.constants import UserAccessPermissions

from core.pdf_reader import open_pdf
from core.pdf_security import protect_pdf, unlock_pdf
from utils.error_handler import PDFMasterError, PasswordRequiredError, ValidationError, WrongPasswordError
from tests.helpers import make_pdf


def test_protect_then_unlock_roundtrip(tmp_path):
    src = make_pdf(tmp_path / "a.pdf", [(595, 842)] * 2)
    enc = protect_pdf(src, tmp_path / "enc.pdf", "pw123")
    assert PdfReader(str(enc)).is_encrypted
    with pytest.raises(PasswordRequiredError):
        open_pdf(enc)
    with pytest.raises(WrongPasswordError):
        unlock_pdf(enc, tmp_path / "x.pdf", "wrong")
    assert not (tmp_path / "x.pdf").exists()
    dec = unlock_pdf(enc, tmp_path / "dec.pdf", "pw123")
    r = PdfReader(str(dec))
    assert not r.is_encrypted and len(r.pages) == 2 and "page 1" in r.pages[0].extract_text()


def test_guards(tmp_path):
    src = make_pdf(tmp_path / "a.pdf")
    with pytest.raises(ValidationError):
        protect_pdf(src, tmp_path / "e.pdf", "")
    with pytest.raises(ValidationError):
        unlock_pdf(src, tmp_path / "d.pdf", "x")                 # not protected
    enc = protect_pdf(src, tmp_path / "enc.pdf", "pw")
    with pytest.raises(PasswordRequiredError):
        protect_pdf(enc, tmp_path / "e2.pdf", "pw2")             # protected source needs its password
    with pytest.raises(ValidationError):
        protect_pdf(enc, tmp_path / "e2.pdf", "pw2", source_password="pw")   # already protected
    with pytest.raises(PasswordRequiredError):
        unlock_pdf(enc, tmp_path / "d.pdf", "")


def test_user_password_cannot_lift_restrictions(tmp_path):
    src = make_pdf(tmp_path / "a.pdf")
    w = PdfWriter(clone_from=str(src))
    w.encrypt("user", owner_password="owner", permissions_flag=UserAccessPermissions.PRINT, algorithm="AES-256")
    restricted = tmp_path / "r.pdf"
    w.write(str(restricted))
    with pytest.raises(PDFMasterError):
        unlock_pdf(restricted, tmp_path / "d1.pdf", "user")
    assert not (tmp_path / "d1.pdf").exists()
    out = unlock_pdf(restricted, tmp_path / "d2.pdf", "owner")
    assert not PdfReader(str(out)).is_encrypted
