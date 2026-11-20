"""Bottom action bar: enhancement choice, destination folder, Scan & Save."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from ..core.enhance import MODE_LABELS, MODES
from . import theme


class ScanBar(QWidget):
    scan_requested = Signal()
    mode_changed = Signal(str)
    folder_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("scanBar")
        self.setStyleSheet(
            f"#scanBar {{ background: {theme.PANEL}; border-top: 1px solid {theme.BORDER}; }}"
        )

        self.mode_combo = QComboBox()
        for mode in MODES:
            self.mode_combo.addItem(MODE_LABELS[mode], mode)
        self.mode_combo.setToolTip("How scanned pages are cleaned up")
        self.mode_combo.setMinimumWidth(110)
        self.mode_combo.currentIndexChanged.connect(
            lambda _i: self.mode_changed.emit(self.mode_combo.currentData())
        )

        self.folder_label = QLabel()
        self.folder_label.setProperty("muted", True)
        self.folder_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.folder_label.setMinimumWidth(120)
        self.change_folder_btn = QPushButton("Change…")
        self.change_folder_btn.setProperty("flat", "true")
        self.change_folder_btn.setToolTip("Choose where scanned documents are saved")
        self.change_folder_btn.clicked.connect(self._pick_folder)

        self.summary = QLabel("No documents detected yet")
        self.summary.setProperty("muted", True)

        self.scan_btn = QPushButton("Scan && Save")
        self.scan_btn.setProperty("variant", "primary")
        self.scan_btn.setMinimumWidth(140)
        self.scan_btn.setToolTip("Scan the documents and save them to the chosen folder (Ctrl+S)")
        self.scan_btn.clicked.connect(self.scan_requested)
        self.scan_btn.setEnabled(False)
        self._folder = ""

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        mode_box = QHBoxLayout()
        mode_box.setSpacing(6)
        mode_label = QLabel("Mode")
        mode_label.setProperty("muted", True)
        mode_box.addWidget(mode_label)
        mode_box.addWidget(self.mode_combo)

        folder_box = QHBoxLayout()
        folder_box.setSpacing(4)
        save_label = QLabel("Save to")
        save_label.setProperty("muted", True)
        folder_box.addWidget(save_label)
        folder_box.addWidget(self.folder_label)
        folder_box.addWidget(self.change_folder_btn)

        layout.addLayout(mode_box)
        layout.addSpacing(8)
        layout.addLayout(folder_box, 1)
        layout.addWidget(self.summary)
        layout.addWidget(self.scan_btn)

    # -- folder ----------------------------------------------------------
    def set_folder(self, folder: str | Path) -> None:
        self._folder = str(folder)
        path = Path(self._folder)
        name = path.name or self._folder
        self.folder_label.setText(name)
        self.folder_label.setToolTip(self._folder + "\nDouble-click to change")
        self.folder_label.setCursor(Qt.CursorShape.PointingHandCursor)

    def folder(self) -> str:
        return self._folder

    def _pick_folder(self) -> None:
        start = self._folder or str(Path.home())
        chosen = QFileDialog.getExistingDirectory(
            self, "Choose the folder for scanned documents", start
        )
        if chosen:
            self.set_folder(chosen)
            self.folder_changed.emit(chosen)

    # -- state -----------------------------------------------------------
    def set_mode(self, mode: str) -> None:
        index = self.mode_combo.findData(mode)
        if index >= 0:
            self.mode_combo.blockSignals(True)
            self.mode_combo.setCurrentIndex(index)
            self.mode_combo.blockSignals(False)

    def current_mode(self) -> str:
        return self.mode_combo.currentData()

    def set_scan_enabled(self, enabled: bool) -> None:
        self.scan_btn.setEnabled(enabled)

    def set_summary(self, text: str) -> None:
        self.summary.setText(text)

    def set_busy(self, busy: bool, text: str = "") -> None:
        self.scan_btn.setEnabled(not busy and self.scan_btn.isEnabled())
        if text:
            self.summary.setText(text)
