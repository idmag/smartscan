"""Persistent user settings.

Stored as JSON in the user's AppData folder on Windows.  Uses QSettings when a
Qt application is available (so the Windows installer/uninstaller and the rest
of the OS see a normal application), and falls back to a plain JSON file so the
module stays unit-testable without Qt.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

APP_NAME = "SmartScan"
ORG_NAME = "SmartScan"

DEFAULT_OUTPUT_DIR = "Documents\\SmartScan"


@dataclass
class Settings:
    output_dir: str = ""
    format: str = "pdf"                 # pdf | jpg | png | tiff
    mode: str = "magic"                 # original|color|gray|bw|magic
    jpeg_quality: int = 90
    auto_detect_on_open: bool = True
    auto_scan: bool = False             # scan, then save immediately
    open_folder_after: bool = True
    name_template: str = "Scan_{date}_{time}_{index}"
    combine_pdf: bool = True            # one multi-page PDF per scan batch
    min_confidence: float = 0.35
    extra: dict[str, Any] | None = None

    def resolved_output_dir(self) -> Path:
        if self.output_dir.strip():
            return Path(self.output_dir).expanduser()
        return default_output_dir()


def default_output_dir() -> Path:
    """``%USERPROFILE%\\Documents\\SmartScan`` (or ~/Documents elsewhere)."""
    home = Path.home()
    documents = home / "Documents"
    base = documents if documents.is_dir() else home
    return base / "SmartScan"


def _settings_file() -> Path:
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Roaming"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".config"
    return base / APP_NAME / "settings.json"


def load_settings(path: Path | None = None) -> Settings:
    """Load settings, ignoring corrupt or unknown keys."""
    target = path or _settings_file()
    settings = Settings()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return settings
    if not isinstance(data, dict):
        return settings
    known = {f.name for f in fields(Settings)}
    for key, value in data.items():
        if key in known:
            setattr(settings, key, value)
    settings.format = settings.format if settings.format in {"pdf", "jpg", "png", "tiff"} else "pdf"
    settings.min_confidence = min(max(float(settings.min_confidence), 0.0), 1.0)
    settings.jpeg_quality = min(max(int(settings.jpeg_quality), 40), 100)
    return settings


def save_settings(settings: Settings, path: Path | None = None) -> Path:
    target = path or _settings_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
    return target
