"""Qt-facing image conversion helpers."""

from __future__ import annotations

import numpy as np
from PySide6.QtGui import QImage, QPixmap


def ndarray_to_qimage(image: np.ndarray) -> QImage:
    """Convert a BGR / BGRA / gray numpy array to a deep-copied QImage."""
    if image is None:
        return QImage()
    if image.dtype != np.uint8:
        image = np.clip(image, 0, 255).astype(np.uint8)
    image = np.ascontiguousarray(image)
    h, w = image.shape[:2]
    if image.ndim == 2:
        fmt = QImage.Format.Format_Grayscale8
        bytes_per_line = w
        data = image.data
    elif image.shape[2] == 4:
        fmt = QImage.Format.Format_ARGB32
        bytes_per_line = w * 4
        data = image.data
    else:
        fmt = QImage.Format.Format_BGR888
        bytes_per_line = w * 3
        data = image.data
    qimage = QImage(data, w, h, bytes_per_line, fmt)
    # QImage does not take ownership of the buffer: copy before returning.
    return qimage.copy()


def ndarray_to_qpixmap(image: np.ndarray) -> QPixmap:
    return QPixmap.fromImage(ndarray_to_qimage(image))


def qpixmap_to_ndarray(pixmap: QPixmap) -> np.ndarray:
    image = pixmap.toImage().convertToFormat(QImage.Format.Format_RGB888)
    w, h = image.width(), image.height()
    ptr = image.constBits()
    arr = np.frombuffer(ptr, np.uint8, count=image.sizeInBytes())
    arr = arr.reshape((h, image.bytesPerLine()))[:, : w * 3].reshape(h, w, 3)
    return np.ascontiguousarray(arr[:, :, ::-1])  # RGB -> BGR


def qimage_to_ndarray(image: QImage) -> np.ndarray | None:
    """Convert a QImage (e.g. from the clipboard) to a BGR numpy array."""
    if image is None or image.isNull():
        return None
    image = image.convertToFormat(QImage.Format.Format_RGB888)
    w, h = image.width(), image.height()
    if w == 0 or h == 0:
        return None
    ptr = image.constBits()
    arr = np.frombuffer(ptr, np.uint8, count=image.sizeInBytes())
    arr = arr.reshape((h, image.bytesPerLine()))[:, : w * 3].reshape(h, w, 3)
    return np.ascontiguousarray(arr[:, :, ::-1])
