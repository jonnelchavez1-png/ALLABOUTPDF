"""Password protect and authorized unlock.

Nothing here tries to guess, crack or bypass passwords or permissions.
"""
from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.constants import UserAccessPermissions
from pypdf.errors import DependencyError

from core.pdf_exporter import export_writer
from core.pdf_reader import open_pdf
from utils.error_handler import (
    DependencyMissingError,
    PDFMasterError,
    PasswordRequiredError,
    ValidationError,
    WrongPasswordError,
)
from utils.validation import validate_pdf_path

USER_PASSWORD = 1
OWNER_PASSWORD = 2


def protect_pdf(src: str | Path, dest: str | Path, user_password: str, owner_password: str | None = None,
                source_password: str | None = None, overwrite: bool = False) -> Path:
    """Save an AES-256 encrypted copy that needs `user_password` to open."""
    if not user_password:
        raise ValidationError("Enter a password to protect the document.")
    reader = open_pdf(src, source_password)
    if reader.is_encrypted:
        raise ValidationError("This PDF is already protected. Remove its password first.")
    writer = PdfWriter(clone_from=reader)
    try:
        writer.encrypt(user_password=user_password, owner_password=owner_password or user_password,
                       algorithm="AES-256")
    except DependencyError as exc:
        raise DependencyMissingError("Password protection needs the 'cryptography' package.") from exc
    return export_writer(writer, dest, overwrite=overwrite, expected_pages=len(reader.pages),
                         protect=[Path(src)], password=user_password)


def unlock_pdf(src: str | Path, dest: str | Path, password: str, overwrite: bool = False) -> Path:
    """Save an unprotected copy, only if `password` is correct.

    If the file has usage restrictions (e.g. printing disabled) the OWNER password is required;
    the user password alone will not lift restrictions.
    """
    p = validate_pdf_path(src)
    reader = PdfReader(str(p))
    if not reader.is_encrypted:
        raise ValidationError("This PDF is not password-protected.")
    if not password:
        raise PasswordRequiredError()
    try:
        result = int(reader.decrypt(password))
    except DependencyError as exc:
        raise DependencyMissingError("Opening this protected PDF needs the 'cryptography' package.") from exc
    if result == 0:
        raise WrongPasswordError()
    permissions = reader.user_access_permissions
    restricted = permissions is not None and permissions != UserAccessPermissions.all()
    if result == USER_PASSWORD and restricted:
        raise PDFMasterError("This document has usage restrictions. The owner password is needed "
                             "to remove them.")
    writer = PdfWriter(clone_from=reader)
    return export_writer(writer, dest, overwrite=overwrite, expected_pages=len(reader.pages), protect=[p])
