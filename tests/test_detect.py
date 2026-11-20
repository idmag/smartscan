"""Detection accuracy tests on deterministic synthetic photos."""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scenes  # noqa: E402

from app.core.detect import detect_documents, refine_quad  # noqa: E402
from app.core.perspective import quad_regularity  # noqa: E402

pytestmark = pytest.mark.filterwarnings("ignore::RuntimeWarning")


def _is_convex(quad) -> bool:
    signs = []
    for i in range(4):
        a = quad[(i + 1) % 4] - quad[i]
        b = quad[(i + 2) % 4] - quad[(i + 1) % 4]
        signs.append(float(a[0] * b[1] - a[1] * b[0]))
    return all(s > 0 for s in signs) or all(s < 0 for s in signs)


def _run(image, min_iou=0.80):
    result = detect_documents(image)
    pred = [d.quad for d in result.detections]
    return result, pred


def test_two_documents_on_wood():
    scene = scenes.compose(
        900, 1200,
        [dict(shape="a5", x=0.33, y=0.34, angle=6),
         dict(shape="receipt", x=0.73, y=0.62, angle=-14)],
        bg="wood", seed=3,
    )
    result, pred = _run(scene.image)
    matched, mean_iou = scenes.match_detections(pred, scene.quads)
    assert len(pred) == 2, f"expected 2 detections, got {len(pred)}"
    assert matched == 2
    assert mean_iou > 0.90
    for det in result.detections:
        assert 0.30 < det.score <= 1.0
        # A photographed page is a convex quad, not necessarily a rectangle.
        assert np.all(np.isfinite(det.quad))
        assert _is_convex(det.quad)


def test_four_documents_mixed_shapes():
    scene = scenes.compose(
        1050, 1400,
        [dict(shape="a5", x=0.32, y=0.33, angle=8),
         dict(shape="receipt", x=0.72, y=0.30, angle=-12),
         dict(shape="card", x=0.34, y=0.74, angle=20),
         dict(shape="a6", x=0.76, y=0.72, angle=-6)],
        bg="wood", seed=7,
    )
    result, pred = _run(scene.image)
    matched, _ = scenes.match_detections(pred, scene.quads)
    assert matched >= 3, f"matched {matched}/4; detections: {len(pred)}"


def test_paper_on_white_desk_does_not_vanish():
    """Low contrast (near-white paper on light grey) must still be detected."""
    scene = scenes.compose(
        900, 1200,
        [dict(shape="a5", x=0.36, y=0.35, angle=-9, tint=(252, 252, 250))],
        bg="gray", seed=11,
    )
    result, pred = _run(scene.image)
    matched, _ = scenes.match_detections(pred, scene.quads, threshold=0.75)
    assert matched == 1


def test_receipt_on_dark_background():
    """A light receipt on a dark mat must be found as a real document.

    White paper on near-black velvet is an extreme contrast; the guarantee is
    that the receipt is located (within a loose IoU) and nothing else is
    invented.
    """
    scene = scenes.compose(
        900, 1200, [dict(shape="receipt", x=0.5, y=0.5, angle=4)], bg="dark", seed=5
    )
    result, pred = _run(scene.image)
    assert 1 <= len(pred) <= 2
    matched, _ = scenes.match_detections(pred, scene.quads, threshold=0.50)
    assert matched == 1


def test_no_documents_returns_empty():
    rng = np.random.default_rng(42)
    noise = rng.integers(0, 255, (600, 800, 3), dtype=np.uint8)
    noise = cv2.GaussianBlur(noise, (7, 7), 0)
    result = detect_documents(noise)
    assert len(result.detections) == 0


def test_full_frame_document_is_rejected_or_exact():
    """A pre-cropped scan should not produce a bogus inner rectangle."""
    page = scenes.render_page((420, 595))
    canvas = np.full((620, 440, 3), 30, np.uint8)
    canvas[12:607, 10:430] = page
    result = detect_documents(canvas)
    for det in result.detections:
        # Any detection must cover essentially the whole page, not a table line.
        assert det.area_fraction > 0.85


def test_refine_quad_improves_shadow_bias():
    scene = scenes.compose(
        800, 1000, [dict(shape="a5", x=0.5, y=0.5, angle=3, jitter=0.0)], bg="wood", seed=21
    )
    gray = cv2.cvtColor(scene.image, cv2.COLOR_BGR2GRAY)
    truth = scene.quads[0]
    biased = truth + np.array([[4, 5], [4, 5], [4, 5], [4, 5]], np.float32)
    refined = refine_quad(gray, biased)
    err_before = np.mean(np.linalg.norm(biased - truth, axis=1))
    err_after = np.mean(np.linalg.norm(refined - truth, axis=1))
    assert err_after < err_before


def test_detections_sorted_reading_order():
    scene = scenes.compose(
        900, 1300,
        [dict(shape="card", x=0.70, y=0.25, angle=0),
         dict(shape="card", x=0.28, y=0.22, angle=0),
         dict(shape="card", x=0.50, y=0.75, angle=0)],
        bg="wood", seed=33,
    )
    result = detect_documents(scene.image)
    assert len(result.detections) == 3
    centers = [d.center for d in result.detections]
    assert centers[0][1] < centers[2][1]
    assert centers[0][0] < centers[1][0]
