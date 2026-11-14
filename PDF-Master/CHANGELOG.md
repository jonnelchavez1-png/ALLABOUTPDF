# Changelog

## [Unreleased]
- Initial project scaffold.
- `app/config.py`: constants, resource paths, JSON settings (theme, last directory, recent files).
- `utils/`: error types and user-friendly messages, logging, validation (PDF/image/page ranges), safe file handling.
- `core/`: reader (info, passwords, PyMuPDF page render), `PagePlan` (rotate/move/delete/duplicate/extract with
  undo/redo), exporter (temp file, validation, no overwrite, originals protected), merger, splitter, rotator,
  security (AES-256 protect / authorized unlock), watermark + page numbers, compressor (measured sizes only),
  converter (images to PDF with preview layout; PDF to images via PyMuPDF).
- Tests for reader/validation, organizer, merger, splitter, compressor, converter, security, watermark.
- Fix: compressor works with pypdf 5 and 7 (renamed keyword); requirements pin pypdf to the tested 5.x range.
- `ui/`, `services/`: not implemented yet.
