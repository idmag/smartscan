"""Settings dialog."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..core.enhance import MODE_LABELS, MODES
from ..core.naming import DEFAULT_TEMPLATE, render_name, validate_template
from ..core.settings import Settings, default_output_dir


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("SmartScan settings")
        self.setModal(True)
        self.setMinimumWidth(500)
        self._settings = settings

        # -- output folder
        self.folder_edit = QLineEdit(settings.output_dir or str(default_output_dir()))
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        folder_row = QHBoxLayout()
        folder_row.setSpacing(6)
        folder_row.addWidget(self.folder_edit, 1)
        folder_row.addWidget(browse)

        # -- format
        self.format_combo = QComboBox()
        for value, label in (
            ("pdf", "PDF (one multi-page file)"),
            ("pdf-pages", "PDF (one file per page)"),
            ("jpg", "JPG images"),
            ("png", "PNG images"),
            ("tiff", "TIFF images"),
        ):
            self.format_combo.addItem(label, value)
        self._set_format(settings)

        self.pdf_check = QCheckBox("Combine all pages into a single PDF")
        self.pdf_check.setChecked(settings.combine_pdf)
        self.pdf_check.setVisible(settings.format == "pdf")

        # -- mode
        self.mode_combo = QComboBox()
        for mode in MODES:
            self.mode_combo.addItem(MODE_LABELS[mode], mode)
        index = self.mode_combo.findData(settings.mode)
        self.mode_combo.setCurrentIndex(max(0, index))

        # -- quality
        self.quality = QSpinBox()
        self.quality.setRange(40, 100)
        self.quality.setValue(settings.jpeg_quality)
        self.quality.setSuffix(" %")

        # -- naming
        self.template_edit = QLineEdit(settings.name_template or DEFAULT_TEMPLATE)
        self.template_edit.textChanged.connect(self._update_preview)
        self.preview_label = QLabel()
        self.preview_label.setProperty("muted", True)
        hint = QLabel(
            "Tokens: {date} {time} {index} {doc} {total} {timestamp}. "
            "Use {index:3} to pad with zeros."
        )
        hint.setProperty("muted", True)
        hint.setWordWrap(True)

        # -- behaviour
        self.auto_detect = QCheckBox("Detect documents automatically when a photo is added")
        self.auto_detect.setChecked(settings.auto_detect_on_open)
        self.open_folder = QCheckBox("Open the output folder after saving")
        self.open_folder.setChecked(settings.open_folder_after)
        self.combine_check_alias = None

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.addRow("Save scans to", folder_row)
        form.addRow("File format", self.format_combo)
        form.addRow("", self.pdf_check)
        form.addRow("Default cleanup", self.mode_combo)
        form.addRow("JPG / PDF quality", self.quality)
        form.addRow("File name", self.template_edit)
        form.addRow("", self.preview_label)
        form.addRow("", hint)
        form.addRow("", self.auto_detect)
        form.addRow("", self.open_folder)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 14)
        layout.setSpacing(14)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self.format_combo.currentIndexChanged.connect(self._on_format_changed)
        self._update_preview()

    def _set_format(self, settings: Settings) -> None:
        target = settings.format
        if target == "pdf" and not settings.combine_pdf:
            target = "pdf-pages"
        index = self.format_combo.findData(target)
        self.format_combo.setCurrentIndex(max(0, index))

    def _on_format_changed(self) -> None:
        self.pdf_check.setVisible(self.format_combo.currentData() == "pdf")

    def _browse(self) -> None:
        start = self.folder_edit.text() or str(default_output_dir())
        chosen = QFileDialog.getExistingDirectory(self, "Choose the folder for scans", start)
        if chosen:
            self.folder_edit.setText(chosen)

    def _update_preview(self) -> None:
        template = self.template_edit.text().strip()
        unknown = validate_template(template)
        if unknown:
            self.preview_label.setText(f"⚠ Unknown token(s): {', '.join(unknown)}")
            return
        try:
            sample = render_name(template, index=1, total=3)
        except Exception:  # noqa: BLE001
            sample = "—"
        self.preview_label.setText(f"Example: {sample}.pdf")

    def _accept(self) -> None:
        unknown = validate_template(self.template_edit.text())
        if unknown:
            self.preview_label.setText(f"⚠ Unknown token(s): {', '.join(unknown)}")
            return
        folder = self.folder_edit.text().strip()
        if not folder:
            folder = str(default_output_dir())
        try:
            Path(folder).mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self.preview_label.setText(f"⚠ Cannot create folder: {exc}")
            return
        self.accept()

    def apply_to(self, settings: Settings) -> None:
        settings.output_dir = self.folder_edit.text().strip() or str(default_output_dir())
        selected = self.format_combo.currentData()
        if selected == "pdf-pages":
            settings.format = "pdf"
            settings.combine_pdf = False
        else:
            settings.format = selected
            settings.combine_pdf = self.pdf_check.isChecked()
        settings.mode = self.mode_combo.currentData()
        settings.jpeg_quality = self.quality.value()
        settings.name_template = self.template_edit.text().strip() or DEFAULT_TEMPLATE
        settings.auto_detect_on_open = self.auto_detect.isChecked()
        settings.open_folder_after = self.open_folder.isChecked()
