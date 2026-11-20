"""Page thumbnail widget for the preview strip."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from . import theme
from .qt_image import ndarray_to_qimage


class PageThumb(QWidget):
    """A single scanned-page card: image, index badge, optional exclude state."""

    clicked = Signal(int)

    def __init__(self, index: int, image: np.ndarray, parent: QWidget | None = None):
        super().__init__(parent)
        self.index = index
        self._qimage: QImage = ndarray_to_qimage(image)
        self._pixmap: QPixmap | None = None
        self.selected = False
        self.included = True
        self.source_note = ""
        self.setFixedSize(QSize(132, 188))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(
            f"Page {index + 1} - click to preview, double-click to exclude/include"
        )

    def set_image(self, image: np.ndarray) -> None:
        self._qimage = ndarray_to_qimage(image)
        self._pixmap = None
        self.update()

    def set_selected(self, selected: bool) -> None:
        if selected != self.selected:
            self.selected = selected
            self.update()

    def set_included(self, included: bool) -> None:
        if included != self.included:
            self.included = included
            self.update()

    def sizeHint(self) -> QSize:  # noqa: N802 (Qt naming)
        return QSize(132, 188)

    def _thumb(self, box: QRectF) -> QPixmap:
        if self._pixmap is None or self._pixmap.width() < int(box.width()):
            self._pixmap = QPixmap.fromImage(
                self._qimage.scaled(
                    int(box.width() * 2),
                    int(box.height() * 2),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        return self._pixmap

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        outer = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
        radius = 8.0

        # Card background
        card = QPainterPath()
        card.addRoundedRect(outer, radius, radius)
        painter.fillPath(card, QColor(theme.PANEL))

        # Page image inside with its own rounded clip
        inner = outer.adjusted(7, 7, -7, -26)
        page_path = QPainterPath()
        page_path.addRoundedRect(inner, 4, 4)
        painter.save()
        painter.setClipPath(page_path)
        painter.fillPath(page_path, QColor("#f7f7f5"))
        pm = self._thumb(inner)
        if not pm.isNull():
            scaled = pm.size().scaled(inner.size().toSize(), Qt.AspectRatioMode.KeepAspectRatio)
            x = inner.x() + (inner.width() - scaled.width()) / 2
            y = inner.y() + (inner.height() - scaled.height()) / 2
            painter.drawPixmap(int(x), int(y), pm.scaled(
                scaled, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            ))
        painter.restore()

        # Page border
        pen = QPen(QColor("#d9dde5"), 1)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(page_path)

        if not self.included:
            painter.fillPath(page_path, QColor(255, 255, 255, 170))
            painter.setPen(QPen(QColor(theme.DANGER), 2))
            painter.drawLine(inner.topLeft(), inner.bottomRight())
            painter.drawLine(inner.topRight(), inner.bottomLeft())

        # Caption
        painter.setPen(QColor(theme.TEXT_MUTED))
        font = QFont(self.font())
        font.setPointSizeF(max(7.5, font.pointSizeF() - 1.5))
        painter.setFont(font)
        caption = f"Page {self.index + 1}"
        if not self.included:
            caption += "  (excluded)"
        painter.drawText(
            QRectF(outer.x() + 8, outer.bottom() - 22, outer.width() - 16, 18),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            caption,
        )

        # Selection ring
        if self.selected:
            pen = QPen(QColor(theme.ACCENT), 2.2)
            painter.setPen(pen)
            painter.drawRoundedRect(outer, radius, radius)
        else:
            painter.setPen(QPen(QColor(theme.BORDER), 1))
            painter.drawRoundedRect(outer, radius, radius)
        painter.end()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.index)
        super().mousePressEvent(event)
