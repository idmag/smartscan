"""One loaded photo and everything derived from it."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ..core.detect import Detection
from ..core.scanner import Page


@dataclass
class DocPage:
    """A source photo plus its detections and resulting scanned pages."""

    path: Path | None
    image: np.ndarray                      # BGR full resolution
    origin: str = "photo"                  # "photo" | "scan" | "clipboard"
    detections: list[Detection] = field(default_factory=list)
    pages: list[Page] = field(default_factory=list)
    excluded: set[int] = field(default_factory=set)   # detection indices excluded
    preview: np.ndarray | None = None      # cached preview of the selected doc
    detected: bool = False
    notes: str = ""

    @property
    def name(self) -> str:
        return self.path.name if self.path else "Clipboard image"

    @property
    def is_scan(self) -> bool:
        """True when the page came straight off a flatbed or feeder.

        Detection advice differs: on a scan the background is the scanner's
        own lid, which the user cannot change by "improving the lighting".
        """
        return self.origin == "scan"

    @property
    def source_label(self) -> str:
        return "scr" if self.is_scan else "ph"

    @property
    def size_label(self) -> str:
        h, w = self.image.shape[:2]
        return f"{w} × {h}"

    def quads(self) -> list[np.ndarray]:
        return [d.quad for d in self.detections]

    def included_quads(self) -> list[np.ndarray]:
        return [d.quad for i, d in enumerate(self.detections) if i not in self.excluded]

    def clear_results(self) -> None:
        self.pages = []
        self.preview = None

    def toggle_excluded(self, index: int) -> None:
        if index in self.excluded:
            self.excluded.discard(index)
        else:
            self.excluded.add(index)
        self.clear_results()
