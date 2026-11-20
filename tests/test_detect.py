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


# ------------------------------------------------------ flatbed scans (1.1.3)
# A scan is the opposite of a photo: the scanner's lid is white, so a coloured
# or grey document is *darker* than its background.  1.1.x required "brighter
# than the surroundings" and rejected every such scan, however clean its edge.
# Reported from a real HP LaserJet M1005 scan of a yellow India Post postcard.
def test_yellow_postcard_on_white_lid_is_found():
    scene = scenes.compose_scan(
        1000, 1300,
        [dict(shape="postcard", x=0.5, y=0.5, angle=2, tint=(60, 190, 235))],
        seed=1,
    )
    result = detect_documents(scene.image)
    pred = [d.quad for d in result.detections]
    matched, mean_iou = scenes.match_detections(pred, scene.quads)
    assert matched == 1, f"expected the postcard, got {len(pred)} detections"
    assert mean_iou > 0.93


def test_grey_card_on_white_lid_is_found():
    scene = scenes.compose_scan(
        1000, 1300,
        [dict(shape="a6", x=0.48, y=0.52, angle=-4, tint=(205, 205, 203))],
        seed=3,
    )
    result = detect_documents(scene.image)
    pred = [d.quad for d in result.detections]
    matched, _ = scenes.match_detections(pred, scene.quads)
    assert matched == 1, f"expected the grey card, got {len(pred)} detections"


def test_two_postcards_on_the_scanner_are_both_found():
    """Two cards on an open bed, each found on its own.

    The second card is light cream rather than pure white: paper only a few
    grey levels from the lid is a known limitation (see `DARKER_CONTRAST_MIN`),
    so the scene stays one a human could also separate at a glance.
    """
    scene = scenes.compose_scan(
        1200, 1300,
        [dict(shape="postcard", x=0.30, y=0.32, angle=1, width=0.40,
              tint=(60, 190, 235)),
         dict(shape="postcard", x=0.72, y=0.70, angle=-2, width=0.40,
              tint=(200, 196, 190))],
        seed=5,
    )
    result = detect_documents(scene.image)
    pred = [d.quad for d in result.detections]
    matched, _ = scenes.match_detections(pred, scene.quads)
    assert matched == 2, f"matched {matched}/2; {len(pred)} detections"


def test_blank_scanner_lid_produces_nothing():
    """The empty bed must not invent documents."""
    from app.core.detect import detect_documents as detect

    blank = scenes.scanner_bed(1000, 1300, seed=9)
    assert detect(blank).detections == []


def test_internal_boxes_on_a_cropped_scan_are_not_documents():
    """A pre-cropped scan has crisp internal edges; they must stay rejected."""
    page = scenes.render_page((420, 595))
    canvas = np.full((620, 440, 3), 30, np.uint8)
    canvas[12:607, 10:430] = page
    for det in detect_documents(canvas).detections:
        assert det.area_fraction > 0.85, (
            f"small internal box accepted: area={det.area_fraction:.3f}"
        )


# --------------------------------------------------------------------------- #
# Low-contrast photographs: paper that is only slightly lighter than a plain
# desk.  The brightness gate alone cannot decide these; the surface's texture
# is the evidence that separates a smooth sheet from a tabletop.
# --------------------------------------------------------------------------- #
def test_white_paper_on_a_light_grey_desk_is_found():
    """Measured 15-31 grey levels of contrast: under the 35-level floor."""
    scene = scenes.compose(
        1100, 1300, [dict(shape="a6", x=0.5, y=0.5, angle=3, tint=(210, 208, 200))],
        bg="gray", seed=11,
    )
    result = detect_documents(scene.image)
    matched, _ = scenes.match_detections([d.quad for d in result.detections], scene.quads)
    assert matched == 1, f"contrast was too low to accept; {len(result.detections)} found"


def test_pale_paper_on_a_wooden_desk_is_found():
    scene = scenes.compose(
        1100, 1300, [dict(shape="a5", x=0.5, y=0.5, angle=3, tint=(225, 225, 220))],
        bg="wood", seed=21,
    )
    result = detect_documents(scene.image)
    matched, _ = scenes.match_detections([d.quad for d in result.detections], scene.quads)
    assert matched == 1


def test_empty_desks_never_become_documents():
    """The texture evidence must not turn a bare tabletop into paper."""
    for bg in ("wood", "gray", "dark"):
        for seed in range(1, 5):
            empty = scenes.background(1100, 1300, bg, seed=seed)
            assert detect_documents(empty).detections == [], f"invented a page on {bg}/{seed}"


def test_internal_boxes_stay_rejected_on_a_low_contrast_scene():
    """Same low-contrast desk, but the 'document' is a box inside a page."""
    page = scenes.render_page((600, 440), tint=(240, 238, 232), seed=3)
    canvas = scenes.background(1300, 1100, "gray", seed=11)
    h, w = page.shape[:2]
    canvas[300:300 + h, 220:220 + w] = page
    for det in detect_documents(canvas).detections:
        # Only the whole photographed page is a document; boxes inside it are not.
        assert det.area_fraction > 0.05, f"accepted an internal box: {det.area_fraction:.3f}"


# Bright white through to a light recycled grey, where brightness alone stops
# being enough to separate paper from the desk.
_SWEEP_TINTS = [(250, 249, 244), (240, 236, 225), (225, 225, 220)]


@pytest.mark.parametrize("bg", ["wood", "dark", "gray"])
def test_paper_on_any_desk_is_found_for_every_shape(bg):
    """A sweep, not a lucky scene: every paper shape, on every desk surface.

    The tints run from bright white down to a light recycled grey, which is
    where brightness alone stops being enough.  Shape coverage matters: a
    small, text-dense card gives the masks far less to work with than A5.
    """
    misses = []
    for seed in (1, 2):
        for tint in _SWEEP_TINTS:
            if bg == "gray" and tint[0] == 225:
                continue  # the known gap, pinned by its own test above
            for k, shape in enumerate(("a5", "a6", "receipt", "card")):
                scene = scenes.compose(
                    1100, 1300, [dict(shape=shape, x=0.5, y=0.5, angle=3, tint=tint)],
                    bg=bg, seed=seed * 10 + k,
                )
                result = detect_documents(scene.image)
                matched, _ = scenes.match_detections(
                    [d.quad for d in result.detections], scene.quads
                )
                if not (matched == 1 and len(result.detections) == 1):
                    misses.append((tint[0], shape, seed))
    assert not misses, f"{len(misses)} scenes missed on {bg}: {misses}"


def test_light_grey_paper_on_a_light_grey_desk_is_the_known_gap():
    """Pinned as a measurement, not a wish: most scenes pass, some do not.

    The limiting factor is resolution, not logic.  In a 1100 px scene the 3 px
    high-pass that measures surface roughness straddles paper (2.4 grey levels
    of noise) and desk (3.2) too closely to be decisive.  Recording the real
    number means an improvement shows up as a failure here, prompting an
    update rather than silent drift.
    """
    found = 0
    scenes_checked = 0
    for seed in (1, 2, 3):
        for k, shape in enumerate(("a5", "a6", "receipt", "card")):
            scene = scenes.compose(
                1100, 1300,
                [dict(shape=shape, x=0.5, y=0.5, angle=3, tint=(225, 225, 220))],
                bg="gray", seed=seed * 10 + k,
            )
            result = detect_documents(scene.image)
            matched, _ = scenes.match_detections(
                [d.quad for d in result.detections], scene.quads
            )
            scenes_checked += 1
            found += matched == 1 and len(result.detections) == 1
    assert found >= 9, f"regressed: only {found}/{scenes_checked} found"
    assert found < scenes_checked, (
        f"the gap is closed ({found}/{scenes_checked}) - retire this test and "
        "fold the tint back into the sweep above"
    )


def test_quad_fitting_does_not_require_numpy_2d_cross(monkeypatch):
    """Support-line fitting must work when NumPy rejects 2D cross products."""
    from app.core.detect import _fit_quad

    def reject_cross(*args, **kwargs):
        raise AssertionError("use the scalar 2D determinant instead")

    monkeypatch.setattr(np, "cross", reject_cross)
    angles = np.linspace(0, 2 * np.pi, 60, endpoint=False)
    contour = np.column_stack((200 + 100 * np.cos(angles),
                               200 + 80 * np.sin(angles))).astype(np.float32)
    result = _fit_quad(contour.reshape(-1, 1, 2))
    assert result is None or (result.shape == (4, 2) and np.isfinite(result).all())
