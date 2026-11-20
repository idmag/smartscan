"""Left-hand panel: list of loaded photos with tiny previews."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import theme


def _placeholder_icon(size: int = 40) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#e8edf5"))
    painter.drawRoundedRect(0, 0, size, size, 6, 6)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#9aa4b5"))
    cy = size // 2
    for dx in (-size * 0.17, 0, size * 0.17):
        painter.drawEllipse(QPointF(size / 2 + dx, cy), size * 0.055, size * 0.055)
    painter.end()
    return QIcon(pm)


# Where a page came from, shown next to its name: a scan and a photo need
# different advice when nothing is found, and the list keeps that visible.
_SOURCE_LABELS = {
    "scan": "scanner",
    "clipboard": "clipboard",
    "photo": "",
}


class PhotoPanel(QWidget):
    """Thumbnail list + add/remove buttons."""

    add_requested = Signal()
    remove_requested = Signal(int)
    current_changed = Signal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumWidth(210)
        self.setMaximumWidth(320)

        title = QLabel("Photos")
        title.setProperty("heading", True)
        count = QLabel("0")
        count.setProperty("pill", True)
        self.count_label = count

        header = QHBoxLayout()
        header.setContentsMargins(2, 0, 2, 0)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(count)

        self.list = QListWidget()
        self.list.setIconSize(QSize(40, 40))
        self.list.setSpacing(2)
        self.list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.list.currentRowChanged.connect(self._on_row_changed)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        add_btn = QPushButton("Add photos…")
        add_btn.setProperty("variant", "primary")
        add_btn.clicked.connect(self.add_requested)
        self.add_button = add_btn

        remove_btn = QPushButton("Remove")
        remove_btn.setProperty("flat", "true")
        remove_btn.setToolTip("Remove the selected photo (Delete)")
        remove_btn.clicked.connect(self._emit_remove)
        self.remove_button = remove_btn

        buttons = QHBoxLayout()
        buttons.setSpacing(6)
        buttons.addWidget(add_btn, 1)
        buttons.addWidget(remove_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 12, 10, 12)
        layout.setSpacing(10)
        layout.addLayout(header)
        layout.addWidget(self.list, 1)
        layout.addLayout(buttons)

        self._placeholder = _placeholder_icon()

    def _emit_remove(self) -> None:
        row = self.list.currentRow()
        if row >= 0:
            self.remove_requested.emit(row)

    def add_photo(self, name: str, detail: str, thumb: QPixmap | None = None,
                  *, origin: str = "photo") -> None:
        source = _SOURCE_LABELS.get(origin, "")
        item = QListWidgetItem(f"{name}   {source}" if source else name)
        item.setToolTip(f"{name} ({source})\n{detail}" if source else f"{name}\n{detail}")
        item.setData(Qt.ItemDataRole.UserRole, origin)
        if thumb is not None and not thumb.isNull():
            item.setIcon(QIcon(thumb))
        else:
            item.setIcon(self._placeholder)
        item.setSizeHint(QSize(0, 50))
        self.list.addItem(item)
        self.count_label.setText(str(self.list.count()))
        if self.list.currentRow() < 0:
            self.list.setCurrentRow(0)

    def set_photo_thumbnail(self, row: int, pixmap: QPixmap) -> None:
        item = self.list.item(row)
        if item is not None and not pixmap.isNull():
            item.setIcon(QIcon(pixmap))

    def clear(self) -> None:
        self.list.clear()
        self.count_label.setText("0")

    def remove_row(self, row: int) -> None:
        if 0 <= row < self.list.count():
            self.list.takeItem(row)
            self.count_label.setText(str(self.list.count()))
            if self.list.count():
                self.list.setCurrentRow(min(row, self.list.count() - 1))

    def set_current(self, row: int) -> None:
        if 0 <= row < self.list.count():
            self.list.setCurrentRow(row)

    def current_row(self) -> int:
        return self.list.currentRow()

    def count(self) -> int:
        return self.list.count()

    def _on_row_changed(self, row: int) -> None:
        self.current_changed.emit(row)

    def set_busy(self, busy: bool) -> None:
        self.add_button.setEnabled(not busy)
