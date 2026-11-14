"""App constants, paths, and persisted settings (theme, last directory)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

APP_NAME = "PDF Master"
APP_VERSION = "0.1.0"

SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".gif", ".webp"}
PDF_EXTENSION = ".pdf"


def resource_path(relative: str) -> Path:
    """Resolve a bundled resource path (works in dev and under PyInstaller)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / relative


def user_data_dir() -> Path:
    """Per-user folder for settings, history and logs. Created on demand."""
    if sys.platform.startswith("win"):
        root = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    path = root / "PDFMaster"
    path.mkdir(parents=True, exist_ok=True)
    return path


class Settings:
    """Small JSON-backed settings store. Never raises on a corrupt/missing file."""

    DEFAULTS = {"theme": "light", "last_directory": "", "recent_files": []}

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path else user_data_dir() / "settings.json"
        self._data = dict(self.DEFAULTS)
        self.load()

    def load(self) -> None:
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                self._data.update({k: v for k, v in loaded.items() if k in self.DEFAULTS})
        except (OSError, ValueError):
            pass  # first run or unreadable file: keep defaults

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    def get(self, key: str):
        return self._data.get(key, self.DEFAULTS.get(key))

    def set(self, key: str, value) -> None:
        if key not in self.DEFAULTS:
            raise KeyError(f"Unknown setting: {key}")
        self._data[key] = value
        self.save()
