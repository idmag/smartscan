"""Scanner (WIA) support for Windows.

SmartScan gets most of its input from phones and downloaded images, but a real
scanner on Windows exposes its pages through **WIA** (Windows Image
Acquisition), which ships with the OS - no drivers, no extra packages.

Talking to WIA from Python is possible through ``comtypes``/``pywin32``, but
that would add a dependency and, worse, a crash inside the scanner's COM
server would take SmartScan down with it.  Instead we drive WIA from a small
PowerShell script and exchange files through a temporary folder:

    SmartScan  --(temp dir)-->  PowerShell + WIA  -->  TIFF/JPEG page  -->  SmartScan

That keeps every hardware/driver failure inside a child process where it can be
reported as a message rather than an exception, and it works on any Windows 10
or 11 machine without Python packages being installed for COM.

This module holds the *platform-independent* half so it stays testable on
Linux: device parsing, the acquisition script, output discovery and friendly
error classification.  The GUI thread only ever calls :func:`list_devices` and
:func:`acquire_pages`, both of which run in a worker.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

# WIA item type for a whole scanner (as opposed to a child item such as a
# feeder slot).  Defined by the WIA automation model.
WIA_DEVICE_TYPE_SCANNER = 1

IS_WINDOWS = sys.platform == "win32"

# Requested DPI values offered in the UI.  300 matches the rest of the app.
DPI_CHOICES = (150, 200, 300, 600)
DEFAULT_DPI = 300


class ScannerError(RuntimeError):
    """A scanner problem with a message meant for the user."""

    def __init__(self, message: str, hint: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint

    def user_text(self) -> str:
        return f"{self.message}\n\n{self.hint}" if self.hint else self.message


@dataclass(frozen=True)
class ScannerDevice:
    """One WIA scanner."""

    device_id: str
    name: str
    # "feeder" when the device reports an automatic document feeder.
    kind: str = "flatbed"

    @property
    def label(self) -> str:
        suffix = " (document feeder)" if self.kind == "feeder" else " (flatbed)"
        return f"{self.name}{suffix}"


# --------------------------------------------------------------------------- #
# PowerShell scripts
# --------------------------------------------------------------------------- #
# Device discovery.  Emits one JSON object; WIA is only touched inside the
# try block so a missing WIA service yields a clean error, not a stack trace.
_LIST_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
try {
    $dm = New-Object -ComObject WIA.DeviceManager
    $out = @()
    foreach ($info in $dm.DeviceInfos) {
        if ([int]$info.Type -ne 1) { continue }
        $feeder = $false
        try {
            $dev = $info.Connect()
            foreach ($item in $dev.Items) {
                if ($item.Properties.Exists("3088")) { $feeder = $true }
            }
        } catch { }
        $out += [pscustomobject]@{
            id     = [string]$info.DeviceID
            name   = [string]$info.Properties.Item("Name").Value
            feeder = [bool]$feeder
        }
    }
    [pscustomobject]@{ ok = $true; devices = $out } | ConvertTo-Json -Compress -Depth 4
} catch {
    [pscustomobject]@{ ok = $false; error = [string]$_.Exception.Message } |
        ConvertTo-Json -Compress
}
"""

# Acquisition.  $args[0] = device id, $args[1] = output folder,
# $args[2] = dpi, $args[3] = "#RRGGBB" paper colour for the ADF's blank back
# page ("" lets WIA decide).  Pages are written as TIFF (lossless, colour) or,
# if the driver refuses TIFF, JPEG; multi-page TIFFs from a feeder are split
# afterwards by the caller.
_ACQUIRE_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$deviceId = $args[0]
$outDir   = $args[1]
$dpi      = [int]$args[2]
$paperBGR = $args[3]
$log = New-Object System.Collections.ArrayList
$count = 0
try {
    $dm = New-Object -ComObject WIA.DeviceManager
    $info = $null
    foreach ($i in $dm.DeviceInfos) {
        if ([int]$i.Type -eq 1 -and [string]$i.DeviceID -eq $deviceId) { $info = $i; break }
    }
    if ($null -eq $info) { throw "The scanner is no longer connected." }
    $device = $info.Connect()
    $feeder = $false
    try {
        foreach ($item in $device.Items) {
            if ($item.Properties.Exists("3088")) { $feeder = $true }
        }
    } catch { }

    $maxPages = 50
    while ($count -lt $maxPages) {
        # 4 = first page only (flatbed); 1 = next page (feeder)
        $scanType = if ($feeder) { 1 } else { 4 }
        $item = $device.Items.Item(1)
        $props = $item.Properties
        if ($props.Exists("6146")) { $props.Item("6146").Value = 1 }        # colour
        if ($props.Exists("6147")) { $props.Item("6147").Value = $dpi }     # horizontal DPI
        if ($props.Exists("6148")) { $props.Item("6148").Value = $dpi }     # vertical DPI
        if ($props.Exists("6151")) { $props.Item("6151").Value = 0 }        # no automatic deskew
        if ($props.Exists("6155")) { $props.Item("6155").Value = 1 }        # light source on
        if ($paperBGR -ne "" -and $props.Exists("3100")) {
            $props.Item("3100").Value = $paperBGR
        }
        $file = Join-Path $outDir ("page_{0:D3}" -f $count)
        try {
            $image = $item.Transfer("{B96B3CB0-0728-11D3-9D7B-0000F81EF32E}")  # TIFF
            $image.SaveFile($file + ".tif")
        } catch {
            $image = $item.Transfer("{B96B3CAE-0728-11D3-9D7B-0000F81EF32E}")  # JPEG
            $image.SaveFile($file + ".jpg")
        }
        $count++
        [void]$log.Add("page $count saved")
        if (-not $feeder) { break }
        # WIA throws when the ADF runs dry; that is the normal end of a batch.
        # The status probe is best-effort: many drivers omit property 3088 and
        # a missing property must not abort a healthy batch.
        $status = -1
        try {
            if ($device.Properties.Exists("3088")) {
                $status = [int]$device.Properties.Item("3088").Value
            }
        } catch { $status = -1 }
        if ($status -ne -1 -and $status -ne 1 -and $status -ne 5) { break }
        Start-Sleep -Milliseconds 400
    }
    [pscustomobject]@{ ok = $true; pages = $count; feeder = $feeder; log = $log } |
        ConvertTo-Json -Compress
} catch {
    $message = [string]$_.Exception.Message
    # "paper empty" after at least one page is a finished batch, not a failure.
    $dry = $message -match '(?i)paper|empty|no document|feed|0x8021006B|80210003'
    if ($count -gt 0 -and $dry) {
        [pscustomobject]@{ ok = $true; pages = $count; feeder = $feeder; log = $log } |
            ConvertTo-Json -Compress
    } else {
        [pscustomobject]@{
            ok = $false; pages = $count; error = $message; feeder = $feeder
        } | ConvertTo-Json -Compress
    }
}
"""


def powershell_command(exe: str, script_path: str, arguments: list[str]) -> list[str]:
    """Build the command line that runs a script file with arguments.

    The script must be a **file** passed with ``-File``, never text after
    ``-Command``: PowerShell swallows everything following ``-Command`` as part
    of the command text, so arguments disappear and stray tokens are parsed as
    operators (a trailing ``--`` produced "Missing expression after unary
    operator").  ``-File`` passes arguments through to ``$args`` as documented.

    Kept separate so a test can assert the ordering.
    """
    return [
        exe,
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy", "Bypass",
        "-File", str(script_path),
        *[str(a) for a in arguments],
    ]


def _powershell_exe() -> str:
    return shutil.which("powershell.exe") or shutil.which("powershell") or "powershell.exe"


def _run_powershell(script: str, arguments: list[str], timeout: float = 300.0) -> str:
    """Run *script* in PowerShell, passing *arguments* via ``$args``."""
    if not IS_WINDOWS:
        raise ScannerError(
            "Scanning from a scanner is only available on Windows.",
            "Use \"Add photos\" to import images the scanner's own software saved.",
        )
    # A UTF-8 BOM keeps non-ASCII device names intact on PowerShell 5.1, which
    # otherwise assumes the system ANSI code page for BOM-less script files.
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".ps1", delete=False, encoding="utf-8-sig"
    )
    try:
        handle.write(script)
        handle.close()
        command = powershell_command(_powershell_exe(), handle.name, arguments)
        creation = 0
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            creation = subprocess.CREATE_NO_WINDOW  # do not flash a console window
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=creation,
            )
        except subprocess.TimeoutExpired as exc:  # pragma: no cover - hardware path
            raise ScannerError(
                "The scanner did not finish in time.",
                "Check that the scanner is switched on and connected, then try again.",
            ) from exc
    finally:
        try:
            os.unlink(handle.name)
        except OSError:
            pass

    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()
    if not stdout:
        raise _diagnose_powershell_failure(stderr or "", completed.returncode)
    return stdout


def _diagnose_powershell_failure(stderr: str, returncode: int) -> ScannerError:
    """Turn a silent PowerShell run into a message that names the real culprit.

    A failure inside *our* script (a syntax error, a blocked policy) must never
    be reported as a scanner problem - that sends the user hunting for a loose
    cable when the bug is ours.
    """
    lowered = stderr.lower()
    if "parsererror" in lowered or "missingexpression" in lowered:
        first = next((ln.strip() for ln in stderr.splitlines() if ln.strip()), "")
        return ScannerError(
            "The scanner helper script failed to run.",
            f"{first[:300]}\n\nThis is a SmartScan problem, not a scanner problem - "
            "please report it.",
        )
    if (
        "executionpolicy" in lowered
        or "not digitally signed" in lowered
        or "running scripts is disabled" in lowered
        or "scripts is disabled on this system" in lowered
    ):
        return ScannerError(
            "Windows blocked the scanner helper script.",
            "Your organisation's PowerShell policy is blocking scripts. Ask an "
            "administrator, or use \"Add photos\" for images saved by the scanner "
            "software.",
        )
    if stderr:
        return ScannerError(
            "Windows could not run the scanner helper.",
            stderr.splitlines()[0][:300],
        )
    return ScannerError(
        "Windows did not answer the scanner.",
        "Check that the scanner is switched on and connected, then try again.",
    )


def _last_json_object(text: str) -> dict:
    """PowerShell may prepend warnings; take the last JSON object it printed."""
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                return json.loads(line)
            except ValueError:
                continue
    raise ScannerError(
        "Unexpected answer from Windows while talking to the scanner.",
        "Try again, or use \"Add photos\" for images saved by the scanner software.",
    )


def _parse_devices(payload: dict) -> list[ScannerDevice]:
    devices: list[ScannerDevice] = []
    for raw in payload.get("devices") or []:
        if isinstance(raw, dict):
            name, device_id = raw.get("name"), raw.get("id")
        else:  # a single device is serialised as an object, not an array
            name, device_id = getattr(raw, "name", None), getattr(raw, "id", None)
        if not name or not device_id:
            continue
        kind = "feeder" if raw.get("feeder") else "flatbed"
        devices.append(ScannerDevice(device_id=str(device_id), name=str(name), kind=kind))
    return devices


def parse_device_list(output: str) -> list[ScannerDevice]:
    """Turn the discovery script's stdout into devices (empty when none)."""
    payload = _last_json_object(output)
    if not payload.get("ok"):
        raise ScannerError(
            "Windows could not list the scanners.",
            str(payload.get("error") or "")[:400]
            or "Check that the Windows Image Acquisition service is running.",
        )
    return _parse_devices(payload)


def list_devices() -> list[ScannerDevice]:
    """All scanners Windows reports.  Blocking: call from a worker thread."""
    return parse_device_list(_run_powershell(_LIST_SCRIPT, [], timeout=60.0))


# --------------------------------------------------------------------------- #
# Acquisition
# --------------------------------------------------------------------------- #
@dataclass
class AcquireResult:
    pages: list[Path]
    feeder: bool = False
    warnings: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.warnings is None:
            self.warnings = []


def parse_acquire_output(output: str, folder: Path) -> AcquireResult:
    """Collect the files a finished acquisition left in *folder*."""
    payload = _last_json_object(output)
    pages = sorted(
        p for p in folder.glob("page_*") if p.suffix.lower() in {".tif", ".tiff", ".jpg", ".jpeg", ".png", ".bmp"}
    )
    feeder = bool(payload.get("feeder"))
    if not payload.get("ok"):
        message = str(payload.get("error") or "The scanner reported an error.")
        raise ScannerError(describe_wia_error(message), "Check the scanner, then try again.")
    if not pages:
        raise ScannerError(
            "The scanner reported success but sent no image.",
            "If the document feeder is empty, load the pages and try again.",
        )
    return AcquireResult(pages=pages, feeder=feeder)


def describe_wia_error(message: str) -> str:
    """Map WIA/driver text onto something a user can act on."""
    text = (message or "").strip()
    lowered = text.lower()
    if "0x8021006b" in lowered or "paper" in lowered and "empty" in lowered:
        return "The document feeder is empty."
    if "0x80210003" in lowered or "offline" in lowered or "not connected" in lowered:
        return "The scanner is offline or not connected."
    if "0x80210015" in lowered or "busy" in lowered:
        return "The scanner is busy — another program may be using it."
    if "0x80210005" in lowered or "denied" in lowered or "access" in lowered:
        return "Windows refused access to the scanner."
    if "cancel" in lowered:
        return "The scan was cancelled."
    if not text:
        return "The scanner reported an unknown error."
    return f"The scanner reported: {text[:300]}"


def acquire_pages(
    device: ScannerDevice | str,
    *,
    dpi: int = DEFAULT_DPI,
    paper_hex: str = "",
    folder: Path | None = None,
    timeout: float = 300.0,
) -> AcquireResult:
    """Scan from *device* into *folder* (a temp dir when not given).

    Blocking; call from a worker thread.  The caller owns *folder* and should
    delete it once the images have been loaded.
    """
    device_id = device.device_id if isinstance(device, ScannerDevice) else str(device)
    target = Path(folder) if folder is not None else Path(tempfile.mkdtemp(prefix="smartscan_scan_"))
    target.mkdir(parents=True, exist_ok=True)
    dpi = int(dpi) if int(dpi) in DPI_CHOICES else DEFAULT_DPI
    # WIA wants BGR order in a "#BBGGRR" string; the UI speaks RGB.
    paper = ""
    if paper_hex:
        value = paper_hex.lstrip("#")
        if len(value) == 6:
            paper = f"#{value[4:6]}{value[2:4]}{value[0:2]}"
    started = time.perf_counter()
    output = _run_powershell(
        _ACQUIRE_SCRIPT, [device_id, str(target), str(dpi), paper], timeout=timeout
    )
    result = parse_acquire_output(output, target)
    if result.feeder and dpi >= 600:
        result.warnings.append(
            "High resolution from a document feeder can be slow; 300 DPI is usually enough."
        )
    elapsed = time.perf_counter() - started
    if not result.pages:
        raise ScannerError("Nothing was scanned.", f"Gave up after {elapsed:.0f}s.")
    return result


def split_multipage(path: Path) -> list[Path]:
    """Split a multi-page TIFF into single-page files next to it.

    Some WIA drivers ignore "first page only" and hand back one TIFF holding
    every page; the rest of the app expects one image per page.
    """
    suffix = path.suffix.lower()
    if suffix not in {".tif", ".tiff"}:
        return [path]
    try:
        from PIL import Image, ImageSequence
    except Exception:  # pragma: no cover - Pillow is a hard dependency
        return [path]
    try:
        with Image.open(path) as image:
            frames = [frame.copy() for frame in ImageSequence.Iterator(image)]
    except Exception:
        return [path]
    if len(frames) <= 1:
        return [path]
    out: list[Path] = []
    for index, frame in enumerate(frames):
        target = path.with_name(f"{path.stem}_{index + 1}{path.suffix}")
        frame.save(target)
        out.append(target)
    try:
        path.unlink()
    except OSError:
        pass
    return out
