"""Advice shown when nothing is found must fit the kind of page it is about."""

from __future__ import annotations

import pytest

from app.core import guidance


def test_scan_advice_is_not_photo_advice():
    """A scan's background is the lid; 'improve the lighting' is not actionable."""
    scan = guidance.empty_help(True)

    assert "lid" in scan
    assert "coloured sheet" in scan
    assert "dark mat" in scan
    assert "lighting " not in scan.split("own:")[1]   # only mentioned to rule it out
    assert "shadows" not in scan.lower()


def test_photo_advice_stays_about_the_photograph():
    photo = guidance.empty_help(False)

    assert "photo" in photo.lower()
    assert "shadows" in photo.lower()
    assert "lid" not in photo.lower()
    assert "Diagnose" not in photo


def test_scan_help_points_at_the_tool_that_can_actually_diagnose_a_scan():
    scan = guidance.empty_help(True)
    assert "Diagnose" in scan
    assert "glass" in scan


@pytest.mark.parametrize("is_scan", [True, False])
def test_status_line_matches_the_dialog(is_scan):
    status = guidance.empty_status(is_scan)
    assert status.startswith("No documents found")
    if is_scan:
        assert "lid" in status
    else:
        assert "lighting" in status
    assert status == guidance.EMPTY_STATUS[is_scan]


def test_status_accepts_a_plain_truthiness_flag():
    assert guidance.empty_status(1) == guidance.empty_status(True)
    assert guidance.empty_status(0) == guidance.empty_status(False)


def test_scan_and_photo_text_are_different():
    assert guidance.empty_help(True) != guidance.empty_help(False)
    assert guidance.empty_status(True) != guidance.empty_status(False)


def test_docpage_reports_where_it_came_from():
    """The gate for the advice above lives on DocPage; no Qt needed for it."""
    from pathlib import Path

    import numpy as np

    from app.ui.doc_page import DocPage

    blank = np.zeros((8, 8, 3), np.uint8)
    scan = DocPage(path=Path("page_000.tif"), image=blank, origin="scan")
    photo = DocPage(path=Path("IMG_0001.jpg"), image=blank)
    clip = DocPage(path=None, image=blank, origin="clipboard")

    assert scan.is_scan and scan.source_label == "scr"
    assert not photo.is_scan and photo.source_label == "ph"
    assert not clip.is_scan
    assert photo.name == "IMG_0001.jpg"
    assert clip.name == "Clipboard image"
