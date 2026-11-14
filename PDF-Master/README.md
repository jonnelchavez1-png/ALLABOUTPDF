# PDF Master

Offline, all-in-one Windows desktop PDF manager (Python + PySide6).

**Status:** project scaffold only. No features implemented yet.

## Setup
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Structure
- `app/` configuration and startup
- `ui/` interface and live previews
- `core/` PDF engine (no UI code)
- `services/` previews, thumbnails, background processing, history
- `utils/` validation, file handling, errors, logging
- `tests/` pytest suite
