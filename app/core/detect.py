"""Automatic detection of multiple document quadrilaterals in one photo.

The detector deliberately combines several independent "candidate" sources
(edge map, adaptive threshold, illumination flattening, colour saturation).
Any single method fails on some real-world scene -- white paper on a white
table, a receipt on a dark wallet, coloured flyers.  Union of candidates plus
a geometric score and greedy non-maximum suppression is robust and fast
enough to run on a full phone photo in well under a second.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .imaging import (
    _cv,
    normalize_illumination,
    order_points,
    quad_angles,
    quad_area,
    resize_max,
    to_gray,
)
from .perspective import estimate_paper_aspect, quad_regularity

# Detection is run on a downscaled copy for speed; quads are scaled back.
WORK_MAX_SIDE = 1600
MIN_AREA_FRACTION = 0.004          # ignore specks smaller than 0.4% of the frame
MIN_SIDE_PX = 36                   # and anything with a side shorter than this
MAX_AREA_FRACTION = 0.97
MIN_FILL_RATIO = 0.62              # quad area / min-area-rect area


@dataclass
class Detection:
    """One detected document in the original image's coordinates."""

    quad: np.ndarray                      # 4x2, tl, tr, br, bl
    score: float = 0.0                    # 0..1 geometric/morphological quality
    source: str = ""
    area_fraction: float = 0.0

    def __post_init__(self) -> None:
        self.quad = order_points(self.quad)

    @property
    def center(self) -> tuple[float, float]:
        c = self.quad.mean(axis=0)
        return float(c[0]), float(c[1])

    @property
    def width(self) -> float:
        return float(
            (np.linalg.norm(self.quad[1] - self.quad[0]) + np.linalg.norm(self.quad[2] - self.quad[3])) / 2.0
        )

    @property
    def height(self) -> float:
        return float(
            (np.linalg.norm(self.quad[3] - self.quad[0]) + np.linalg.norm(self.quad[2] - self.quad[1])) / 2.0
        )

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        x0, y0 = np.floor(self.quad.min(axis=0)).astype(int)
        x1, y1 = np.ceil(self.quad.max(axis=0)).astype(int)
        return int(x0), int(y0), int(x1), int(y1)

    def scaled(self, factor: float) -> "Detection":
        return Detection(self.quad * factor, self.score, self.source, self.area_fraction)


@dataclass
class DetectionResult:
    detections: list[Detection] = field(default_factory=list)
    work_size: tuple[int, int] = (0, 0)   # (w, h) of the image used internally
    debug: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def detect_documents(image: np.ndarray, *, work_max_side: int = WORK_MAX_SIDE) -> DetectionResult:
    """Detect all document quads in a BGR (or gray) image."""
    cv2 = _cv()
    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    h, w = image.shape[:2]
    if h < 8 or w < 8:
        return DetectionResult()

    work, scale = resize_max(image, work_max_side)
    wh, ww = work.shape[:2]
    total_area = float(ww * wh)
    _FRAME_BOUNDS[0], _FRAME_BOUNDS[1] = float(ww), float(wh)

    candidates: list[Detection] = []
    debug_masks: dict[str, np.ndarray] = {}

    gray = to_gray(work)
    debug_masks["gray"] = gray

    masks = list(_candidate_masks(work, gray))
    for source, mask, approx_eps in masks:
        debug_masks[source] = mask
        for det in _quads_from_mask(mask, total_area, approx_eps):
            det.source = source
            candidates.append(det)

    # Geometry-only fallback is intentionally *not* included: random rectangles
    # in a texture would produce false positives.  Instead, weak candidates are
    # kept only if their edges are supported by actual image gradients.
    scored = [d for d in candidates if d.score >= 0.32]

    # Measure gradient support *before* suppressing duplicates.  Geometry alone
    # is a poor judge when two documents touch: the merged blob is often a
    # fancier-looking polygon than either real page, so NMS would keep it and
    # swallow the accurate pieces.  Real page outlines sit on a strong edge
    # (the perimeter of an actual sheet); a merged blob's outline runs mostly
    # through the desk between the pages.
    # For a merged blob only *part* of each edge sits on a document boundary,
    # so the 25th percentile across the four sides is used rather than the mean:
    # a real page has support along every side, a blob does not.  Mean and
    # quartile are averaged so one shadowed side doesn't veto a real page.
    gx, gy = gradient_maps(gray)
    if scored:
        stats = [edge_support_stats(gx, gy, d.quad) for d in scored]
        raw_support = [0.5 * s_mean + 0.5 * s_p25 for s_mean, s_p25 in stats]
        reference = float(np.percentile(raw_support, 90)) or 1.0
        for det, support_raw in zip(scored, raw_support):
            support = min(1.0, support_raw / reference)
            det.score = min(1.0, 0.55 * det.score + 0.45 * support)

    deduped = _suppress(scored)

    # Keep only quads that actually look like a sheet of paper: noticeably
    # brighter than their surroundings, with a real edge around them.
    # Real paper on a desk is far brighter than its surroundings (measured in
    # tens of grey levels); shadows and wood grain are not.  The threshold sits
    # well clear of both populations.
    validated: list[Detection] = []
    for det in deduped:
        contrast = interior_contrast(gray, det.quad)
        if contrast >= 35.0:
            det.score = min(1.0, det.score + min(0.12, contrast / 400.0))
            validated.append(det)
    deduped = validated

    # Snap each accepted quad onto its edge, inwards only: masks tend to bleed
    # outward, and a shadow can drag a corner into the background.
    for det in deduped:
        det.quad = refine_quad(gray, det.quad, inward_only=True)
    deduped = [d for d in deduped if d.score >= 0.34]

    # Snap edges onto real image gradients (fixes shadow bias, rounded corners).
    for det in deduped:
        det.quad = refine_quad(gray, det.quad)

    # Sort reading order: top-to-bottom, then left-to-right.
    deduped.sort(key=lambda d: (round(d.center[1] / max(1.0, wh / 12.0)), d.center[0]))
    for det in deduped:
        det.area_fraction = quad_area(det.quad) / total_area
        if scale != 1.0:
            det.quad = det.quad / scale
    result = DetectionResult(
        detections=deduped, work_size=(ww, wh), debug={"masks": debug_masks, "scale": scale}
    )
    if scale != 1.0:
        # keep debug masks at working resolution; callers only visualise them
        pass
    return result


def detect_quads(image: np.ndarray, **kwargs) -> list[np.ndarray]:
    """Convenience wrapper returning just the quads."""
    return [d.quad for d in detect_documents(image, **kwargs).detections]


# --------------------------------------------------------------------------- #
# Candidate generation
# --------------------------------------------------------------------------- #
def _candidate_masks(work: np.ndarray, gray: np.ndarray):
    """Yield (name, binary mask, approx epsilon) candidate region masks.

    Every mask is *locally adaptive*: a scene photo has a lit side and a
    shadowed side, and global thresholds happily merge a white page with a
    bright patch of desk.  Divide-by-background normalization is deliberately
    not used here -- it is designed to flatten a page that fills the frame and
    would erase the paper/desk contrast that detection depends on.
    """
    cv2 = _cv()
    h, w = gray.shape[:2]
    short = min(h, w)

    # A. Canny edges, closed into regions.
    blurred = cv2.bilateralFilter(gray, 7, 60, 60)
    v = float(np.median(blurred))
    lower = int(max(0, 0.66 * v))
    upper = int(min(255, 1.33 * v))
    edges = cv2.Canny(blurred, lower, upper)
    edges = cv2.morphologyEx(
        edges, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)), iterations=2
    )
    yield "edges", edges, 0.02

    # B/C. Local (adaptive) brightness, at two window scales.  Window sizes are
    # tied to the frame, so documents of very different sizes are covered.
    for name, fraction in (("adaptive-fine", 0.10), ("adaptive-coarse", 0.30)):
        win = int(max(15, round(short * fraction)) | 1)
        mask = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, win, 7
        )
        mask = cv2.morphologyEx(
            mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        )
        yield name, mask, 0.02

    # D. Global bright regions: reliable when lighting is even, and a useful
    # extra vote when it is not.
    otsu, _ = _otsu(gray)
    _, bright = cv2.threshold(gray, int(otsu), 255, cv2.THRESH_BINARY)
    bright = cv2.morphologyEx(
        bright, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    )
    yield "bright", bright, 0.03

    # E. Saturated regions catch coloured flyers / documents on white desks.
    hsv = cv2.cvtColor(work, cv2.COLOR_BGR2HSV)
    sat = hsv[:, :, 1]
    _, sat_mask = cv2.threshold(sat, 55, 255, cv2.THRESH_BINARY)
    sat_mask = cv2.morphologyEx(
        sat_mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    )
    yield "saturation", sat_mask, 0.03


def _otsu(gray: np.ndarray) -> tuple[int, float]:
    """Fast histogram Otsu for uint8 images."""
    cv2 = _cv()
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).ravel()
    total = float(gray.size)
    if total <= 0:
        return 128, 0.0
    levels = np.arange(256, dtype=np.float64)
    sum_all = float(np.dot(levels, hist))
    w_b = np.cumsum(hist)
    sum_b = np.cumsum(levels * hist)
    w_f = total - w_b
    valid = (w_b > 0) & (w_f > 0)
    if not np.any(valid):
        return 128, 0.0
    mean_b = np.zeros_like(w_b)
    mean_f = np.zeros_like(w_b)
    mean_b[valid] = sum_b[valid] / w_b[valid]
    mean_f[valid] = (sum_all - sum_b[valid]) / w_f[valid]
    var = np.zeros_like(w_b)
    var[valid] = w_b[valid] * w_f[valid] * (mean_b[valid] - mean_f[valid]) ** 2
    best = int(np.argmax(var))
    return best, float(var[best])


def _quads_from_mask(
    mask: np.ndarray, total_area: float, approx_eps: float, *, limit: int = 60
) -> list[Detection]:
    cv2 = _cv()
    h, w = mask.shape[:2]
    contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:limit]
    out: list[Detection] = []
    for contour in contours:
        det = _quad_from_contour(contour, total_area, approx_eps)
        if det is None:
            continue
        x0, y0, x1, y1 = det.bbox
        spans_w = (x1 - x0) >= 0.92 * w
        spans_h = (y1 - y0) >= 0.92 * h
            # A rectangle that runs from frame edge to frame edge in one direction
        # is a lighting band or table edge, not a document lying in the frame.
        if spans_w and (y1 - y0) < 0.55 * h:
            continue
        if spans_h and (x1 - x0) < 0.55 * w:
            continue
        if spans_w and spans_h:
            continue  # the whole frame: nothing to cut out
        out.append(det)
    return out


def _quad_from_contour(contour: np.ndarray, total_area: float, eps_ratio: float) -> Detection | None:
    cv2 = _cv()
    area = float(cv2.contourArea(contour))
    if area < max(400.0, total_area * MIN_AREA_FRACTION) or area > total_area * MAX_AREA_FRACTION:
        return None

    hull = cv2.convexHull(contour)
    peri = float(cv2.arcLength(hull, True))
    quad = None
    # Try progressively looser polygon approximations; the first 4-gon wins.
    for eps in (eps_ratio, eps_ratio * 1.6, eps_ratio * 2.5, eps_ratio * 4.0):
        approx = cv2.approxPolyDP(hull, eps * peri, True)
        if len(approx) == 4:
            quad = approx.reshape(4, 2).astype(np.float32)
            break
    if quad is None:
        # Rounded or partly occluded pages never simplify to exactly four
        # points, which is the common case in real photos.  Fit the best
        # enclosing quadrilateral to the contour instead of giving up.
        quad = _fit_quad(hull)
    if quad is None:
        # Last resort: the minimum-area rectangle.
        rect = cv2.minAreaRect(hull)
        box = cv2.boxPoints(rect).astype(np.float32)
        rect_area = float(cv2.contourArea(box))
        if rect_area <= 0:
            return None
        hull_area = float(cv2.contourArea(hull))
        if hull_area / rect_area < MIN_FILL_RATIO:
            return None
        quad = box

    return _make_detection(quad, total_area, contour_hint=hull)


def _fit_quad(contour: np.ndarray) -> np.ndarray | None:
    """Best enclosing quadrilateral of a contour (4 points, may be skew).

    Brute-force over four tangent lines derived from the contour's edge
    orientations.  Cheap because the candidate set is small, and far more
    accurate for perspective-distorted pages than a minimum-area rectangle.
    """
    cv2 = _cv()
    pts = contour.reshape(-1, 2).astype(np.float32)
    if len(pts) < 12:
        return None

    # Candidate edge directions from a simplified hull, clustered by angle.
    eps = 0.02 * float(cv2.arcLength(pts.reshape(-1, 1, 2), True))
    approx = cv2.approxPolyDP(pts.reshape(-1, 1, 2), eps, True).reshape(-1, 2)
    if len(approx) < 4:
        return None
    edges = np.roll(approx, -1, axis=0) - approx
    lengths = np.linalg.norm(edges, axis=1) + 1e-6
    normals = np.stack([edges[:, 1], -edges[:, 0]], axis=1) / lengths[:, None]

    # Opposite edges of a page share a direction; keep the longest few.
    order = np.argsort(-lengths)[: min(8, len(lengths))]
    normals = normals[order]
    if len(normals) < 4:
        return None

    hull_pts = pts
    # For each normal direction, the support line that contains the contour.
    supports = [(n, float(np.max(hull_pts @ n))) for n in normals]

    best = None
    best_area = None
    count = len(supports)
    for i in range(count):
        for j in range(i + 1, count):
            for k in range(j + 1, count):
                for m in range(k + 1, count):
                    lines = [supports[i], supports[j], supports[k], supports[m]]
                    # Reject near-parallel pairs: a page needs two distinct axes.
                    if min(
                        abs(np.cross(lines[0][0], lines[1][0])),
                        abs(np.cross(lines[0][0], lines[2][0])),
                        abs(np.cross(lines[0][0], lines[3][0])),
                    ) < 0.15:
                        continue
                    corners = []
                    ok = True
                    for a in range(4):
                        n1, c1 = lines[a]
                        n2, c2 = lines[(a + 1) % 4]
                        det = n1[0] * n2[1] - n2[0] * n1[1]
                        if abs(det) < 1e-6:
                            ok = False
                            break
                        corners.append(
                            [
                                (c1 * n2[1] - c2 * n1[1]) / det,
                                (n1[0] * c2 - n2[0] * c1) / det,
                            ]
                        )
                    if not ok:
                        continue
                    quad = order_points(np.array(corners, np.float32))
                    area = quad_area(quad)
                    if area <= 0:
                        continue
                    # The quad must contain essentially all of the contour.
                    inside = sum(
                        1
                        for p in hull_pts
                        if cv2.pointPolygonTest(quad.reshape(-1, 1, 2), (float(p[0]), float(p[1])), False) >= -1.0
                    )
                    if inside < 0.97 * len(hull_pts):
                        continue
                    if best_area is None or area < best_area:
                        best_area = area
                        best = quad
    return best


# --------------------------------------------------------------------------- #
# Scoring / filtering
# --------------------------------------------------------------------------- #
def _page_likeness(quad: np.ndarray) -> float:
    """0..1 score for "could this be a sheet of paper seen from an angle?".

    Checks that the quad is convex, that opposite sides are roughly parallel
    (the defining property of a projected rectangle), and that no angle is
    absurd.  Unlike rectangle-regularity this accepts strong perspective.
    """
    quad = order_points(quad)
    if not np.all(np.isfinite(quad)):
        return 0.0
    # Convexity / consistent orientation of all four turns.
    signs = []
    for i in range(4):
        a = quad[(i + 1) % 4] - quad[i]
        b = quad[(i + 2) % 4] - quad[(i + 1) % 4]
        signs.append(float(a[0] * b[1] - a[1] * b[0]))
    if not (all(s > 0 for s in signs) or all(s < 0 for s in signs)):
        return 0.0
    # Opposite sides parallel-ish (vanishing points make them not exactly so).
    tops = quad[1] - quad[0]
    bottoms = quad[2] - quad[3]
    lefts = quad[3] - quad[0]
    rights = quad[2] - quad[1]
    def parallel(p, q):
        np_ = np.linalg.norm(p) * np.linalg.norm(q)
        if np_ < 1e-6:
            return 0.0
        return abs(float(np.dot(p, q)) / np_)  # |cos| -> 1 means parallel
    parallel_score = (parallel(tops, bottoms) + parallel(lefts, rights)) / 2.0
    # Angles should stay within a sane range for a photographed page.
    angles = quad_angles(quad)
    angle_score = float(np.mean([np.clip((a - 35.0) / 25.0, 0.0, 1.0) for a in angles]))
    return float(np.clip(0.6 * parallel_score + 0.4 * angle_score, 0.0, 1.0))


_FRAME_BOUNDS: list[float] = [0.0, 0.0, 0.0, 0.0]  # w, h set per call


def _quad_outside_penalty(quad: np.ndarray, tolerance: float = 8.0) -> float:
    """Multiplier penalising corners that run off the photo.

    Detection runs on a *downscaled* copy, so a perfectly framed document can
    still land a pixel or two beyond the edge; ``tolerance`` absorbs that and
    only genuinely truncated documents are penalised.
    """
    if not _FRAME_BOUNDS[0]:
        return 1.0
    w, h = _FRAME_BOUNDS[0], _FRAME_BOUNDS[1]
    worst = 0.0
    for x, y in quad:
        worst = max(
            worst,
            -x - tolerance,
            -y - tolerance,
            x - w - tolerance,
            y - h - tolerance,
        )
    if worst <= 0:
        return 1.0
    return float(max(0.6, 1.0 - 0.004 * worst))


def _make_detection(quad: np.ndarray, total_area: float, contour_hint=None) -> Detection | None:
    cv2 = _cv()
    quad = order_points(quad)
    area = quad_area(quad)
    if area <= 0:
        return None
    area_fraction = area / total_area
    if area_fraction < MIN_AREA_FRACTION or area_fraction > MAX_AREA_FRACTION:
        return None

    sides = [
        float(np.linalg.norm(quad[(i + 1) % 4] - quad[i])) for i in range(4)
    ]
    if min(sides) < MIN_SIDE_PX:
        return None
    aspect = max(sides[0], sides[2]) / max(1e-6, max(sides[1], sides[3]))
    if aspect > 8.0 and area_fraction < 0.05:
        # Thin strips are usually table edges, not documents (except receipts,
        # which are handled by the aspect test below).
        if aspect > 14.0:
            return None

    angles = quad_angles(quad)
    if min(angles) < 22.0 or max(angles) > 150.0:
        return None  # self-intersecting or not a page at all

    # Perspective is the norm in photos, so measure how *convex and
    # page-like* the quad is rather than how rectangular it is.
    regularity = quad_regularity(quad) * 0.5 + _page_likeness(quad) * 0.5
    size_score = min(1.0, (area_fraction / 0.35) ** 0.5)
    convexity = 1.0
    if contour_hint is not None and len(contour_hint) >= 4:
        hull_area = float(cv2.contourArea(contour_hint))
        convexity = float(np.clip(hull_area / max(area, 1e-6), 0.4, 1.0))

    score = 0.5 * regularity + 0.35 * size_score + 0.15 * convexity
    # Receipts really are long and thin, so only *extreme* slivers (a table
    # edge, a light strip) are penalised.
    longest = max(sides)
    shortest = max(1e-6, min(sides))
    if longest / shortest > 12.0:
        score *= 0.8
    # Corners outside the frame mean the contour ran off the photo: a document
    # that is not fully visible cannot be scanned well anyway.
    score *= _quad_outside_penalty(quad)
    score *= 0.75 + 0.25 * convexity
    return Detection(quad=quad.astype(np.float32), score=float(score), area_fraction=area_fraction)


def interior_contrast(gray: np.ndarray, quad: np.ndarray) -> float:
    """How much brighter the quad's interior is than a ring just outside it.

    Documents are bright objects on a darker surface.  This cheap measure
    rejects shadow patches, wood-grain stripes and other "rectangle-shaped
    nothings" that survive the mask stage.  Units are grey levels.
    """
    cv2 = _cv()
    h, w = gray.shape[:2]
    quad = order_points(quad).astype(np.float32)
    x0, y0 = np.clip(np.floor(quad.min(axis=0)).astype(int) - 1, 0, [w - 1, h - 1])
    x1, y1 = np.clip(np.ceil(quad.max(axis=0)).astype(int) + 1, 0, [w - 1, h - 1])
    if x1 - x0 < 8 or y1 - y0 < 8:
        return 0.0
    roi = gray[y0:y1, x0:x1]
    mask = np.zeros(roi.shape, np.uint8)
    local = quad - np.array([x0, y0], np.float32)
    cv2.fillConvexPoly(mask, local.astype(np.int32), 255)
    # Shrink the mask so edge pixels and a possible drop shadow don't count.
    eroded = cv2.erode(mask, np.ones((7, 7), np.uint8))
    if not np.any(eroded):
        return 0.0
    inside = float(roi[eroded > 0].mean())
    k = max(3, int(min(roi.shape[:2]) * 0.08) | 1)
    outer = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))
    ring = (outer > 0) & (mask == 0)
    if ring.sum() < 40:
        return 0.0
    outside = float(roi[ring].mean())
    return inside - outside


def _suppress(detections: list[Detection], iou_threshold: float = 0.30) -> list[Detection]:
    """Greedy non-maximum suppression over quadrilaterals."""
    cv2 = _cv()
    ordered = sorted(detections, key=lambda d: (d.score, d.area_fraction), reverse=True)
    kept: list[Detection] = []
    for det in ordered:
        duplicate = False
        for other in kept:
            inter, _ = cv2.intersectConvexConvex(
                det.quad.astype(np.float32), other.quad.astype(np.float32)
            )
            if inter <= 0:
                continue
            a1 = quad_area(det.quad)
            a2 = quad_area(other.quad)
            union = a1 + a2 - inter
            iou = inter / union if union > 0 else 0.0
            contained = inter / max(1.0, min(a1, a2))
            if iou > iou_threshold or contained > 0.80:
                duplicate = True
                break
        if not duplicate:
            # The contour's own source is more informative than which mask
            # happened to find it first (dedupe keeps the best score).
            kept.append(det)
    return kept


# --------------------------------------------------------------------------- #
# Helpers for debugging / deterministic tests
# --------------------------------------------------------------------------- #
def overlay(image: np.ndarray, detections: list[Detection] | DetectionResult) -> np.ndarray:
    """Draw detected quads on a copy of *image* (for tests and the dev tool)."""
    cv2 = _cv()
    out = image.copy()
    if out.ndim == 2:
        out = cv2.cvtColor(out, cv2.COLOR_GRAY2BGR)
    if isinstance(detections, DetectionResult):
        detections = detections.detections
    for i, det in enumerate(detections):
        pts = det.quad.astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(out, [pts], True, (0, 200, 0), 3, cv2.LINE_AA)
        x, y = det.quad[0].astype(int)
        cv2.putText(
            out,
            f"{i + 1}",
            (int(x) + 6, int(y) + 26),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )
    return out


def set_work_max_side(value: int) -> None:
    """Adjust the working resolution (used by tests to speed things up)."""
    global WORK_MAX_SIDE
    WORK_MAX_SIDE = int(value)


def paper_aspect_hint(det: Detection) -> float | None:
    return estimate_paper_aspect(det.width, det.height)


# --------------------------------------------------------------------------- #
# Edge refinement
# --------------------------------------------------------------------------- #
def _sample(map_: np.ndarray, points: np.ndarray) -> np.ndarray:
    """Bilinear sample of a float map at Nx2 float points (cv2.remap)."""
    cv2 = _cv()
    pts = np.asarray(points, np.float32).reshape(-1, 1, 2)
    return cv2.remap(
        map_, pts, None, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE
    ).ravel()


def _edge_samples(quad: np.ndarray, edge_index: int, count: int):
    """Sample points along edge i, plus its unit direction and normal."""
    p0 = quad[edge_index]
    p1 = quad[(edge_index + 1) % 4]
    edge = p1 - p0
    length = float(np.linalg.norm(edge))
    if length < 10:
        return None
    d = edge / length
    n = np.array([-d[1], d[0]], np.float32)
    ts = np.linspace(0.12, 0.88, count)
    pts = p0[None, :] + edge[None, :] * ts[:, None]
    return pts, n, length


def gradient_maps(gray: np.ndarray):
    """Smoothed Sobel gradients used for edge scoring and refinement."""
    cv2 = _cv()
    smooth = cv2.GaussianBlur(gray, (3, 3), 0)
    gx = cv2.Sobel(smooth, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(smooth, cv2.CV_32F, 0, 1, ksize=3)
    return gx, gy


def edge_support_stats(gx: np.ndarray, gy: np.ndarray, quad: np.ndarray,
                       band: int = 2, samples: int = 90) -> tuple[float, float]:
    """(mean, 25th-percentile) gradient magnitude across the four quad edges."""
    per_side: list[float] = []
    for i in range(4):
        sampled = _edge_samples(order_points(quad), i, samples)
        if sampled is None:
            continue
        pts, normal, _ = sampled
        best = np.zeros(len(pts), np.float32)
        for off in range(-band, band + 1):
            shifted = pts + normal[None, :] * off
            response = np.abs(_sample(gx, shifted) * normal[0] + _sample(gy, shifted) * normal[1])
            best = np.maximum(best, response)
        per_side.append(float(best.mean()))
    if not per_side:
        return 0.0, 0.0
    return float(np.mean(per_side)), float(np.percentile(per_side, 25))


def edge_support(gx: np.ndarray, gy: np.ndarray, quad: np.ndarray,
                 band: int = 2, samples: int = 90) -> float:
    """Mean gradient magnitude measured across the four quad edges."""
    total, count = 0.0, 0
    for i in range(4):
        sampled = _edge_samples(order_points(quad), i, samples)
        if sampled is None:
            continue
        pts, normal, _ = sampled
        best = np.zeros(len(pts), np.float32)
        for off in range(-band, band + 1):
            shifted = pts + normal[None, :] * off
            response = np.abs(_sample(gx, shifted) * normal[0] + _sample(gy, shifted) * normal[1])
            best = np.maximum(best, response)
        total += float(best.mean())
        count += 1
    return total / max(1, count)


def refine_quad(gray: np.ndarray, quad: np.ndarray, *, search_px: int | None = None,
                gate: bool = True, inward_only: bool = False) -> np.ndarray:
    """Snap each quad edge onto the strongest nearby gradient.

    Strategy per edge: build an aggregate response profile over perpendicular
    offsets (sum of |gradient·normal| along the whole edge).  The peak of that
    profile is far more reliable than per-sample argmax, which is easily
    distracted by wood grain or a neighbouring document.  Samples near the peak
    are then robustly line-fitted and adjacent lines intersected.
    """
    quad = order_points(quad)
    h, w = gray.shape[:2]
    side = float(min(np.linalg.norm(quad[1] - quad[0]), np.linalg.norm(quad[3] - quad[0])))
    if search_px is None:
        search_px = int(np.clip(side * 0.035, 3, 26))
    search_px = max(1, int(search_px))

    gx, gy = gradient_maps(gray)

    lines: list[tuple[float, float, float] | None] = []
    # Offsets run along each edge's normal.  With ``inward_only`` the search
    # space is shrunk towards the quad's centre, which is what we want when a
    # mask has bled outwards into the background.
    offsets = np.arange(-search_px, search_px + 1, dtype=np.float32)
    inward_sign = [1.0, 1.0, 1.0, 1.0]
    if inward_only:
        centre = quad.mean(axis=0)
        for i in range(4):
            mid = (quad[i] + quad[(i + 1) % 4]) / 2.0
            edge_dir = quad[(i + 1) % 4] - quad[i]
            normal = np.array([-edge_dir[1], edge_dir[0]], np.float32)
            inward_sign[i] = 1.0 if np.dot(centre - mid, normal) > 0 else -1.0
    for i in range(4):
        sampled = _edge_samples(quad, i, int(np.clip(side / 5.0, 16, 140)))
        if sampled is None:
            lines.append(None)
            continue
        pts, normal, _ = sampled

        # Vectorised response for every sample x offset.
        offs = offsets * inward_sign[i]
        shifted = pts[:, None, :] + normal[None, None, :] * offs[None, :, None]
        resp = np.abs(
            _sample(gx, shifted.reshape(-1, 2)) * normal[0]
            + _sample(gy, shifted.reshape(-1, 2)) * normal[1]
        ).reshape(shifted.shape[:2])
        profile = resp.sum(axis=0)
        if profile.max() <= 0:
            lines.append(None)
            continue
        penalty = 1.0 - 0.010 * np.abs(offs)
        peak = int(np.argmax(profile * penalty))
        peak_off = float(offs[peak])
        peak_value = float(profile[peak] / len(pts))
        if peak_value < 8.0:
            lines.append(None)  # no credible border here; keep the original edge
            continue

        # Per-sample refined hits within +/- 2 px of the aggregate peak.
        lo = max(0, peak - 2)
        hi = min(resp.shape[1], peak + 3)
        near = resp[:, lo:hi]
        best_col = np.argmax(near, axis=1)
        best_val = near[np.arange(len(pts)), best_col]
        keep = best_val > 0.45 * peak_value
        if keep.sum() < 6:
            lines.append(None)
            continue
        refined_pts = pts[keep] + normal[None, :] * offs[lo + best_col[keep]][:, None]
        lines.append(_robust_line(list(refined_pts)))

    if all(line is None for line in lines):
        return quad

    refined = []
    for i in range(4):
        prev_line = lines[i - 1]
        this_line = lines[i]
        corner = quad[i]
        if prev_line is not None and this_line is not None:
            hit = _line_intersection(prev_line, this_line)
            if hit is not None:
                cand = np.array(hit, np.float32)
                if np.linalg.norm(cand - quad[i]) <= max(4.0, search_px * 2.0):
                    corner = cand
        refined.append(corner)
    refined = np.array(refined, np.float32)

    # Geometric sanity checks.  Refinement moves each corner at most a few
    # pixels, so anything beyond a modest change means the fit went wrong.
    # (A relative check is used: a global area threshold would reject small
    # documents entirely.)
    area0 = quad_area(quad)
    area1 = quad_area(refined)
    if area1 <= 0 or not (0.55 * area0 <= area1 <= 1.8 * area0):
        return quad
    err0 = max(abs(a - 90.0) for a in quad_angles(quad))
    err1 = max(abs(a - 90.0) for a in quad_angles(refined))
    if err1 > max(35.0, err0 + 2.0) or not np.all(np.isfinite(refined)):
        return quad
    # Final gate: only accept if the border is genuinely better supported.
    if gate and edge_support(gx, gy, refined) < edge_support(gx, gy, quad) * 1.005:
        return quad
    return order_points(refined)


def _robust_line(points: list[np.ndarray]) -> tuple[float, float, float] | None:
    """Least-squares line (a, b, c with ax+by=c) with iterative outlier removal."""
    if len(points) < 6:
        return None
    arr = np.array(points, np.float64)
    line = _fit_line(arr)
    if line is None:
        return None
    for _ in range(2):
        a, b, c = line
        dist = np.abs(a * arr[:, 0] + b * arr[:, 1] - c) / max(1e-6, (a * a + b * b) ** 0.5)
        keep = dist <= max(1.5, float(np.percentile(dist, 75)))
        if keep.sum() < 6:
            break
        line = _fit_line(arr[keep])
        if line is None:
            break
    return line


def _fit_line(arr: np.ndarray) -> tuple[float, float, float] | None:
    """Total least squares line via PCA; returns (a, b, c) normalised."""
    mean = arr.mean(axis=0)
    centered = arr - mean
    try:
        _, _, vt = np.linalg.svd(centered, full_matrices=False)
    except np.linalg.LinAlgError:  # pragma: no cover
        return None
    normal = vt[-1]
    n = np.linalg.norm(normal)
    if n < 1e-9:
        return None
    normal = normal / n
    a, b = float(normal[0]), float(normal[1])
    c = float(a * mean[0] + b * mean[1])
    return a, b, c


def _line_intersection(l1: tuple[float, float, float],
                       l2: tuple[float, float, float]) -> tuple[float, float] | None:
    a1, b1, c1 = l1
    a2, b2, c2 = l2
    det = a1 * b2 - a2 * b1
    if abs(det) < 1e-6:
        return None
    x = (c1 * b2 - c2 * b1) / det
    y = (a1 * c2 - a2 * c1) / det
    return float(x), float(y)
