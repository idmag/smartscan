"""Output file naming for scanned documents."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

_TOKEN_RE = re.compile(r"\{([a-z_]+)(?::(\d+))?\}")

DEFAULT_TEMPLATE = "Scan_{date}_{time}_{index}"


def validate_template(template: str) -> list[str]:
    """Return a list of unknown tokens in *template* (empty if valid)."""
    known = {"date", "time", "index", "doc", "total", "timestamp"}
    unknown = []
    for match in _TOKEN_RE.finditer(template or ""):
        if match.group(1) not in known:
            unknown.append(match.group(1))
    return unknown


def sanitize_stem(stem: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", stem or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned[:120] or "Scan"


def render_name(
    template: str = DEFAULT_TEMPLATE,
    *,
    index: int = 1,
    total: int = 1,
    when: datetime | None = None,
) -> str:
    """Render the file template. ``index`` is 1-based."""
    when = when or datetime.now()
    values = {
        "date": when.strftime("%Y-%m-%d"),
        "time": when.strftime("%H-%M-%S"),
        "timestamp": when.strftime("%Y%m%d-%H%M%S"),
        "index": str(index),
        "doc": str(index),
        "total": str(total),
    }

    def repl(match: re.Match) -> str:
        key, width = match.group(1), match.group(2)
        value = values.get(key, match.group(0))
        if width and value.isdigit():
            value = value.zfill(int(width))
        return value

    return sanitize_stem(_TOKEN_RE.sub(repl, template or DEFAULT_TEMPLATE))


def unique_path(folder: Path, stem: str, suffix: str) -> Path:
    """Return a path inside *folder* that does not exist yet (adds _2, _3...)."""
    folder = Path(folder)
    suffix = "." + suffix.lstrip(".")
    candidate = folder / f"{stem}{suffix}"
    counter = 2
    while candidate.exists():
        candidate = folder / f"{stem}_{counter}{suffix}"
        counter += 1
    return candidate
