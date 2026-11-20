"""Scanner (WIA) import: the parts that can be tested without hardware.

Real acquisition needs a physical scanner, so these tests cover the plumbing
that has caused trouble in comparable apps: PowerShell output parsing, feeding
an empty device list, mapping WIA error codes onto readable messages, splitting
multi-page TIFFs, and failing politely on non-Windows platforms.
"""

from __future__ import annotations

import json
import sys

import numpy as np
import pytest
from PIL import Image

from app.core import scan_device
from app.core.scan_device import (
    AcquireResult,
    ScannerDevice,
    ScannerError,
    _diagnose_powershell_failure,
    _run_powershell,
    acquire_pages,
    describe_wia_error,
    list_devices,
    parse_acquire_output,
    parse_device_list,
    powershell_command,
    split_multipage,
)


def _device_payload(devices):
    return json.dumps({"ok": True, "devices": devices}, separators=(",", ":"))


# --------------------------------------------------------------- device list
def test_parse_device_list_with_two_scanners():
    devices = parse_device_list(
        _device_payload(
            [
                {"id": "WIA-AAA", "name": "Epson Perfection V39", "feeder": False},
                {"id": "WIA-BBB", "name": "Brother ADS-1700W", "feeder": True},
            ]
        )
    )
    assert [d.name for d in devices] == ["Epson Perfection V39", "Brother ADS-1700W"]
    assert devices[0].kind == "flatbed"
    assert devices[1].kind == "feeder"
    assert "document feeder" in devices[1].label
    assert "flatbed" in devices[0].label


def test_parse_device_list_when_none_attached():
    assert parse_device_list(json.dumps({"ok": True, "devices": []})) == []


def test_parse_device_list_skips_incomplete_entries():
    devices = parse_device_list(_device_payload([{"id": "", "name": "Broken"}]))
    assert devices == []


def test_parse_device_list_ignores_leading_powershell_noise():
    output = 'WARNING: something\n{"ok":true,"devices":[{"id":"X","name":"S","feeder":false}]}'
    assert [d.name for d in parse_device_list(output)] == ["S"]


def test_parse_device_list_reports_wia_failure():
    with pytest.raises(ScannerError) as info:
        parse_device_list(json.dumps({"ok": False, "error": "The RPC server is unavailable."}))
    assert "could not list the scanners" in info.value.message
    assert "RPC server" in info.value.hint


def test_parse_device_list_rejects_garbage():
    with pytest.raises(ScannerError):
        parse_device_list("not json at all")


# ------------------------------------------------------------------- acquire
def test_parse_acquire_output_collects_pages_in_order(tmp_path):
    (tmp_path / "page_000.tif").write_bytes(b"x")
    (tmp_path / "page_001.tif").write_bytes(b"x")
    (tmp_path / "notes.txt").write_text("ignore me")
    result = parse_acquire_output(
        json.dumps({"ok": True, "pages": 2, "feeder": True}), tmp_path
    )
    assert [p.name for p in result.pages] == ["page_000.tif", "page_001.tif"]
    assert result.feeder is True


def test_parse_acquire_output_raises_when_driver_fails(tmp_path):
    payload = json.dumps({"ok": False, "pages": 0, "error": "The paper feed is empty."})
    with pytest.raises(ScannerError):
        parse_acquire_output(payload, tmp_path)


def test_parse_acquire_output_raises_when_no_files_written(tmp_path):
    with pytest.raises(ScannerError) as info:
        parse_acquire_output(json.dumps({"ok": True, "pages": 1}), tmp_path)
    assert "no image" in info.value.message.lower()


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("The operation cannot be performed because the paper is empty. 0x8021006B", "feeder is empty"),
        ("The device is offline (0x80210003)", "offline"),
        ("Device busy", "busy"),
        ("Access denied", "refused access"),
        ("Scan was cancelled by user", "cancelled"),
        ("", "unknown error"),
    ],
)
def test_wia_errors_become_actionable_text(raw, expected):
    assert expected in describe_wia_error(raw).lower()


def test_wia_error_keeps_unrecognised_detail():
    message = describe_wia_error("Something odd happened in the driver")
    assert "Something odd happened" in message


# -------------------------------------------------------------- multi-page TIFF
def _multipage_tiff(path, count=3):
    frames = [
        Image.fromarray(np.full((40, 30, 3), 30 + i * 60, dtype=np.uint8))
        for i in range(count)
    ]
    frames[0].save(path, save_all=True, append_images=frames[1:])
    return path


def test_split_multipage_tiff_keeps_every_page(tmp_path):
    source = _multipage_tiff(tmp_path / "page_000.tif", count=3)
    pages = split_multipage(source)
    assert len(pages) == 3
    assert source.exists() is False  # replaced by the split files
    for page in pages:
        with Image.open(page) as image:
            assert image.n_frames == 1


def test_split_multipage_tiff_leaves_single_pages_alone(tmp_path):
    source = tmp_path / "page_000.tif"
    Image.fromarray(np.zeros((10, 10, 3), dtype=np.uint8)).save(source)
    assert split_multipage(source) == [source]


def test_split_multipage_ignores_jpegs(tmp_path):
    source = tmp_path / "page_000.jpg"
    Image.fromarray(np.zeros((10, 10, 3), dtype=np.uint8)).save(source)
    assert split_multipage(source) == [source]


# ---------------------------------------------------------------- platform gate
@pytest.mark.skipif(sys.platform == "win32", reason="Windows has real WIA")
def test_listing_devices_outside_windows_explains_itself():
    with pytest.raises(ScannerError) as info:
        list_devices()
    assert "only available on Windows" in info.value.message
    # The hint must point at the path that does work everywhere.
    assert "Add photos" in info.value.hint


@pytest.mark.skipif(sys.platform == "win32", reason="Windows has real WIA")
def test_acquire_outside_windows_raises_scanner_error():
    device = ScannerDevice(device_id="X", name="Test scanner")
    with pytest.raises(ScannerError):
        acquire_pages(device, folder="/tmp/does-not-matter")


def test_acquire_result_defaults_to_empty_warning_list():
    result = AcquireResult(pages=[])
    assert result.warnings == []
    assert result.feeder is False


def test_dpi_choices_include_the_app_default():
    assert scan_device.DEFAULT_DPI in scan_device.DPI_CHOICES
    assert scan_device.DEFAULT_DPI == 300


# ------------------------------------------------------- command construction
def test_script_is_run_as_a_file_never_after_dash_command():
    """Regression: 1.1.0 broke every scan with "Missing expression after '--'".

    PowerShell treats everything after ``-Command`` as command *text*, so a
    script passed there cannot receive arguments and any extra token is parsed
    as PowerShell.  The script must go through ``-File``.
    """
    command = powershell_command(
        "powershell.exe", "C:/Temp/smartscan.ps1", []
    )
    assert "-Command" not in command
    assert "-File" in command
    assert command[command.index("-File") + 1] == "C:/Temp/smartscan.ps1"


def test_no_stray_tokens_after_the_arguments():
    command = powershell_command("powershell.exe", "s.ps1", ["dev", "out", "300", ""])
    assert command[-4:] == ["dev", "out", "300", ""]
    # Nothing that PowerShell could read as an operator.
    assert not any(a == "--" for a in command)


def test_arguments_are_stringified():
    command = powershell_command("powershell.exe", "s.ps1", [300, True])
    assert command[-2:] == ["300", "True"]


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="uses a POSIX shell as a stand-in for powershell.exe; the real "
    "thing is exercised by the Windows CI job instead",
)
def test_arguments_reach_the_script_through_args(monkeypatch, tmp_path):
    """End-to-end on the script-file mechanism, without needing Windows.

    Replace the PowerShell binary with a shell that mimics ``-File`` +
    ``$args``: the script must receive every argument, in order.
    """
    fake = tmp_path / "fake-ps"
    # Everything before -File is consumed, exactly like PowerShell does.
    fake.write_text(
        '#!/bin/sh\n'
        'while [ $# -gt 0 ] && [ "$1" != "-File" ]; do shift; done\n'
        'shift  # consume -File itself\n'
        'script="$1"  # the script path, in the slot -File puts it in\n'
        'shift\n'
        'echo "script: $script argv: $@"\n'
    )
    fake.chmod(0o755)
    monkeypatch.setattr(scan_device, "IS_WINDOWS", True)
    monkeypatch.setattr(scan_device, "_powershell_exe", lambda: str(fake))

    output = _run_powershell("ignored", ["first", "second"])
    assert "argv: first second" in output
    # -File points at the temporary .ps1 that holds the script text.
    assert ".ps1" in output


# --------------------------------------------------- failure classification
def test_parser_error_is_reported_as_a_smartscan_bug_not_a_scanner_one():
    err = _diagnose_powershell_failure(
        "At C:\\Temp\\x.ps1:1 char:1\n+ --\n"
        "Missing expression after unary operator '--'.\n"
        "    + CategoryInfo : ParserError",
        returncode=1,
    )
    assert "helper script failed" in err.message.lower()
    assert "not a scanner problem" in err.hint.lower()


def test_execution_policy_block_is_explained():
    err = _diagnose_powershell_failure(
        "File cannot be loaded because running scripts is disabled", returncode=1
    )
    assert "blocked" in err.message.lower()
    assert ".ps1 is not digitally signed" in err.hint.lower() or "policy" in err.hint.lower()


def test_silent_failure_without_stderr_points_at_the_scanner():
    err = _diagnose_powershell_failure("", returncode=1)
    assert "did not answer the scanner" in err.message.lower()
