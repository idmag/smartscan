"""Image enhancement modes used after dewarping.

The goal is "looks like a flatbed scanner": even background, crisp dark text,
good contrast.  We avoid heavy binarisation (users want to keep photos,
signatures and colour stamps intact) and instead implement a few sensible
modes with a shared, well-tested core.
"""

from __future__ import annotations

import numpy as np

from .imaging import _cv, normalize_illumination, to_gray

# Public mode identifiers.  The UI shows a human label for each of these.
MODE_ORIGINAL = "original"
MODE_COLOR = "color"          # colour-corrected, gentle background cleanup
MODE_GRAY = "gray"            # scanner-like grayscale
MODE_BW = "bw"                # high contrast black & white (text documents)
MODE_MAGIC = "magic"          # adaptive: colour for photos, gray for text

MODES = (MODE_ORIGINAL, MODE_COLOR, MODE_GRAY, MODE_BW, MODE_MAGIC)

MODE_LABELS = {
    MODE_ORIGINAL: "Original",
    MODE_COLOR: "Color",
    MODE_GRAY: "Gray",
    MODE_BW: "B&W",
    MODE_MAGIC: "Auto",
}


def enhance(image: np.ndarray, mode: str = MODE_MAGIC) -> np.ndarray:
    """Return an enhanced 3-channel (BGR) copy of *image*."""
    cv2 = _cv()
    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif image.shape[2] == 4:
        image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)

    if mode == MODE_ORIGINAL:
        return image.copy()
    if mode == MODE_MAGIC:
        mode = MODE_COLOR if is_color_content(image) else MODE_GRAY
    if mode == MODE_COLOR:
        return _enhance_color(image)
    if mode == MODE_GRAY:
        return _enhance_gray(image)
    if mode == MODE_BW:
        return _enhance_bw(image)
    raise ValueError(f"Unknown enhancement mode: {mode!r}")


def is_color_content(image: np.ndarray) -> bool:
    """Detect whether the page has meaningful colour (photo, stamp, highlighter)."""
    cv2 = _cv()
    if image.ndim != 3 or image.shape[2] < 3:
        return False
    small = cv2.resize(image, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    sat = hsv[:, :, 1].astype(np.float32) / 255.0
    val = hsv[:, :, 2].astype(np.float32) / 255.0
    # Only count reasonably bright, clearly saturated pixels; JPEG noise and
    # slight paper tint have low saturation.
    mask = (sat > 0.22) & (val > 0.20)
    return float(mask.mean()) > 0.012


def _enhance_color(image: np.ndarray) -> np.ndarray:
    cv2 = _cv()
    # 1. Remove colour casts / paper tint with a white-balance pass.
    balanced = gray_world_white_balance(image, strength=0.65)
    # 2. Even out lighting softly (keep colour, only tame shadows).
    lab = cv2.cvtColor(balanced, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l_flat = normalize_illumination(l, strength=0.55)
    l_flat = cv2.createCLAHE(clipLimit=1.6, tileGridSize=(8, 8)).apply(l_flat)
    out = cv2.cvtColor(cv2.merge([l_flat, a, b]), cv2.COLOR_LAB2BGR)
    # 3. Mild unsharp mask so text stays readable.
    return unsharp_mask(out, amount=0.55, radius=1.2)


def _enhance_gray(image: np.ndarray) -> np.ndarray:
    cv2 = _cv()
    gray = to_gray(image)
    gray = normalize_illumination(gray, strength=1.0)
    gray = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8)).apply(gray)
    gray = unsharp_mask(gray, amount=0.9, radius=1.0)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def _enhance_bw(image: np.ndarray) -> np.ndarray:
    cv2 = _cv()
    gray = to_gray(image)
    gray = normalize_illumination(gray, strength=1.0)
    gray = cv2.bilateralFilter(gray, 5, 45, 45)
    # Choose a threshold that sits between the paper and the ink peaks.
    threshold = _otsu_threshold(gray)
    threshold = max(threshold, int(gray.mean() * 0.82))
    _, bw = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
    return cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR)


def _otsu_threshold(gray: np.ndarray) -> int:
    cv2 = _cv()
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).ravel()
    total = gray.size
    if total == 0:
        return 128
    sum_all = float(np.dot(np.arange(256), hist))
    sum_b = 0.0
    w_b = 0.0
    best_var = -1.0
    best_t = 128
    for t in range(256):
        w_b += hist[t]
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break
        sum_b += t * hist[t]
        mean_b = sum_b / w_b
        mean_f = (sum_all - sum_b) / w_f
        var = w_b * w_f * (mean_b - mean_f) ** 2
        if var > best_var:
            best_var = var
            best_t = t
    return best_t


def gray_world_white_balance(image: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """Simple gray-world balance; *strength* blends between input and result."""
    if strength <= 0:
        return image
    b, g, r = (image[:, :, i].astype(np.float32) for i in range(3))
    means = np.array([b.mean(), g.mean(), r.mean()], dtype=np.float32)
    means[means < 1e-3] = 1.0
    gain = means.mean() / means
    gain = np.clip(gain, 0.7, 1.4)
    gain = 1.0 + (gain - 1.0) * strength
    out = image.astype(np.float32) * gain.reshape(1, 1, 3)
    return np.clip(out, 0, 255).astype(np.uint8)


def unsharp_mask(image: np.ndarray, amount: float = 0.6, radius: float = 1.0) -> np.ndarray:
    cv2 = _cv()
    k = max(3, int(round(radius * 4)) | 1)
    blurred = cv2.GaussianBlur(image, (k, k), radius)
    out = cv2.addWeighted(image, 1.0 + amount, blurred, -amount, 0)
    return out
