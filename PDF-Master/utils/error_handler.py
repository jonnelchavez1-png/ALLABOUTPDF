"""User-friendly error mapping."""
from __future__ import annotations


class PDFMasterError(Exception):
    """Base class. `user_message` is safe to show in the UI."""

    user_message = "Something went wrong while processing the document."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.user_message)
        if message:
            self.user_message = message


class ValidationError(PDFMasterError):
    user_message = "The selected file or setting is not valid."


class InvalidPDFError(PDFMasterError):
    user_message = "This file is not a valid PDF or it is damaged."


class PasswordRequiredError(PDFMasterError):
    user_message = "This PDF is password-protected. Enter the password to open it."


class WrongPasswordError(PDFMasterError):
    user_message = "The password is incorrect."


class ExportError(PDFMasterError):
    user_message = "The result could not be saved. Your original file was not changed."


class DependencyMissingError(PDFMasterError):
    user_message = "A required component is not installed."


def to_user_message(exc: BaseException) -> str:
    """Map any exception to a short, understandable message."""
    if isinstance(exc, PDFMasterError):
        return exc.user_message
    if isinstance(exc, PermissionError):
        return "Permission denied. Close the file in other programs or choose another folder."
    if isinstance(exc, FileNotFoundError):
        return "The file could not be found. It may have been moved or deleted."
    if isinstance(exc, MemoryError):
        return "Not enough memory to process this document."
    if isinstance(exc, OSError):
        return "A file system error occurred. Check free disk space and the output folder."
    return PDFMasterError.user_message
