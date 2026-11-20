"""Choose a scanner and scan pages into SmartScan.

The dialog is deliberately thin: it lists the WIA devices Windows reports,
collects a DPI, and hands the work to :class:`ScanDeviceWorker`.  All the
hardware risk lives in the worker and in ``app/core/scan_device.py``.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..core.settings import Settings, save_settings
from ..core.scan_device import DEFAULT_DPI, DPI_CHOICES, ScannerDevice, ScannerError, list_devices
from .theme import ACCENT
from .workers import (
    DeviceListWorker,
    DiagnosticsResult,
    ScannerJobResult,
    run_device_list,
    run_diagnose,
    run_scanner,
)


class ScanDeviceDialog(QDialog):
    """Pick a scanner, scan pages, and return the image files."""

    def __init__(self, settings: Settings, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Scan from scanner")
        self.setMinimumWidth(520)
        self.settings = settings
        self.pool = QThreadPool.globalInstance()
        self.page_files: list[Path] = []
        self._devices: list[ScannerDevice] = []
        self._busy = False
        self._temp_dirs: list[str] = []

        self.intro = QLabel(
            "Load the pages in the scanner, then choose a device and press Scan."
        )
        self.intro.setWordWrap(True)

        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(300)
        self.dpi_combo = QComboBox()
        for dpi in DPI_CHOICES:
            self.dpi_combo.addItem(f"{dpi} DPI", dpi)
        self.dpi_combo.setCurrentIndex(DPI_CHOICES.index(DEFAULT_DPI))
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        self.hint.setTextFormat(Qt.TextFormat.RichText)
        self.hint.setVisible(False)

        form = QFormLayout()
        form.addRow("Scanner:", self.device_combo)
        form.addRow("Resolution:", self.dpi_combo)

        self.buttons = QDialogButtonBox()
        self.scan_button = self.buttons.addButton(
            "Scan", QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.rescan_button = self.buttons.addButton(
            "Scan again", QDialogButtonBox.ButtonRole.ActionRole
        )
        self.close_button = self.buttons.addButton(
            "Close", QDialogButtonBox.ButtonRole.RejectRole
        )
        self.rescan_button.setVisible(False)
        # Constructed with the other buttons but placed in the button box below,
        # left of Scan, so it reads as a utility rather than a primary action.
        self.diagnose_button = QPushButton("Diagnose…")
        self.diagnose_button.setToolTip(
            "Save a report describing what this scanner driver supports"
        )
        self.diagnose_button.setEnabled(False)
        self.diagnose_button.clicked.connect(self._diagnose_clicked)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 12)
        layout.setSpacing(10)
        layout.addWidget(self.intro)
        layout.addLayout(form)
        layout.addWidget(self.hint)
        self.buttons.addButton(
            self.diagnose_button, QDialogButtonBox.ButtonRole.ResetRole
        )
        layout.addWidget(self.buttons)

        self.buttons.accepted.connect(self._scan_clicked)
        self.buttons.rejected.connect(self.reject)
        self.rescan_button.clicked.connect(self._scan_clicked)
        self.device_combo.currentIndexChanged.connect(self._remember_device)

        self._load_devices()

    # ------------------------------------------------------------- devices
    def _load_devices(self) -> None:
        self.device_combo.clear()
        self.device_combo.addItem("Looking for scanners…", None)
        self._set_busy(True)
        self._list_worker = run_device_list(
            self.pool, self._on_devices, self._on_device_error
        )

    def _on_devices(self, devices) -> None:
        self._set_busy(False)
        if isinstance(devices, ScannerJobResult):  # an error came back instead
            self._devices = []
            self._show_unavailable(devices.error, devices.hint)
            return
        self._devices = list(devices)
        self.device_combo.clear()
        if not self._devices:
            self._show_no_scanner()
            return
        self.hint.setVisible(False)
        for device in self._devices:
            self.device_combo.addItem(device.label, device.device_id)
        wanted = (self.settings.extra or {}).get("scanner_id")
        for index, device in enumerate(self._devices):
            if wanted and device.device_id == wanted:
                self.device_combo.setCurrentIndex(index)
                break
        self.scan_button.setEnabled(True)
        self.device_combo.setEnabled(True)
        self.dpi_combo.setEnabled(True)
        self.diagnose_button.setEnabled(True)
        self.intro.setText(
            "Load the pages in the scanner, then press Scan. "
            "A document feeder will pull every page it finds."
        )

    def _on_device_error(self, message: str) -> None:
        self._set_busy(False)
        self._devices = []
        self._show_unavailable(
            "Windows could not look for scanners.", message.splitlines()[0]
        )

    def _show_unavailable(self, message: str, hint: str) -> None:
        """No usable scanner: disable scanning and say why, in plain words."""
        self.device_combo.clear()
        self.device_combo.addItem("No scanner available", None)
        self.device_combo.setEnabled(False)
        self.scan_button.setEnabled(False)
        self.rescan_button.setVisible(False)
        self.diagnose_button.setEnabled(False)
        self.intro.setText(
            "SmartScan uses the scanner support built into Windows (WIA)."
        )
        self._show_problem(message, hint, retry=True)
        # "Look again" keeps the dialog useful after plugging a scanner in,
        # but it must not look like a normal Scan button.
        self.scan_button.setEnabled(True)
        self.scan_button.setText("Look again")

    def _show_no_scanner(self) -> None:
        self.device_combo.addItem("No scanner found", None)
        self.device_combo.setEnabled(False)
        self.scan_button.setEnabled(False)
        self.intro.setText(
            "SmartScan uses the scanner support built into Windows (WIA), "
            "and Windows reports no scanner."
        )
        self._show_problem(
            "No scanner was found.",
            "Check that it is switched on and connected by USB or Wi-Fi, then press "
            "\"Look again\". If it is a network scanner, install its Windows driver "
            "first.<br><br>You can still use <b>Add photos</b> for images saved by the "
            "scanner's own software.",
            retry=False,
        )
        self.scan_button.setEnabled(True)
        self.scan_button.setText("Look again")

    def _show_problem(self, message: str, hint: str = "", retry: bool = False) -> None:
        html = f"<b>{message}</b>"
        if hint:
            html += f"<br><br>{hint}"
        self.hint.setText(html)
        self.hint.setStyleSheet(
            f"QLabel {{ background: #fff4f4; border: 1px solid #f0c9c9; color: #8a2b2b;"
            f" border-radius: 8px; padding: 10px; }}"
        )
        self.hint.setVisible(True)
        if retry:
            self.rescan_button.setVisible(False)
            self.scan_button.setText("Look again")
            self.scan_button.setEnabled(True)
            self.scan_button.setStyleSheet("")
        self.adjustSize()

    # -------------------------------------------------------------- scan
    def _scan_clicked(self) -> None:
        if self.scan_button.text() == "Look again":
            self.scan_button.setText("Scan")
            self.hint.setVisible(False)
            self._load_devices()
            return
        device_id = self.device_combo.currentData()
        if not device_id:
            return
        device = next((d for d in self._devices if d.device_id == device_id), None)
        if device is None:
            return
        self._remember_device()
        dpi = int(self.dpi_combo.currentData() or DEFAULT_DPI)
        self._set_busy(True)
        self.intro.setText(
            "Scanning… this can take a few seconds while the scanner warms up."
        )
        self._scan_worker = run_scanner(
            self.pool, device, self._on_scanned, self._on_scan_error, dpi=dpi
        )

    def _on_scanned(self, result: ScannerJobResult) -> None:
        self._set_busy(False)
        if not result.ok:
            self._show_problem(result.error, result.hint, retry=False)
            self.scan_button.setEnabled(True)
            self.scan_button.setText("Try again")
            return
        self.page_files = [Path(p) for p in result.pages]
        self._temp_dirs = sorted({str(p.parent) for p in self.page_files})
        pages = len(self.page_files)
        note = ""
        if result.warnings:
            note = " " + result.warnings[0]
        self.intro.setText(
            f"Scanned {pages} page{'s' if pages != 1 else ''}.{note} "
            "Press Scan again for more, or Close to work on these pages."
        )
        self.hint.setVisible(False)
        self.rescan_button.setVisible(True)
        self.scan_button.setText("Scan")
        self.scan_button.setEnabled(True)
        self.accept()

    def _on_scan_error(self, message: str) -> None:
        self._set_busy(False)
        self.scan_button.setEnabled(True)
        self.intro.setText("The scanner stopped unexpectedly.")
        self._show_problem("The scan failed.", message.splitlines()[0])

    # -------------------------------------------------------- diagnostics
    def _current_device(self) -> ScannerDevice | None:
        device_id = self.device_combo.currentData()
        return next((d for d in self._devices if d.device_id == device_id), None)

    def _diagnose_clicked(self) -> None:
        device = self._current_device()
        if device is None:
            return
        self.diagnose_button.setEnabled(False)
        self.diagnose_button.setText("Reading driver…")
        self._diagnose_worker = run_diagnose(
            self.pool, device, self._on_diagnosed, self._on_diagnose_error
        )

    def _on_diagnosed(self, result) -> None:
        self.diagnose_button.setEnabled(True)
        self.diagnose_button.setText("Diagnose…")
        if isinstance(result, DiagnosticsResult) and not result.ok:
            QMessageBox.warning(self, "Diagnose scanner", result.error)
            return
        text = result.text if isinstance(result, DiagnosticsResult) else str(result)
        target, _ = QFileDialog.getSaveFileName(
            self,
            "Save scanner report",
            str(Path.home() / "smartscan-scanner-report.txt"),
            "Text files (*.txt)",
        )
        if not target:
            return
        try:
            Path(target).write_text(text, encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, "Could not save the report", str(exc))
            return
        self.hint.setVisible(False)
        QMessageBox.information(
            self,
            "Scanner report saved",
            f"Saved to:\n{target}\n\n"
            "Send this file with any bug report — it lists exactly which settings "
            "the scanner driver accepts.",
        )

    def _on_diagnose_error(self, message: str) -> None:
        self.diagnose_button.setEnabled(True)
        self.diagnose_button.setText("Diagnose…")
        QMessageBox.warning(self, "Diagnose scanner", message.splitlines()[0])

    # ------------------------------------------------------------ helpers
    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.device_combo.setEnabled(not busy and bool(self._devices))
        self.dpi_combo.setEnabled(not busy)
        self.scan_button.setEnabled(not busy)
        if busy:
            self.scan_button.setText("Scanning…")
        else:
            self.scan_button.setText("Scan")

    def _remember_device(self) -> None:
        device_id = self.device_combo.currentData()
        if not device_id:
            return
        extra = dict(self.settings.extra or {})
        if extra.get("scanner_id") == device_id:
            return
        extra["scanner_id"] = device_id
        self.settings.extra = extra
        try:
            save_settings(self.settings)
        except OSError:
            pass

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        if self._busy:
            event.ignore()
            return
        super().closeEvent(event)


# Temp folders whose images the main window now owns.  They are removed when
# the process exits, not when the dialog closes.
_KEEP: list[str] = []


def keep_for_session(paths: list[Path]) -> None:
    """Keep the temp folders holding *paths* until this process exits."""
    import atexit
    import shutil

    for parent in {str(Path(p).parent) for p in paths}:
        if parent in _KEEP:
            continue
        _KEEP.append(parent)

        def _cleanup(folder: str = parent) -> None:
            shutil.rmtree(folder, ignore_errors=True)

        atexit.register(_cleanup)


def list_scanners_without_ui() -> list[ScannerDevice]:
    """Small helper used by tests and diagnostics."""
    try:
        return list_devices()
    except ScannerError:
        return []
