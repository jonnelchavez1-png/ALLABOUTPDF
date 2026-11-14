# PDF Master

Offline, all-in-one Windows desktop PDF manager (Python + PySide6).

**Status:** PDF engine (`core/`, `utils/`) implemented and tested. UI and services not implemented yet.

## Tested vs untested
- Tested (pytest, Linux sandbox): merge, split, organize (rotate/move/delete/duplicate/extract + undo/redo), export safety,
  compression, image to PDF, password protect/unlock, watermark and page numbers, validation.
- Written but NOT yet run: PDF to images and page rendering (need PyMuPDF), all UI, Windows packaging.

## Known limitations
- Watermark/page numbers use the built-in Helvetica font (Latin text). Pass a .ttf for other scripts.
- Merge does not carry over bookmarks; images are always centered on the page.

## Quick start (Windows)
1. Install Python 3.11 or 3.12 (64-bit) and tick "Add python.exe to PATH".
2. Extract the whole zip, then double-click `setup.bat`. It builds the Python environment in `%LOCALAPPDATA%\PDFMaster\venv` (outside the project folder) and installs dependencies. It prefers Python 3.12.
3. Double-click `run_tests.bat` to verify the engine, or `run.bat` to launch the app (UI not built yet).

## Manual setup
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m pytest
python main.py   # UI not built yet
```

## Structure
- `app/` configuration and startup
- `ui/` interface and live previews
- `core/` PDF engine (no UI code)
- `services/` previews, thumbnails, background processing, history
- `utils/` validation, file handling, errors, logging
- `tests/` pytest suite
