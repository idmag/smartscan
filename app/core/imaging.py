"""Small array/image helpers shared by the detection and enhancement code.

Everything in ``app.core`` is deliberately free of Qt and of any Windows API so
that it can be unit-tested on any platform (including CI machines).
"""

from __future__ import annotations

import math
from typing import Iterable

import numpy as np


def to_gray(image: np.ndarray) -> np.ndarray:
    """Return an 8-bit single channel view of *image* (BGR or gray)."""
    if image.ndim == 2:
        gray = image
    elif image.ndim == 3 and image.shape[2] == 1:
        gray = image[:, :, 0]
    else:
        if image.shape[2] == 4:
            image = image[:, :, :3]
        # BGR weights (OpenCV images are BGR).
        gray = (
            0.114 * image[:, :, 0]
            + 0.587 * image[:, :, 1]
            + 0.299 * image[:, :, 2]
        )
    if gray.dtype != np.uint8:
        gray = np.clip(gray, 0, 255).astype(np.uint8)
    return gray


def normalize_illumination(gray: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """Flatten uneven lighting ("divide by background").

    The background is estimated with a large *morphological closing*: dilating
    then eroding removes dark ink (text, stamps) while preserving the slow
    brightness gradient we want to cancel.  (*Opening* would do the opposite:
    it eats the white paper between text lines and wrecks the page.)
    """
    if strength <= 0:
        return gray
    cv2 = _cv()
    h, w = gray.shape
    short = min(h, w)
    # Estimate on a downscaled copy: much faster and smoother.
    scale = min(1.0, 480.0 / max(short, 1))
    small = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) \
        if scale < 1.0 else gray
    sh, sw = small.shape
    # Kernel must be wider than text line spacing to erase the text.
    k = int(max(9, round(min(sh, sw) / 12.0)) | 1)
    k = min(k, 61)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
    background_small = cv2.morphologyEx(small, cv2.MORPH_CLOSE, kernel)
    background_small = cv2.GaussianBlur(background_small, (0, 0), max(1.0, k / 4.0))
    if scale < 1.0:
        background = cv2.resize(background_small, (w, h), interpolation=cv2.INTER_LINEAR)
    else:
        background = background_small

    bg = background.astype(np.float32)
    bg = np.clip(bg, 24.0, 255.0)
    mean = float(bg.mean())
    flat = gray.astype(np.float32) / bg * mean
    flat = np.clip(flat, 0, 255)
    if strength >= 1.0:
        return flat.astype(np.uint8)
    out = gray.astype(np.float32) * (1.0 - strength) + flat * strength
    return np.clip(out, 0, 255).astype(np.uint8)


def order_points(pts: Iterable[Iterable[float]]) -> np.ndarray:
    """Order four points as top-left, top-right, bottom-right, bottom-left."""
    pts = np.asarray(pts, dtype=np.float32).reshape(4, 2)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()  # y - x
    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmin(d)]
    bl = pts[np.argmax(d)]
    return np.array([tl, tr, br, bl], dtype=np.float32)


def quad_area(pts: np.ndarray) -> float:
    """Absolute area of a convex quad, shoelace formula."""
    x = pts[:, 0]
    y = pts[:, 1]
    return 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def quad_angles(pts: np.ndarray) -> list[float]:
    """Interior angles (degrees) of a quad in point order."""
    n = len(pts)
    angles = []
    for i in range(n):
        a = pts[(i - 1) % n]
        b = pts[i]
        c = pts[(i + 1) % n]
        v1 = a - b
        v2 = c - b
        denom = (np.linalg.norm(v1) * np.linalg.norm(v2)) or 1e-6
        cosang = float(np.clip(np.dot(v1, v2) / denom, -1.0, 1.0))
        angles.append(math.degrees(math.acos(cosang)))
    return angles


def resize_max(image: np.ndarray, max_side: int) -> tuple[np.ndarray, float]:
    """Downscale so the longest side is at most *max_side*.

    Returns ``(image, scale)`` where ``scale`` maps working -> original pixels.
    """
    h, w = image.shape[:2]
    longest = max(h, w)
    if longest <= max_side:
        return image, 1.0
    scale = max_side / float(longest)
    cv2 = _cv()
    out = cv2.resize(
        image, (int(round(w * scale)), int(round(h * scale))), interpolation=cv2.INTER_AREA
    )
    return out, scale


def rotate_bound(image: np.ndarray, angle: float, border_value: int | tuple = 255) -> np.ndarray:
    """Rotate *image* by *angle* degrees without cropping (white fill by default)."""
    cv2 = _cv()
    h, w = image.shape[:2]
    cx, cy = w / 2.0, h / 2.0
    m = cv2.getRotationMatrix2D((cx, cy), angle, 1.0)
    cos = abs(m[0, 0])
    sin = abs(m[0, 1])
    nw = int(round(h * sin + w * cos))
    nh = int(round(h * cos + w * sin))
    m[0, 2] += nw / 2.0 - cx
    m[1, 2] += nh / 2.0 - cy
    return cv2.warpAffine(
        image,
        m,
        (nw, nh),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=border_value,
    )


def _cv_import():
    """Import OpenCV lazily and raise a helpful error if it is missing."""
    try:
        import cv2
    except Exception as exc:  # pragma: no cover - environment problem
        raise RuntimeError(
            "OpenCV is required for SmartScan. Install it with: pip install opencv-python-headless"
        ) from exc
    return cv2


def _cv():
    """Name used throughout the package."""
    return _cv_import()
