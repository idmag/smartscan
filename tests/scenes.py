"""Deterministic synthetic photo generator for detector tests.

Renders documents with real text at known page shapes, perspective-warps them
onto textured backgrounds, and returns ground-truth quads.  Everything is
seeded so failures are reproducible.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
PAPER_SHAPES = {
    # ``px`` is the rendered page size, ``mm`` the real paper width.  Scenes use
    # ``mm`` to keep every document at a consistent physical scale.
    "a5": (420, 595),
    "a6": (298, 420),
    "receipt": (200, 640),
    "card": (340, 214),
    "letter": (612, 792),
}
PAPER_MM = {"a5": 148.0, "a6": 105.0, "receipt": 80.0, "card": 85.6, "letter": 215.9}


@dataclass
class Scene:
    image: np.ndarray
    quads: list[np.ndarray]  # ground truth, in image coordinates


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "DejaVuSerif-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(f"{FONT_DIR}/{name}", size)


LOREM = (
    "INVOICE  No. 2024-1138",
    "Date: 14 March 2024   Due: 14 April 2024",
    "",
    "Item                  Qty      Price     Total",
    "Consulting hours       12      85.00    1020.00",
    "Travel expenses         1     140.00     140.00",
    "Software licence        2      49.99      99.98",
    "",
    "Subtotal                               1259.98",
    "VAT (20%)                               251.99",
    "TOTAL                                  1511.97",
    "",
    "Payment within 30 days to account",
    "GB29 NWBK 6016 1331 9268 19.",
    "Thank you for your business.",
)


def render_page(shape: tuple[int, int], *, tint=(250, 249, 244), font_scale=1.0,
                seed=0) -> np.ndarray:
    """Render a document page with text and a table, as a BGR uint8 image."""
    w, h = shape
    rng = np.random.default_rng(seed)
    img = Image.new("RGB", (w, h), tuple(tint))
    draw = ImageDraw.Draw(img)
    margin = int(min(w, h) * 0.08)
    y = margin
    title_font = _font(max(10, int(min(w, h) * 0.055 * font_scale)), bold=True)
    body_font = _font(max(7, int(min(w, h) * 0.031 * font_scale)))
    draw.text((margin, y), LOREM[0], fill=(20, 20, 25), font=title_font)
    y += int(title_font.size * 1.8)
    draw.line([(margin, y), (w - margin, y)], fill=(60, 60, 70), width=2)
    y += int(body_font.size * 0.9)
    for line in LOREM[1:]:
        if y > h - margin - body_font.size:
            break
        draw.text((margin, y), line, fill=(35, 35, 45), font=body_font)
        y += int(body_font.size * 1.55)
    # A few hand-drawn-looking strokes and a stamp to defeat naive detectors.
    for _ in range(4):
        x0 = int(rng.integers(margin, max(margin + 1, w - margin - 40)))
        y0 = int(rng.integers(h // 3, max(h // 3 + 1, h - margin)))
        draw.line(
            [(x0, y0), (x0 + int(rng.integers(20, 70)), y0 + int(rng.integers(-4, 5)))],
            fill=(40, 40, 120),
            width=2,
        )
    if w > 250:
        cx, cy = int(w * 0.72), int(h * 0.80)
        rad = int(min(w, h) * 0.09)
        draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], outline=(180, 40, 40), width=3)
        draw.text((cx - rad + 4, cy - 6), "PAID", fill=(180, 40, 40), font=_font(int(rad * 0.7), True))
    arr = np.array(img)[:, :, ::-1].copy()
    # Slight paper texture / gradient.
    grad = np.linspace(0.97, 1.0, h)[:, None, None]
    arr = np.clip(arr.astype(np.float32) * grad + rng.normal(0, 1.2, arr.shape), 0, 255)
    return arr.astype(np.uint8)


def background(w: int, h: int, kind: str = "wood", seed: int = 1) -> np.ndarray:
    rng = np.random.default_rng(seed)
    if kind == "wood":
        base = np.zeros((h, w, 3), np.float32)
        yy = np.linspace(0, 1, h)[:, None]
        xx = np.linspace(0, 1, w)[None, :]
        for c, (r, g, b) in enumerate([(120, 90, 60), (150, 120, 85), (100, 75, 50)]):
            base[:, :, c] = r + 25 * np.sin(30 * yy + 2 * xx) + 8 * np.sin(90 * yy)
        noise = rng.normal(0, 7, (h, w, 1))
        base = np.clip(base + noise, 0, 255).astype(np.uint8)
        return cv2.GaussianBlur(base, (3, 3), 0)
    if kind == "gray":
        base = np.full((h, w, 3), 205, np.uint8)
        noise = rng.normal(0, 4, (h, w, 3))
        return np.clip(base.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    if kind == "dark":
        base = np.full((h, w, 3), 55, np.uint8)
        noise = rng.normal(0, 5, (h, w, 3))
        return np.clip(base.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    raise ValueError(kind)


def _random_quad(cx: float, cy: float, pw: float, ph: float, angle: float,
                 rng: np.random.Generator, jitter: float = 0.06) -> np.ndarray:
    corners = []
    ca, sa = math.cos(angle), math.sin(angle)
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        x = sx * pw / 2 + rng.normal(0, pw * jitter)
        y = sy * ph / 2 + rng.normal(0, ph * jitter)
        corners.append([cx + ca * x - sa * y, cy + sa * x + ca * y])
    return np.array(corners, np.float32)


def compose(scene_w: int, scene_h: int, papers: list[dict], *, bg="wood", seed=0) -> Scene:
    """Warp rendered pages onto a background; *papers* entries describe placement."""
    canvas = background(scene_w, scene_h, bg, seed=seed)
    rng = np.random.default_rng(seed)
    quads: list[np.ndarray] = []
    for i, spec in enumerate(papers):
        shape = PAPER_SHAPES[spec["shape"]]
        page = render_page(
            shape,
            tint=spec.get("tint", (250, 249, 244)),
            font_scale=spec.get("font_scale", 1.0),
            seed=seed + i,
        )
        ph, pw = page.shape[:2]
        # Keep a consistent physical scale: a receipt is narrower than A5.
        width_fraction = min(0.44, 0.38 * PAPER_MM[spec["shape"]] / 148.0)
        scale = spec.get("scale", 1.0) * width_fraction * scene_w / pw
        quad = _random_quad(
            spec["x"] * scene_w,
            spec["y"] * scene_h,
            pw * scale,
            ph * scale,
            math.radians(spec.get("angle", 0.0)),
            rng,
            jitter=spec.get("jitter", 0.05),
        )
        # Keep every document fully inside the photo, like a real shot would.
        margin = 6
        quad[:, 0] = np.clip(quad[:, 0], margin, scene_w - margin)
        quad[:, 1] = np.clip(quad[:, 1], margin, scene_h - margin)
        src = np.array(
            [[0, 0], [pw - 1, 0], [pw - 1, ph - 1], [0, ph - 1]], dtype=np.float32
        )
        matrix = cv2.getPerspectiveTransform(src, quad)
        canvas = _warp_into(canvas, page, matrix, quad)
        quads.append(quad)
    return Scene(canvas, quads)


def _warp_into(canvas: np.ndarray, page: np.ndarray, matrix: np.ndarray,
               quad: np.ndarray) -> np.ndarray:
    h, w = canvas.shape[:2]
    mask = np.zeros((h, w), np.uint8)
    cv2.fillConvexPoly(mask, quad.astype(np.int32), 255)
    # Warp page plus alpha; erode the alpha slightly so the page's own border
    # pixels (antialiased with the background) are not pasted onto the scene.
    warped = cv2.warpPerspective(page, matrix, (w, h), flags=cv2.INTER_LINEAR)
    warped_mask = cv2.warpPerspective(
        np.full(page.shape[:2], 255, np.uint8), matrix, (w, h), flags=cv2.INTER_NEAREST
    )
    warped_mask = cv2.erode(warped_mask, np.ones((3, 3), np.uint8))
    out = canvas.copy()
    # Soft shadow offset below the page.
    shadow = np.zeros((h, w), np.uint8)
    cv2.fillConvexPoly(shadow, (quad + np.array([6, 9], np.float32)).astype(np.int32), 255)
    shadow = cv2.GaussianBlur(shadow, (0, 0), 9)
    out = (out.astype(np.float32) * (1.0 - 0.35 * (shadow[..., None] / 255.0))).clip(0, 255)
    out[shadow > 0] = out[shadow > 0]  # keep types simple
    out = out.astype(np.uint8)
    out[warped_mask > 0] = warped[warped_mask > 0]
    return out


def iou_quad(a: np.ndarray, b: np.ndarray) -> float:
    inter, _ = cv2.intersectConvexConvex(a.astype(np.float32), b.astype(np.float32))
    if inter <= 0:
        return 0.0
    area_a = _shoelace(a)
    area_b = _shoelace(b)
    union = area_a + area_b - inter
    return float(inter / union) if union > 0 else 0.0


def _shoelace(pts: np.ndarray) -> float:
    x, y = pts[:, 0], pts[:, 1]
    return 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def match_detections(pred: list[np.ndarray], truth: list[np.ndarray],
                     threshold: float = 0.80) -> tuple[int, float]:
    """Greedy matching; returns (matches, mean IoU of matched pairs)."""
    pairs = []
    for i, p in enumerate(pred):
        for j, t in enumerate(truth):
            pairs.append((iou_quad(p, t), i, j))
    pairs.sort(reverse=True)
    used_p, used_t, ious = set(), set(), []
    for iou, i, j in pairs:
        if iou < threshold or i in used_p or j in used_t:
            continue
        used_p.add(i)
        used_t.add(j)
        ious.append(iou)
    return len(ious), float(np.mean(ious)) if ious else 0.0
