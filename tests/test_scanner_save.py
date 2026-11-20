"""Tests for naming, output sizing, saving and settings."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app.core.naming import render_name, sanitize_stem, unique_path, validate_template
from app.core.scanner import Page, output_size_for, save_pages, scan_page, estimate_size_bytes
from app.core.settings import Settings, default_output_dir, load_settings, save_settings
from app.core.perspective import estimate_paper_aspect


def _page(w=800, h=1000, value=240) -> Page:
    img = np.full((h, w, 3), value, np.uint8)
    img[50:80, 50:w - 50] = 20
    return Page(image=img)


def test_render_name_basic():
    when = datetime(2024, 3, 14, 15, 9, 26)
    assert render_name("Scan_{date}_{time}_{index}", when=when, index=3) == "Scan_2024-03-14_15-09-26_3"
    assert render_name("Doc{index:3}", when=when, index=7) == "Doc007"


def test_render_name_sanitises_illegal_chars():
    when = datetime(2024, 1, 1)
    name = render_name("a/b:c*{index}", when=when, index=1)
    assert not any(ch in name for ch in '\\/:*?"<>|')
    assert sanitize_stem("  name. ") == "name"


def test_validate_template():
    assert validate_template("Scan_{date}_{index}") == []
    assert validate_template("Scan_{bogus}") == ["bogus"]


def test_unique_path(tmp_path):
    (tmp_path / "a.pdf").write_bytes(b"x")
    assert unique_path(tmp_path, "a", "pdf").name == "a_2.pdf"


def test_output_size_never_upscales_absurdly():
    w, h, aspect = output_size_for(200, 283)  # 200x283 ~ A4
    assert aspect == pytest.approx(297 / 210, rel=0.02)
    assert 300 <= h <= 283 * 1.6 + 2
    assert w < h


def test_output_size_respects_max():
    w, h, _ = output_size_for(5000, 7000)
    assert max(w, h) <= 4500


def test_save_pdf_combined(tmp_path):
    pages = [_page(), _page(value=230), _page(value=220)]
    res = save_pages(pages, tmp_path, fmt="pdf", combine_pdf=True,
                     name_template="Batch_{date}_{index}")
    assert not res.errors
    assert len(res.files) == 1
    path = res.files[0]
    assert path.suffix == ".pdf"
    assert path.stat().st_size > 1000
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    assert len(reader.pages) == 3
    # 800 px at the page's 300 dpi == 192 PostScript points.
    assert reader.pages[0].mediabox.width == pytest.approx(800 * 72 / 300, abs=1)
    assert reader.pages[0].mediabox.height == pytest.approx(1000 * 72 / 300, abs=1)


def test_save_pdf_per_page(tmp_path):
    res = save_pages([_page(), _page()], tmp_path, fmt="pdf", combine_pdf=False,
                     name_template="P{index}")
    assert [p.name for p in res.files] == ["P1.pdf", "P2.pdf"]


def test_save_jpg_and_png(tmp_path):
    res = save_pages([_page()], tmp_path, fmt="jpg", name_template="J{index}", jpeg_quality=80)
    assert res.files[0].suffix == ".jpg"
    assert res.files[0].stat().st_size > 300
    res = save_pages([_page()], tmp_path, fmt="png", name_template="N{index}")
    with Image.open(res.files[0]) as img:
        assert img.size == (800, 1000)


def test_save_no_overwrite(tmp_path):
    a = save_pages([_page()], tmp_path, fmt="png", name_template="same")
    b = save_pages([_page()], tmp_path, fmt="png", name_template="same")
    assert a.files[0] != b.files[0]
    assert b.files[0].name == "same_2.png"


def test_save_creates_missing_folder(tmp_path):
    target = tmp_path / "deep" / "folder"
    res = save_pages([_page()], target, fmt="pdf")
    assert target.is_dir()
    assert not res.errors


def test_save_empty_pages(tmp_path):
    res = save_pages([], tmp_path, fmt="pdf")
    assert res.errors


def test_scan_page_end_to_end():
    photo = np.full((1200, 900, 3), 60, np.uint8)
    photo[100:1100, 100:800] = 245
    photo[200:230, 150:700] = 30
    quad = np.array([[100, 100], [800, 100], [800, 1100], [100, 1100]], np.float32)
    page = scan_page(photo, quad, mode="gray")
    assert page.height > page.width
    assert page.image.shape[2] == 3


def test_estimate_size():
    assert estimate_size_bytes([_page()], "jpg") > 200


def test_settings_roundtrip(tmp_path):
    path = tmp_path / "settings.json"
    s = Settings(output_dir=str(tmp_path), format="jpg", jpeg_quality=75)
    save_settings(s, path)
    loaded = load_settings(path)
    assert loaded.output_dir == str(tmp_path)
    assert loaded.format == "jpg"
    assert loaded.jpeg_quality == 75


def test_settings_corrupt_file(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{not json", encoding="utf-8")
    assert load_settings(path).format == "pdf"


def test_settings_clamps_values(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"jpeg_quality": 500, "min_confidence": 5, "format": "webp"}')
    loaded = load_settings(path)
    assert loaded.jpeg_quality == 100
    assert loaded.min_confidence == 1.0
    assert loaded.format == "pdf"


def test_default_output_dir():
    assert default_output_dir().name == "SmartScan"


def test_paper_aspect_hint():
    assert estimate_paper_aspect(1000, 1414) == pytest.approx(297 / 210, rel=1e-3)
