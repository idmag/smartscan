"""Interactive canvas: shows the photo, detected document outlines and the
final scanned page side by side (or one at a time)."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from . import theme
from .qt_image import ndarray_to_qimage


class _ImagePane(QWidget):
    """Draws an image scaled to fit, with a title chip and an optional overlay."""

    clicked = Signal()

    def __init__(self, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.title = title
        self._image: QImage | None = None
        self._pixmap: QPixmap | None = None
        self._overlays: list[tuple[np.ndarray, float, bool]] = []
        self.placeholder = "No image yet"
        self.setMinimumSize(180, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    # -- data --------------------------------------------------------------
    def set_image(self, image: np.ndarray | None) -> None:
        self._image = ndarray_to_qimage(image) if image is not None else None
        self._pixmap = None
        self.update()

    def set_overlays(self, overlays: list[tuple[np.ndarray, float, bool]]) -> None:
        """Overlays are (quad, opacity, filled) tuples in image coordinates."""
        self._overlays = overlays
        self.update()

    def has_image(self) -> bool:
        return self._image is not None

    # -- painting ----------------------------------------------------------
    def _content_rect(self) -> QRectF:
        return QRectF(self.rect()).adjusted(14, 40, -14, -14)

    def _image_rect(self) -> QRectF:
        rect = self._content_rect()
        if self._image is None or self._image.isNull():
            return rect
        iw, ih = self._image.width(), self._image.height()
        scale = min(rect.width() / iw, rect.height() / ih)
        w, h = iw * scale, ih * scale
        return QRectF(
            rect.x() + (rect.width() - w) / 2,
            rect.y() + (rect.height() - h) / 2,
            w,
            h,
        )

    def _scaled_pixmap(self) -> QPixmap | None:
        if self._image is None or self._image.isNull():
            return None
        rect = self._image_rect()
        target = rect.size().toSize()
        if target.width() <= 0 or target.height() <= 0:
            return None
        dpr = self.devicePixelRatioF()
        target = target * dpr
        if (
            self._pixmap is None
            or self._pixmap.width() < target.width() - 2
            or self._pixmap.height() < target.height() - 2
        ):
            self._pixmap = QPixmap.fromImage(
                self._image.scaled(
                    target,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            self._pixmap.setDevicePixelRatio(dpr)
        return self._pixmap

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        outer = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(outer, 10, 10)
        painter.fillPath(path, QColor("#fbfbfc"))
        painter.setPen(QPen(QColor(theme.BORDER), 1))
        painter.drawPath(path)

        # Header chip
        chip_font = QFont(self.font())
        chip_font.setPointSizeF(max(8.0, chip_font.pointSizeF() - 1))
        chip_font.setBold(True)
        painter.setFont(chip_font)
        metrics = painter.fontMetrics()
        text_w = metrics.horizontalAdvance(self.title.upper()) + 18
        chip = QRectF(outer.x() + 12, outer.y() + 10, text_w, 20)
        chip_path = QPainterPath()
        chip_path.addRoundedRect(chip, 9, 9)
        painter.fillPath(chip_path, QColor("#eef1f6"))
        painter.setPen(QColor(theme.TEXT_MUTED))
        painter.drawText(chip, Qt.AlignmentFlag.AlignCenter, self.title.upper())

        if self._image is None:
            painter.setPen(QColor("#9aa1ad"))
            body = QFont(self.font())
            body.setPointSizeF(max(9.0, body.pointSizeF()))
            painter.setFont(body)
            painter.drawText(
                self._content_rect(),
                Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                self.placeholder,
            )
            painter.end()
            return

        image_rect = self._image_rect()
        # Soft shadow
        shadow = image_rect.adjusted(3, 4, 3, 4)
        shadow_path = QPainterPath()
        shadow_path.addRoundedRect(shadow, 3, 3)
        painter.fillPath(shadow_path, QColor(15, 23, 42, 22))

        pm = self._scaled_pixmap()
        if pm is not None:
            painter.drawPixmap(image_rect.topLeft(), pm)

        if self._overlays:
            self._paint_overlays(painter, image_rect)

        painter.setPen(QPen(QColor(0, 0, 0, 30), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(shadow_path)
        painter.end()

    def _paint_overlays(self, painter: QPainter, image_rect: QRectF) -> None:
        if self._image is None:
            return
        iw, ih = self._image.width(), self._image.height()
        sx = image_rect.width() / iw
        sy = image_rect.height() / ih
        ox, oy = image_rect.x(), image_rect.y()
        for quad, opacity, filled in self._overlays:
            pts = [QPointF(ox + float(p[0]) * sx, oy + float(p[1]) * sy) for p in quad]
            path = QPainterPath(pts[0])
            for p in pts[1:]:
                path.lineTo(p)
            path.closeSubpath()
            if filled:
                painter.fillPath(path, QColor(37, 99, 235, 34))
            pen = QPen(QColor(37, 99, 235, int(235 * opacity)), 2.4)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)
            # Corner dots make the detection look "selected"
            painter.setBrush(QColor(255, 255, 255))
            painter.setPen(QPen(QColor(37, 99, 235, int(235 * opacity)), 2))
            for p in pts:
                painter.drawEllipse(p, 3.4, 3.4)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def resizeEvent(self, event) -> None:  # noqa: N802
        self._pixmap = None
        super().resizeEvent(event)


class PreviewCanvas(QWidget):
    """Two panes: the source photo with detected outlines, and the scan result."""

    page_selected = Signal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.photo_pane = _ImagePane("Original")
        self.result_pane = _ImagePane("Preview")
        self.photo_pane.placeholder = (
            "Add photos of your documents\n\n"
            "Drag & drop images here, paste from the\n"
            "clipboard (Ctrl+V) or click “Add photos”."
        )
        self.result_pane.placeholder = (
            "Detected documents appear here\n\n"
            "Adjust corners on the left, then\nclick “Scan documents”."
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 10)
        layout.setSpacing(12)
        layout.addWidget(self.photo_pane, 1)
        layout.addWidget(self.result_pane, 1)

        self._single = False
        self.result_pane.show()

    def set_single_view(self, single: bool) -> None:
        """Show only the preview pane (useful on small screens)."""
        self._single = single
        self.photo_pane.setVisible(not single)
        self.result_pane.setVisible(True)

    def show_photo(self, image: np.ndarray, overlays: list | None = None) -> None:
        self.photo_pane.set_image(image)
        self.photo_pane.set_overlays(overlays or [])

    def show_photo_empty(self, text: str | None = None) -> None:
        if text:
            self.photo_pane.placeholder = text
        self.photo_pane.set_image(None)

    def show_result(self, image: np.ndarray | None) -> None:
        self.result_pane.set_image(image)
        if image is not None:
            self.result_pane.show()
            self.photo_pane.show()

    def show_overlay(self, overlay: np.ndarray | None) -> None:
        self.photo_pane.set_image(overlay)

    def set_result_title(self, title: str) -> None:
        self.result_pane.title = title
        self.result_pane.update()
