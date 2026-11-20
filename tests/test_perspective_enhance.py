"""Tests for dewarping, uprighting and enhancement."""

from __future__ import annotations

import numpy as np
import pytest

from app.core.enhance import (
    MODE_BW,
    MODE_COLOR,
    MODE_GRAY,
    MODE_MAGIC,
    MODE_ORIGINAL,
    enhance,
    is_color_content,
)
from app.core.perspective import (
    estimate_paper_aspect,
    looks_sideways,
    quad_to_image,
)

A4 = np.array([[120, 80], [620, 110], [600, 780], [95, 760]], np.float32)


@pytest.fixture()
def page() -> np.ndarray:
    img = np.full((800, 700, 3), 245, np.uint8)
    img[100:130, 100:500] = 20      # title bar
    for y in range(180, 700, 30):
        img[y : y + 10, 100:550] = 45
    return img


def test_quad_to_image_returns_upright_rectangle(page):
    out = quad_to_image(page, A4)
    h, w = out.shape[:2]
    assert h > w, "A4 detected portrait should come out portrait"
    assert 1.2 < h / w < 1.6


def test_quad_to_image_respects_max_side(page):
    out = quad_to_image(page, A4, out_max_side=400)
    assert max(out.shape[:2]) <= 402


def test_quad_to_image_margin_grows_crop(page):
    plain = quad_to_image(page, A4, margin_px=0)
    grown = quad_to_image(page, A4, margin_px=12)
    assert grown.shape[0] >= plain.shape[0]
    assert grown.shape[1] >= plain.shape[1]


def test_estimate_paper_aspect_matches_a4():
    assert estimate_paper_aspect(1000, 1414) == pytest.approx(297 / 210, rel=1e-6)
    assert estimate_paper_aspect(700, 1000) == pytest.approx(297 / 210, rel=0.02)


def test_estimate_paper_aspect_unknown_shape():
    assert estimate_paper_aspect(500, 500) in (None, 1.0)


def test_sideways_text_detected_and_rotated():
    text = np.full((700, 500, 3), 250, np.uint8)
    for y in range(60, 640, 26):
        text[y : y + 8, 60:440] = 30
    sideways = np.rot90(text)
    assert looks_sideways(sideways)
    assert not looks_sideways(text)


def test_enhance_modes_produce_same_shape(page):
    for mode in (MODE_ORIGINAL, MODE_COLOR, MODE_GRAY, MODE_BW, MODE_MAGIC):
        out = enhance(page, mode)
        assert out.shape == page.shape
        assert out.dtype == np.uint8


def test_enhance_bw_makes_bimodal(page):
    out = enhance(page, MODE_BW)
    values = np.unique(out)
    assert set(values.tolist()).issubset({0, 255})


def test_enhance_gray_is_gray(page):
    out = enhance(page, MODE_GRAY)
    assert np.array_equal(out[:, :, 0], out[:, :, 1])
    assert np.array_equal(out[:, :, 1], out[:, :, 2])


def test_enhance_rejects_unknown_mode(page):
    with pytest.raises(ValueError):
        enhance(page, "sepia")


def test_color_content_detection():
    white = np.full((300, 300, 3), 250, np.uint8)
    colored = white.copy()
    colored[:150] = (40, 80, 220)
    assert not is_color_content(white)
    assert is_color_content(colored)


def test_gray_input_accepted():
    gray = np.full((300, 200), 240, np.uint8)
    out = enhance(gray, MODE_MAGIC)
    assert out.shape == (300, 200, 3)
