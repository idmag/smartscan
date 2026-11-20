"""Perspective correction ("dewarping") of a detected document quad."""

from __future__ import annotations

import math

import numpy as np

from .imaging import _cv, order_points, quad_angles


def quad_to_image(
    image: np.ndarray,
    quad: np.ndarray,
    *,
    margin_px: int = 0,
    out_max_side: int = 2600,
    out_size: tuple[int, int] | None = None,
) -> np.ndarray:
    """Warp the *quad* region of *image* to a straight-on, upright rectangle.

    ``margin_px`` grows the quad slightly outwards (in source pixels) so the
    dark edge of the paper is not cut off.  ``out_size`` gives an explicit
    output size ``(width, height)``; otherwise one is derived from the measured
    quad, capped at ``out_max_side``.  Crucially, only the **destination** is
    ever resized for aspect correction: scaling the source quad would pull
    background pixels into the page.
    """
    cv2 = _cv()
    quad = order_points(quad).astype(np.float32)

    width = max(
        (float(np.linalg.norm(quad[1] - quad[0])) + float(np.linalg.norm(quad[2] - quad[3]))) / 2.0,
        1.0,
    )
    height = max(
        (float(np.linalg.norm(quad[3] - quad[0])) + float(np.linalg.norm(quad[2] - quad[1]))) / 2.0,
        1.0,
    )

    # Grow the quad outwards for a safety margin (about the centroid).
    if margin_px > 0:
        center = quad.mean(axis=0)
        grow = np.array(
            [(width + 2.0 * margin_px) / width, (height + 2.0 * margin_px) / height], np.float32
        )
        quad = (quad - center) * grow + center
        width += 2.0 * margin_px
        height += 2.0 * margin_px

    if out_size is not None:
        out_w, out_h = max(1, int(out_size[0])), max(1, int(out_size[1]))
    else:
        longest = max(width, height)
        scale = min(1.0, out_max_side / longest) if longest > 0 else 1.0
        out_w = max(1, int(round(width * scale)))
        out_h = max(1, int(round(height * scale)))

    dst = np.array(
        [[0, 0], [out_w - 1, 0], [out_w - 1, out_h - 1], [0, out_h - 1]], dtype=np.float32
    )
    matrix = cv2.getPerspectiveTransform(quad, dst)
    warped = cv2.warpPerspective(
        image,
        matrix,
        (out_w, out_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return warped


def looks_sideways(image: np.ndarray) -> bool:
    """Heuristic: is the *text* in this dewarped image rotated 90/270 degrees?

    Text lines create strong horizontal gradients; a sideways page has its
    energy concentrated in vertical gradients instead.  Robust enough for
    book pages, forms and receipts, and harmless for photos of drawings.
    """
    cv2 = _cv()
    from .imaging import to_gray

    gray = to_gray(image)
    h, w = gray.shape
    if min(h, w) < 40:
        return False
    scale = 600.0 / max(h, w)
    if scale < 1.0:
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    # Text rows: energy changes mostly along y (horizontal strokes stacked).
    horizontal = float(np.mean(np.abs(gy)))
    vertical = float(np.mean(np.abs(gx)))
    if horizontal + vertical < 1e-3:
        return False
    return vertical > horizontal * 1.35


def rotate_to_portrait_if_needed(image: np.ndarray) -> np.ndarray:
    """Upright a sideways document while keeping landscape content landscape."""
    cv2 = _cv()
    h, w = image.shape[:2]
    if h == 0 or w == 0:
        return image
    aspect = h / float(w)
    # Only consider rotation for portrait-ish pages; a wide receipt strip or a
    # landscape photo of a sketch should stay as it is.
    if aspect >= 1.25 or looks_sideways(image):
        rotated = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        if rotated.shape[0] > rotated.shape[1] and aspect < 1.25:
            # Sideways content on a portrait crop: decide by which orientation
            # makes the text lines horizontal.
            if looks_sideways(rotated):
                return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
            return rotated
        if looks_sideways(image):
            return rotated
    return image


def auto_upright(image: np.ndarray) -> np.ndarray:
    """Rotate a sideways page upright, without harming normal documents.

    Only landscape-ish crops whose *text* runs vertically are rotated; portrait
    pages and drawings (which have no dominant text direction) are untouched.
    This is deliberately conservative: a wrongly rotated scan is far worse than
    an upside-down one, which the user can see in the preview.
    """
    cv2 = _cv()
    h, w = image.shape[:2]
    if h <= 0 or w <= 0:
        return image
    if h >= w * 1.03:
        return image  # already portrait
    if not looks_sideways(image):
        return image
    rotated = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    return rotated


def estimate_paper_aspect(width: float, height: float, angle_deg: float = 0.0) -> float | None:
    """Guess the most likely paper aspect ratio for a quad's dimensions.

    Returns height/width, or ``None`` when the shape does not resemble a known
    paper (then the measured ratio is kept).
    """
    if width <= 1 or height <= 1:
        return None
    ratio = height / width
    if ratio < 1.0:
        ratio = 1.0 / ratio
    known = [
        ("A4", 297 / 210),
        ("Letter", 279.4 / 215.9),
        ("A5", 210 / 148),
        ("Legal", 355.6 / 215.9),
        ("receipt", 3.2),
        ("card", 85.6 / 53.98),
    ]
    best = None
    best_err = float("inf")
    for _name, value in known:
        err = abs(math.log(ratio / value))
        if err < best_err:
            best_err, best = err, value
    if best_err > math.log(1.18):
        return None
    return best


def quad_regularity(quad: np.ndarray) -> float:
    """0..1 score for how rectangle-like a quad is (1 = perfect rectangle)."""
    angles = quad_angles(quad)
    if not angles:
        return 0.0
    err = max(abs(a - 90.0) for a in angles)
    return float(max(0.0, 1.0 - err / 45.0))
