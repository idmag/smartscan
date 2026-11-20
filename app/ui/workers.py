"""Background workers so the UI never blocks on image processing.

Lifetime rules (important, this used to crash):
* ``setAutoDelete(False)`` -- Qt must not delete the C++ object behind our
  Python worker after ``run()``; Python owns it.
* The returned worker is kept in a module-level registry until it finishes,
  otherwise the Python object can be garbage collected while the thread pool
  is still using it.
"""

from __future__ import annotations

import traceback
from dataclasses import dataclass, field

import numpy as np
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from ..core import detect as detect_mod
from ..core import scan_device
from ..core.scanner import Page, scan_many


@dataclass
class DetectionJobResult:
    ok: bool
    detections: list = field(default_factory=list)
    error: str = ""
    elapsed: float = 0.0


@dataclass
class ScanJobResult:
    ok: bool
    pages: list[Page] = field(default_factory=list)
    error: str = ""
    elapsed: float = 0.0


class _Signals(QObject):
    finished = Signal(object)
    failed = Signal(str)


class _BaseWorker(QRunnable):
    """Shared plumbing: safe signals, autoDelete off, error reporting."""

    def __init__(self) -> None:
        super().__init__()
        self.setAutoDelete(False)
        self.signals = _Signals()
        self._done = False

    def _emit(self, payload) -> None:
        if not self._done:
            self._done = True
            self.signals.finished.emit(payload)

    def _fail(self, exc: BaseException) -> None:
        if not self._done:
            self._done = True
            self.signals.failed.emit(f"{exc}\n{traceback.format_exc(limit=3)}")


class DetectionWorker(_BaseWorker):
    """Detects document quads on a photo."""

    def __init__(self, image: np.ndarray, min_confidence: float = 0.0):
        super().__init__()
        self.image = image
        self.min_confidence = min_confidence

    @Slot()
    def run(self) -> None:
        import time

        started = time.perf_counter()
        try:
            result = detect_mod.detect_documents(self.image)
            pairs = [
                (d.quad, {"score": d.score, "source": d.source})
                for d in result.detections
                if d.score >= self.min_confidence
            ]
            self._emit(
                DetectionJobResult(
                    ok=True, detections=pairs, elapsed=time.perf_counter() - started
                )
            )
        except Exception as exc:  # noqa: BLE001
            self._fail(exc)


class ScanWorker(_BaseWorker):
    """Dewarps + enhances every confirmed quad."""

    def __init__(self, image: np.ndarray, quads: list[np.ndarray], mode: str):
        super().__init__()
        self.image = image
        self.quads = list(quads)
        self.mode = mode

    @Slot()
    def run(self) -> None:
        import time

        started = time.perf_counter()
        try:
            pages = scan_many(self.image, self.quads, mode=self.mode)
            self._emit(
                ScanJobResult(ok=True, pages=pages, elapsed=time.perf_counter() - started)
            )
        except Exception as exc:  # noqa: BLE001
            self._fail(exc)


@dataclass
class ScannerJobResult:
    """What a :class:`ScanDeviceWorker` produced (images stay on disk)."""

    ok: bool = False
    pages: list = field(default_factory=list)     # list[Path], in page order
    feeder: bool = False
    warnings: list[str] = field(default_factory=list)
    error: str = ""
    hint: str = ""


class ScanDeviceWorker(_BaseWorker):
    """Acquires pages from a WIA scanner.

    Scanner warm-up, feeder pulls and driver hiccups all happen off the GUI
    thread; the result is a list of image files for the caller to load.
    """

    def __init__(self, device, dpi: int = 300, paper_hex: str = "") -> None:
        super().__init__()
        self.device = device
        self.dpi = dpi
        self.paper_hex = paper_hex

    @Slot()
    def run(self) -> None:
        import shutil
        import tempfile
        from pathlib import Path

        folder = Path(tempfile.mkdtemp(prefix="smartscan_scan_"))
        try:
            result = scan_device.acquire_pages(
                self.device, dpi=self.dpi, paper_hex=self.paper_hex, folder=folder
            )
            pages: list[Path] = []
            for path in result.pages:
                pages.extend(scan_device.split_multipage(path))
            self._emit(
                ScannerJobResult(
                    ok=True,
                    pages=pages,
                    feeder=result.feeder,
                    warnings=list(result.warnings),
                )
            )
        except scan_device.ScannerError as exc:
            shutil.rmtree(folder, ignore_errors=True)
            self._emit(ScannerJobResult(ok=False, error=exc.message, hint=exc.hint))
        except Exception as exc:  # noqa: BLE001 - never crash the pool
            shutil.rmtree(folder, ignore_errors=True)
            self._fail(exc)


class DeviceListWorker(_BaseWorker):
    """Asks Windows which scanners are attached."""

    @Slot()
    def run(self) -> None:
        try:
            devices = scan_device.list_devices()
            self.signals.finished.emit(devices)
        except scan_device.ScannerError as exc:
            self._emit(ScannerJobResult(ok=False, error=exc.message, hint=exc.hint))
        except Exception as exc:  # noqa: BLE001
            self._fail(exc)


# Workers that are still running; keeps Python objects alive until they finish.
_ACTIVE: set[_BaseWorker] = set()


def _start(pool: QThreadPool, worker: _BaseWorker, on_done, on_error) -> _BaseWorker:
    _ACTIVE.add(worker)

    def _finish(payload) -> None:
        _ACTIVE.discard(worker)
        try:
            on_done(payload)
        finally:
            worker.signals.deleteLater()

    def _fail(message: str) -> None:
        _ACTIVE.discard(worker)
        try:
            if on_error is not None:
                on_error(message)
        finally:
            worker.signals.deleteLater()

    worker.signals.finished.connect(_finish)
    worker.signals.failed.connect(_fail)
    pool.start(worker)
    return worker


def run_detection(pool: QThreadPool, image: np.ndarray, callback, error_callback=None,
                  min_confidence: float = 0.0) -> DetectionWorker:
    worker = DetectionWorker(image, min_confidence=min_confidence)
    return _start(pool, worker, callback, error_callback)


def run_scan(pool: QThreadPool, image: np.ndarray, quads, callback,
             error_callback=None, mode: str = "magic") -> ScanWorker:
    worker = ScanWorker(image, list(quads), mode)
    return _start(pool, worker, callback, error_callback)


def run_scanner(pool: QThreadPool, device, callback, error_callback=None,
                dpi: int = 300, paper_hex: str = "") -> ScanDeviceWorker:
    worker = ScanDeviceWorker(device, dpi=dpi, paper_hex=paper_hex)
    return _start(pool, worker, callback, error_callback)


def run_device_list(pool: QThreadPool, callback, error_callback=None) -> DeviceListWorker:
    worker = DeviceListWorker()
    return _start(pool, worker, callback, error_callback)


def active_worker_count() -> int:
    """For tests/diagnostics."""
    return len(_ACTIVE)
