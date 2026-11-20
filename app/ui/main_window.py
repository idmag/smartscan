"""SmartScan main window."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
from PySide6.QtCore import QSize, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import (
    QAction,
    QColor,
    QGuiApplication,
    QIcon,
    QImage,
    QKeySequence,
    QPainter,
    QPixmap,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ..core.detect import Detection, detect_documents
from ..core.naming import validate_template
from ..core.scanner import Page, scan_many, save_pages
from ..core.settings import Settings, default_output_dir, load_settings, save_settings
from . import theme
from .canvas import PreviewCanvas
from .doc_page import DocPage
from .photo_panel import PhotoPanel
from .qt_image import ndarray_to_qimage, ndarray_to_qpixmap
from .scan_bar import ScanBar
from .theme import apply_theme
from .thumbnail import PageThumb
from .workers import DetectionJobResult, ScanJobResult, run_detection, run_scan

IMAGE_FILTER = (
    "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp);;All files (*.*)"
)


def _app_icon(size: int = 256) -> QIcon:
    """Draw the SmartScan logo (a page with a scan line) at runtime."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    margin = size * 0.12
    p.setBrush(QColor(theme.ACCENT))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(int(margin), int(margin), int(size - 2 * margin), int(size - 2 * margin),
                      int(size * 0.16), int(size * 0.16))
    p.setBrush(QColor("#ffffff"))
    inset = size * 0.28
    p.drawRoundedRect(int(inset), int(inset), int(size - 2 * inset), int(size - 2 * inset),
                      int(size * 0.05), int(size * 0.05))
    pen_width = max(2, int(size * 0.035))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QColor(theme.ACCENT))
    for i in range(4):
        y = inset + size * 0.10 * (i + 1)
        p.drawLine(int(inset + size * 0.05), int(y), int(size - inset - size * 0.05), int(y))
    p.fillRect(int(inset - size * 0.02), int(size * 0.52), int(size - 2 * inset + size * 0.04),
               pen_width, QColor("#f59e0b"))
    p.end()
    return QIcon(pm)


class MainWindow(QMainWindow):
    """Load photos → detect documents → review → scan → save."""

    def __init__(self, settings: Settings | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.settings = settings or load_settings()
        self.pool = QThreadPool.globalInstance()
        self.pool.setMaxThreadCount(max(2, min(4, self.pool.maxThreadCount())))
        self.docs: list[DocPage] = []
        self.current_index = -1
        self.current_page_index = 0
        self._scanning = False
        self._detecting = False
        self._started = time.time()
        self._last_saved_dir: Path | None = None

        self.setWindowTitle("SmartScan")
        self.setWindowIcon(_app_icon())
        self.resize(1240, 820)
        self.setMinimumSize(880, 600)
        self.setAcceptDrops(True)

        self._build_actions()
        self._build_ui()
        self._build_menu()
        self._build_toolbar()
        self._connect()
        self._restore_settings()
        self._update_ui_state()

    # ------------------------------------------------------------------ UI
    def _build_actions(self) -> None:
        self.act_add = QAction("Add photos…", self)
        self.act_add.setShortcut(QKeySequence.StandardKey.Open)
        self.act_add.setToolTip("Add one or more photos of your documents (Ctrl+O)")
        self.act_add.triggered.connect(self.open_dialog)

        self.act_paste = QAction("Paste image", self)
        self.act_paste.setShortcut(QKeySequence.StandardKey.Paste)
        self.act_paste.setToolTip("Paste an image from the clipboard (Ctrl+V)")
        self.act_paste.triggered.connect(self.paste_image)

        self.act_detect = QAction("Re-detect documents", self)
        self.act_detect.setShortcut("Ctrl+R")
        self.act_detect.setToolTip("Run automatic document detection again (Ctrl+R)")
        self.act_detect.triggered.connect(lambda: self.detect_current(force=True))

        self.act_scan = QAction("Scan && Save", self)
        self.act_scan.setShortcut("Ctrl+S")
        self.act_scan.setToolTip("Scan every document and save to the chosen folder (Ctrl+S)")
        self.act_scan.triggered.connect(self.scan_and_save)

        self.act_scan_device = QAction("Scan from scanner…", self)
        self.act_scan_device.setShortcut("Ctrl+Shift+N")
        self.act_scan_device.setToolTip(
            "Scan pages directly from a scanner connected to this PC (Ctrl+Shift+N)"
        )
        self.act_scan_device.triggered.connect(self.scan_from_device)

        self.act_folder = QAction("Choose output folder…", self)
        self.act_folder.setShortcut("Ctrl+D")
        self.act_folder.triggered.connect(lambda: self.scan_bar._pick_folder())

        self.act_open_folder = QAction("Open output folder", self)
        self.act_open_folder.setShortcut("Ctrl+Shift+O")
        self.act_open_folder.triggered.connect(self.open_output_folder)

        self.act_settings = QAction("Settings…", self)
        self.act_settings.setShortcut("Ctrl+,")
        self.act_settings.triggered.connect(self.open_settings)

        self.act_help = QAction("How to use", self)
        self.act_help.setShortcut(QKeySequence.StandardKey.HelpContents)
        self.act_help.triggered.connect(self.show_help)

        self.act_about = QAction("About SmartScan", self)
        self.act_about.triggered.connect(self.show_about)

        self.act_remove = QAction("Remove photo", self)
        self.act_remove.setShortcut(QKeySequence.StandardKey.Delete)
        self.act_remove.triggered.connect(self.remove_current)

        self.act_exclude = QAction("Exclude / include this document", self)
        self.act_exclude.setShortcut("E")
        self.act_exclude.triggered.connect(self.toggle_current_excluded)

        self.act_quit = QAction("Quit", self)
        self.act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        self.act_quit.triggered.connect(self.close)

    def _build_ui(self) -> None:
        self.photo_panel = PhotoPanel()
        self.canvas = PreviewCanvas()
        self.scan_bar = ScanBar()

        # -- preview strip --------------------------------------------------
        self.thumbs_host = QWidget()
        self.thumbs_layout = QHBoxLayout(self.thumbs_host)
        self.thumbs_layout.setContentsMargins(8, 8, 8, 8)
        self.thumbs_layout.setSpacing(8)
        self.thumbs_layout.addStretch(1)

        self.thumbs_scroll = QScrollArea()
        self.thumbs_scroll.setWidget(self.thumbs_host)
        self.thumbs_scroll.setWidgetResizable(True)
        self.thumbs_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.thumbs_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.thumbs_scroll.setFixedHeight(200)
        self.thumbs_scroll.setVisible(False)

        self.strip_title = QLabel("Preview")
        self.strip_title.setProperty("heading", True)
        self.strip_count = QLabel("0 pages")
        self.strip_count.setProperty("pill", True)
        self.strip_hint = QLabel(
            "Double-click a page to exclude it · use “Scan & Save” when it looks right"
        )
        self.strip_hint.setProperty("muted", True)
        strip_header = QHBoxLayout()
        strip_header.setContentsMargins(14, 8, 14, 0)
        strip_header.addWidget(self.strip_title)
        strip_header.addWidget(self.strip_count)
        strip_header.addStretch(1)
        strip_header.addWidget(self.strip_hint)
        self.strip_header_widget = QWidget()
        self.strip_header_widget.setLayout(strip_header)
        self.strip_header_widget.setVisible(False)

        self.thumbs_container = QWidget()
        tc_layout = QVBoxLayout(self.thumbs_container)
        tc_layout.setContentsMargins(0, 0, 0, 0)
        tc_layout.setSpacing(0)
        tc_layout.addWidget(self.strip_header_widget)
        tc_layout.addWidget(self.thumbs_scroll)

        # -- central split --------------------------------------------------
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.photo_panel)
        self.splitter.addWidget(self.canvas)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([260, 980])
        self.splitter.setChildrenCollapsible(False)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(self.splitter, 1)
        right_layout.addWidget(self.thumbs_container)
        right_layout.addWidget(self.scan_bar)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.addWidget(right)
        self.setCentralWidget(container)

        # -- bottom progress ------------------------------------------------
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(5)
        self.progress.setVisible(False)
        container_layout.addWidget(self.progress)

        # -- empty state overlay (covers the whole canvas area) -------------
        self.empty_state = self._build_empty_state()
        self.empty_state.setParent(self.splitter)
        self.empty_state.setGeometry(self.splitter.rect())
        self.empty_state.setVisible(True)
        self.empty_state.raise_()

    def _build_empty_state(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("emptyState")
        widget.setStyleSheet("#emptyState { background: #eef1f5; border-radius: 0; }")
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        icon = QLabel()
        icon.setPixmap(_app_icon(96).pixmap(96, 96))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Drop photos of your documents here")
        title.setProperty("heading", True)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 20px;")

        subtitle = QLabel(
            "SmartScan finds every document in the photo, straightens it and\n"
            "prepares a clean, upright scan — then saves it to your folder."
        )
        subtitle.setProperty("muted", True)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        add = QPushButton("Add photos…")
        add.setObjectName("emptyAddButton")
        add.setMinimumWidth(150)
        add.clicked.connect(self.open_dialog)
        paste = QPushButton("Paste image")
        paste.clicked.connect(self.paste_image)
        buttons.addStretch(1)
        buttons.addWidget(add)
        buttons.addWidget(paste)
        buttons.addStretch(1)

        hint = QLabel(
            "You can also drag & drop files anywhere in the window, or paste with Ctrl+V."
        )
        hint.setProperty("muted", True)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addStretch(1)
        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(6)
        layout.addLayout(buttons)
        layout.addWidget(hint)
        layout.addStretch(1)
        return widget

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction(self.act_add)
        file_menu.addAction(self.act_paste)
        file_menu.addSeparator()
        file_menu.addAction(self.act_scan)
        file_menu.addAction(self.act_folder)
        file_menu.addSeparator()
        file_menu.addAction(self.act_scan_device)
        file_menu.addSeparator()
        file_menu.addAction(self.act_open_folder)
        file_menu.addSeparator()
        file_menu.addAction(self.act_quit)

        edit_menu = self.menuBar().addMenu("&Edit")
        edit_menu.addAction(self.act_remove)
        edit_menu.addAction(self.act_detect)
        edit_menu.addAction(self.act_exclude)
        edit_menu.addSeparator()
        edit_menu.addAction(self.act_settings)

        self.act_guide_file = QAction("Open HOW-TO-USE.md", self)
        self.act_guide_file.triggered.connect(self.show_guide_file)

        help_menu = self.menuBar().addMenu("&Help")
        help_menu.addAction(self.act_help)
        help_menu.addAction(self.act_guide_file)
        help_menu.addAction(self.act_about)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(18, 18))
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.addToolBar(toolbar)

        self.tb_photo_name = QLabel("No photo loaded")
        self.tb_photo_name.setStyleSheet("font-weight: 600; padding-left: 4px;")
        self.tb_photo_name.setMinimumWidth(180)

        self.tb_add = self._tool_button("Add photos", self.open_dialog,
                                        "Add photos (Ctrl+O)")
        self.tb_scan_device = self._tool_button(
            "Scan from scanner", self.scan_from_device,
            "Scan pages from a scanner attached to this PC (Ctrl+Shift+N)"
        )
        self.tb_detect = self._tool_button("Re-detect", self.act_detect.trigger,
                                           "Run automatic detection again (Ctrl+R)")
        self.tb_exclude = self._tool_button("Exclude", self.toggle_current_excluded,
                                            "Exclude/include the selected document (E)")
        self.tb_prev = self._tool_button("<", lambda: self.step_page(-1), "Previous document (←)")
        self.tb_next = self._tool_button(">", lambda: self.step_page(1), "Next document (→)")
        self.tb_open_folder = self._tool_button("Open folder", self.open_output_folder,
                                                 "Open the output folder")
        self.tb_help = self._tool_button("How to use", self.show_help,
                                          "Open the short user guide (F1)")
        self.tb_settings = self._tool_button("Settings", self.open_settings, "Settings (Ctrl+,)")

        toolbar.addWidget(self.tb_photo_name)
        toolbar.addSeparator()
        toolbar.addWidget(self.tb_add)
        toolbar.addWidget(self.tb_scan_device)
        toolbar.addWidget(self.tb_detect)
        toolbar.addWidget(self.tb_exclude)
        toolbar.addSeparator()
        toolbar.addWidget(self.tb_prev)
        toolbar.addWidget(self.tb_next)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)
        toolbar.addWidget(self.tb_open_folder)
        toolbar.addWidget(self.tb_help)
        toolbar.addWidget(self.tb_settings)

        self.statusBar().showMessage("Ready — add photos to begin.")

    @staticmethod
    def _tool_button(text: str, slot, tooltip: str):
        from PySide6.QtWidgets import QToolButton

        btn = QToolButton()
        btn.setText(text)
        btn.setToolTip(tooltip)
        btn.clicked.connect(slot)
        return btn

    # -------------------------------------------------------------- wiring
    def _connect(self) -> None:
        self.photo_panel.add_requested.connect(self.open_dialog)
        self.photo_panel.remove_requested.connect(self.remove_photo)
        self.photo_panel.current_changed.connect(self.select_photo)
        self.scan_bar.scan_requested.connect(self.scan_and_save)
        self.scan_bar.folder_changed.connect(self._on_folder_changed)
        self.scan_bar.mode_changed.connect(self._on_mode_changed)

        self.shortcut_left = QShortcut(QKeySequence(Qt.Key.Key_Left), self)
        self.shortcut_left.activated.connect(lambda: self.step_page(-1))
        self.shortcut_right = QShortcut(QKeySequence(Qt.Key.Key_Right), self)
        self.shortcut_right.activated.connect(lambda: self.step_page(1))
        self.shortcut_esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self.shortcut_esc.activated.connect(self._exit_preview)

    def _restore_settings(self) -> None:
        folder = self.settings.resolved_output_dir()
        try:
            folder.mkdir(parents=True, exist_ok=True)
            self.scan_bar.set_folder(folder)
        except OSError:
            self.scan_bar.set_folder(self.settings.resolved_output_dir())
        self.scan_bar.set_mode(self.settings.mode)
        self.settings.output_dir = str(folder)

    # --------------------------------------------------------------- drag
    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasImage() and not event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile() and _is_image_file(Path(url.toLocalFile())):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasImage() and not event.mimeData().hasUrls():
            image = QGuiApplication.clipboard().image()
            if not image.isNull():
                self._load_qimage(image, None)
                event.acceptProposedAction()
                return
        paths = [
            Path(url.toLocalFile())
            for url in event.mimeData().urls()
            if url.isLocalFile() and _is_image_file(Path(url.toLocalFile()))
        ]
        if paths:
            self.load_paths(paths)
            event.acceptProposedAction()

    # -------------------------------------------------------------- photos
    def open_dialog(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Choose photos of your documents",
            str(Path.home() / "Pictures") if (Path.home() / "Pictures").is_dir() else str(Path.home()),
            IMAGE_FILTER,
        )
        if paths:
            self.load_paths([Path(p) for p in paths])

    def load_paths(self, paths: list[Path]) -> None:
        loaded = 0
        for path in paths:
            try:
                image = _read_image(path)
            except Exception as exc:  # noqa: BLE001
                QMessageBox.warning(self, "Could not open image", f"{path.name}\n\n{exc}")
                continue
            if image is None:
                QMessageBox.warning(self, "Could not open image", f"{path.name} is not a readable image.")
                continue
            self._add_doc(DocPage(path=path, image=image))
            loaded += 1
        if loaded:
            self.select_photo(len(self.docs) - 1)
            self.statusBar().showMessage(
                f"Added {loaded} photo{'s' if loaded != 1 else ''}.", 4000
            )

    # ------------------------------------------------------------ scanner
    def scan_from_device(self) -> None:
        """Scan pages from a scanner, then treat them as ordinary photos."""
        from .scan_dialog import ScanDeviceDialog

        dialog = ScanDeviceDialog(self.settings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.page_files:
            from .scan_dialog import keep_for_session

            # The images sit in a temp folder this process owns; it is removed
            # when the app exits, so DocPage.path stays valid meanwhile.
            keep_for_session(dialog.page_files)
            self.load_paths([Path(p) for p in dialog.page_files])
            n = len(dialog.page_files)
            self.statusBar().showMessage(
                f"Scanned {n} page{'s' if n != 1 else ''}.", 5000
            )

    def paste_image(self) -> None:
        clip = QGuiApplication.clipboard()
        image = clip.image()
        if image.isNull():
            self.statusBar().showMessage("There is no image on the clipboard.", 4000)
            return
        self._load_qimage(image, None)

    def _load_qimage(self, image: QImage, path: Path | None) -> None:
        from .qt_image import qimage_to_ndarray

        arr = qimage_to_ndarray(image)
        if arr is None or arr.size == 0:
            self.statusBar().showMessage("The pasted image is empty.", 4000)
            return
        self._add_doc(DocPage(path=path, image=arr))
        self.select_photo(len(self.docs) - 1)
        self.statusBar().showMessage("Pasted image added.", 3000)

    def _add_doc(self, doc: DocPage) -> None:
        self.docs.append(doc)
        thumb = ndarray_to_qpixmap(_fit_thumbnail(doc.image, 80))
        self.photo_panel.add_photo(doc.name, f"{doc.size_label} pixels", thumb)
        self.empty_state.setVisible(False)

    def remove_current(self) -> None:
        self.remove_photo(self.photo_panel.current_row())

    def remove_photo(self, row: int) -> None:
        if not (0 <= row < len(self.docs)):
            return
        self.docs.pop(row)
        self.photo_panel.remove_row(row)
        if not self.docs:
            self.current_index = -1
            self._show_empty()
        else:
            self.current_index = -1  # force refresh
            self.select_photo(self.photo_panel.current_row())
        self._refresh_thumbs()

    def select_photo(self, row: int) -> None:
        if not (0 <= row < len(self.docs)):
            return
        if row == self.current_index:
            self._refresh_current_view()
            return
        self.current_index = row
        self.current_page_index = 0
        doc = self.docs[row]
        self.canvas.show_photo(doc.image, self._overlays_for(doc))
        self.empty_state.setVisible(False)
        self.tb_photo_name.setText(_elide(doc.name, 32))
        self.tb_photo_name.setToolTip(str(doc.path) if doc.path else doc.name)
        self._refresh_thumbs()
        if doc.detected:
            self._show_preview()
            self._update_ui_state()
        elif self.settings.auto_detect_on_open:
            self.detect_current()
        else:
            self.canvas.show_result(None)
            self._update_ui_state()
        self._update_ui_state()

    def _show_empty(self) -> None:
        self.canvas.show_photo_empty()
        self.canvas.show_result(None)
        self.thumbs_container.setVisible(False)
        self.empty_state.setVisible(True)
        self.empty_state.raise_()
        self.tb_photo_name.setText("No photo loaded")
        self.scan_bar.set_summary("No documents detected yet")
        self.scan_bar.set_scan_enabled(False)
        self._update_ui_state()

    def _refresh_current_view(self) -> None:
        if not (0 <= self.current_index < len(self.docs)):
            return
        doc = self.docs[self.current_index]
        self.canvas.show_photo(doc.image, self._overlays_for(doc))
        self._refresh_thumbs()
        if doc.detected:
            self._show_preview()
        self._update_ui_state()

    # ----------------------------------------------------------- detection
    def detect_current(self, force: bool = False) -> None:
        if not (0 <= self.current_index < len(self.docs)) or self._detecting:
            return
        doc = self.docs[self.current_index]
        if doc.detected and not force:
            return
        self._detecting = True
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.statusBar().showMessage(f"Detecting documents in {doc.name}…")
        self.tb_detect.setEnabled(False)
        run_detection(
            self.pool,
            doc.image,
            lambda res: self._on_detected(doc, res),
            self._on_detect_failed,
            min_confidence=self.settings.min_confidence,
        )

    def _on_detected(self, doc: DocPage, result: DetectionJobResult) -> None:
        self._detecting = False
        self.tb_detect.setEnabled(True)
        self.progress.setVisible(False)
        if not result.ok:
            self.statusBar().showMessage("Detection failed.", 6000)
            QMessageBox.warning(self, "Detection failed", result.error)
            return
        detections: list[Detection] = []
        for quad, meta in result.detections:
            detections.append(Detection(quad=quad, score=meta.get("score", 0.0),
                                        source=meta.get("source", "")))
        doc.detections = detections
        doc.detected = True
        doc.excluded.clear()
        doc.clear_results()
        self._refresh_current_view()
        n = len(detections)
        if n == 0:
            self.statusBar().showMessage(
                "No documents found — try a photo with better lighting and contrast.", 7000
            )
            QMessageBox.information(
                self,
                "No documents found",
                "SmartScan could not find a document outline in this photo.\n\n"
                "Tips:\n• Keep the whole document inside the frame\n"
                "• Use a plain, contrasting background\n"
                "• Avoid heavy shadows across the paper",
            )
        else:
            self.statusBar().showMessage(
                f"Found {n} document{'s' if n != 1 else ''} in {result.elapsed * 1000:.0f} ms.",
                5000,
            )

    def _on_detect_failed(self, error: str) -> None:
        self._detecting = False
        self.tb_detect.setEnabled(True)
        self.progress.setVisible(False)
        self.statusBar().showMessage("Detection failed.", 6000)
        QMessageBox.critical(self, "Detection failed", error)

    # ------------------------------------------------------------ scanning
    def scan_and_save(self) -> None:
        if self._scanning:
            return
        docs_with_docs = [d for d in self.docs if d.detections and d.included_quads()]
        if not docs_with_docs:
            self.statusBar().showMessage("No documents to scan yet.", 4000)
            return
        folder = Path(self.scan_bar.folder() or self.settings.resolved_output_dir())
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.critical(self, "Cannot use that folder", f"{folder}\n\n{exc}")
            return
        self._scanning = True
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.tb_detect.setEnabled(False)
        total_docs = len(docs_with_docs)
        self._scan_queue = list(docs_with_docs)
        self._scan_total = total_docs
        self._scan_done = 0
        self._scan_saved: list[Path] = []
        self._scan_errors: list[str] = []
        self.statusBar().showMessage(f"Scanning {total_docs} photo(s)…")
        self._scan_next()

    def _scan_next(self) -> None:
        if not self._scan_queue:
            self._finish_scan()
            return
        doc = self._scan_queue.pop(0)
        quads = doc.included_quads()
        run_scan(
            self.pool,
            doc.image,
            quads,
            lambda res, d=doc: self._on_scanned(d, res),
            self._on_scan_failed,
            mode=self.scan_bar.current_mode(),
        )

    def _on_scanned(self, doc: DocPage, result: ScanJobResult) -> None:
        if not result.ok:
            self._scan_errors.append(result.error)
            self._scan_next()
            return
        doc.pages = result.pages
        if doc is self._current_doc():
            self.current_page_index = 0
            self._show_preview()
        self._scan_done += 1
        self.statusBar().showMessage(
            f"Scanned {self._scan_done}/{self._scan_total} photos…"
        )
        self._scan_next()

    def _on_scan_failed(self, error: str) -> None:
        self._scan_errors.append(error)
        self._scan_next()

    def _finish_scan(self) -> None:
        self._scanning = False
        self.progress.setVisible(False)
        self.tb_detect.setEnabled(True)
        pages: list[Page] = []
        for doc in self.docs:
            pages.extend(doc.pages)
        if not pages:
            self._update_ui_state()
            msg = "Nothing could be scanned."
            if self._scan_errors:
                msg += "\n\n" + "\n".join(self._scan_errors[:3])
            QMessageBox.warning(self, "Nothing scanned", msg)
            return
        folder = Path(self.scan_bar.folder() or self.settings.resolved_output_dir())
        result = save_pages(
            pages,
            folder,
            fmt=self.settings.format,
            name_template=self.settings.name_template,
            jpeg_quality=self.settings.jpeg_quality,
            combine_pdf=self.settings.combine_pdf,
        )
        errors = list(self._scan_errors) + result.errors
        self._update_ui_state()
        if result.files:
            self._last_saved_dir = folder
            names = ", ".join(f.name for f in result.files[:3])
            if len(result.files) > 3:
                names += f" and {len(result.files) - 3} more"
            self.statusBar().showMessage(
                f"Saved {len(result.files)} file(s) to {folder}", 8000
            )
            self.scan_bar.set_summary(f"Saved to {folder.name}")
            if self.settings.open_folder_after and not errors:
                self._reveal(folder)
        if errors:
            QMessageBox.warning(
                self,
                "Some documents could not be saved",
                "\n\n".join(errors[:5]),
            )

    # ------------------------------------------------------------- preview
    def _show_preview(self) -> None:
        doc = self._current_doc()
        if doc is None:
            return
        self.canvas.set_single_view(False)
        if not doc.pages:
            self.canvas.show_result(None)
            self._update_ui_state()
            return
        idx = min(self.current_page_index, len(doc.pages) - 1)
        self.current_page_index = idx
        page = doc.pages[idx]
        self.canvas.show_result(page.image)
        self.canvas.set_result_title(f"Preview · page {idx + 1} of {len(doc.pages)}")
        self._refresh_thumbs()
        self._update_ui_state()

    def _exit_preview(self) -> None:
        self.canvas.show_result(None)
        self.canvas.set_result_title("Preview")
        self._update_ui_state()

    def _refresh_thumbs(self) -> None:
        # clear existing
        while self.thumbs_layout.count():
            item = self.thumbs_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        doc = self._current_doc()
        pages = doc.pages if doc else []
        for i, page in enumerate(pages):
            thumb = PageThumb(i, page.image)
            thumb.set_selected(i == self.current_page_index)
            thumb.set_included(i not in self._excluded_pages(doc))
            thumb.clicked.connect(self._on_thumb_clicked)
            self.thumbs_layout.addWidget(thumb)
        self.thumbs_layout.addStretch(1)
        self.thumbs_container.setVisible(bool(pages))
        self.thumbs_scroll.setVisible(bool(pages))
        self.strip_count.setText(f"{len(pages)} page{'s' if len(pages) != 1 else ''}")
        if doc is not None:
            self.strip_hint.setText(
                f"{doc.name} · {len(doc.included_quads())} of {len(doc.detections)} "
                f"document{'s' if len(doc.detections) != 1 else ''} selected"
            )

    def _excluded_pages(self, doc: DocPage | None) -> set[int]:
        return set()

    def _on_thumb_clicked(self, index: int) -> None:
        doc = self._current_doc()
        if doc is None or not doc.pages:
            return
        self.current_page_index = max(0, min(index, len(doc.pages) - 1))
        self._show_preview()

    # --------------------------------------------------------------- state
    def _update_ui_state(self) -> None:
        has_doc = self._current_doc() is not None
        doc = self._current_doc()
        has_detections = bool(doc and doc.detections)
        has_pages = bool(doc and doc.pages)
        total_pages = sum(len(d.pages) for d in self.docs)
        self.act_scan.setEnabled(total_pages > 0 and not self._scanning)
        self.act_detect.setEnabled(has_doc and not self._detecting)
        self.tb_detect.setEnabled(has_doc and not self._detecting)
        self.act_exclude.setEnabled(has_detections)
        self.tb_exclude.setEnabled(has_detections and not self._detecting)
        self.scan_bar.set_scan_enabled(total_pages > 0 and not self._scanning)
        self.tb_prev.setEnabled(False)
        self.tb_next.setEnabled(False)
        if has_pages:
            self.tb_prev.setEnabled(True)
            self.tb_next.setEnabled(True)
        if doc is not None:
            if has_pages:
                self.scan_bar.set_summary(
                    f"{total_pages} page{'s' if total_pages != 1 else ''} ready"
                )
            elif has_detections:
                n = len(doc.included_quads())
                self.scan_bar.set_summary(
                    f"{n} document{'s' if n != 1 else ''} detected — click Scan & Save"
                )
            else:
                self.scan_bar.set_summary("Detecting…" if self._detecting else "No documents detected")
        self.empty_state.setVisible(not self.docs)
        if self.empty_state.isVisible():
            self.empty_state.setGeometry(self.splitter.rect())
            self.empty_state.raise_()

    def _overlays_for(self, doc: DocPage) -> list[tuple[np.ndarray, float, bool]]:
        out = []
        for i, det in enumerate(doc.detections):
            included = i not in doc.excluded
            out.append((det.quad, 1.0 if included else 0.35, included))
        return out

    def step_page(self, delta: int) -> None:
        doc = self._current_doc()
        if doc is None:
            return
        if doc.pages and self.current_page_index + delta in range(len(doc.pages)):
            self.current_page_index += delta
            self._show_preview()
            return
        # Move between photos when at the ends of the preview strip.
        if self.docs and len(self.docs) > 1:
            row = (self.photo_panel.current_row() + delta) % len(self.docs)
            self.photo_panel.set_current(row)

    def toggle_current_excluded(self) -> None:
        doc = self._current_doc()
        if doc is None or not doc.detections:
            return
        if not doc.pages:
            # Before scanning: nothing to exclude yet.
            self.statusBar().showMessage(
                "Scan the documents first, then you can exclude pages.", 4000
            )
            return
        idx = self.current_page_index
        doc.toggle_excluded(idx)
        self._refresh_thumbs()
        self.canvas.show_photo(doc.image, self._overlays_for(doc))
        n = len(doc.included_quads())
        self.statusBar().showMessage("Page excluded." if idx in doc.excluded else "Page included.", 2500)
        self._update_ui_state()

    def _current_doc(self) -> DocPage | None:
        if 0 <= self.current_index < len(self.docs):
            return self.docs[self.current_index]
        return None

    # ------------------------------------------------------------- folders
    def _on_folder_changed(self, folder: str) -> None:
        self.settings.output_dir = folder
        save_settings(self.settings)
        self.statusBar().showMessage(f"Scans will be saved to {folder}", 4000)

    def _on_mode_changed(self, mode: str) -> None:
        self.settings.mode = mode
        save_settings(self.settings)
        doc = self._current_doc()
        if doc is not None:
            doc.clear_results()
        self._refresh_thumbs()
        self.canvas.show_result(None)
        self._update_ui_state()

    def open_output_folder(self) -> None:
        folder = Path(self.scan_bar.folder() or self.settings.resolved_output_dir())
        folder.mkdir(parents=True, exist_ok=True)
        self._reveal(folder)

    def _reveal(self, folder: Path) -> None:
        try:
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices

            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
        except Exception:  # noqa: BLE001
            self.statusBar().showMessage(f"Folder: {folder}", 6000)

    # --------------------------------------------------------- dialogs
    def open_settings(self) -> None:
        from .settings_dialog import SettingsDialog

        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            dialog.apply_to(self.settings)
            save_settings(self.settings)
            self.scan_bar.set_folder(self.settings.resolved_output_dir())
            self.scan_bar.set_mode(self.settings.mode)
            self.statusBar().showMessage("Settings saved.", 3000)

    def show_help(self) -> None:
        from .help_dialog import HelpDialog

        dialog = HelpDialog(self)
        dialog.exec()

    def show_guide_file(self) -> None:
        """Open HOW-TO-USE.md in the user's editor / browser."""
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        from .help_dialog import bundled_guide_dir

        base = bundled_guide_dir()
        if base is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(base / "HOW-TO-USE.md")))
        else:
            self.show_help()

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            "About SmartScan",
            "<h3>SmartScan</h3>"
            "<p>Scan several small documents from one photo.</p>"
            "<p>Automatic document detection, straightening and cleanup, "
            "with a preview before saving.</p>"
            "<p style='color:#6b7280'>Built with Python, Qt and OpenCV.</p>",
        )

    # --------------------------------------------------------------- close
    def closeEvent(self, event) -> None:  # noqa: N802
        self.settings.output_dir = self.scan_bar.folder()
        save_settings(self.settings)
        self.pool.clear()
        super().closeEvent(event)


# ---------------------------------------------------------------- helpers
def _read_image(path: Path) -> np.ndarray | None:
    import cv2

    data = np.fromfile(str(path), dtype=np.uint8)
    if data.size == 0:
        return None
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    return img


def _is_image_file(path: Path) -> bool:
    return path.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}


def _fit_thumbnail(image: np.ndarray, side: int) -> np.ndarray:
    import cv2

    h, w = image.shape[:2]
    scale = side / float(max(h, w))
    return cv2.resize(image, (max(1, int(w * scale)), max(1, int(h * scale))),
                      interpolation=cv2.INTER_AREA)


def _elide(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    keep = max(4, limit - 1)
    return text[:keep] + "…"
