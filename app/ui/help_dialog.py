"""In-app "How to use" window.

The same text also ships as HOW-TO-USE.md / HOW-TO-USE.txt next to the app, so
users who never open the Help menu still find it.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

GUIDE_HTML = """
<h2>Scanning documents with SmartScan</h2>

<ol>
  <li><b>Get the images in.</b> Use <b>Scan from scanner…</b> (<b>Ctrl+Shift+N</b>) to pull
  pages directly from a scanner, or <b>Add photos…</b> (<b>Ctrl+O</b>), drag image files
  into the window, or paste a screenshot with <b>Ctrl+V</b>.
  You can also lay several small documents (receipts, cards, notes, invoices) on one
  surface and photograph them together.</li>
  <li><b>Check the outlines.</b> SmartScan finds each document automatically and draws a
  blue outline. The right-hand pane previews the straightened, cleaned-up page.
  Use <b>Re-detect</b> (Ctrl+R) if something was missed.</li>
  <li><b>Remove unwanted documents</b> by selecting them in the preview strip and pressing
  <b>E</b> (or the <b>Exclude</b> button).</li>
  <li><b>Scan &amp; Save.</b> Press <b>Scan &amp; Save</b> (Ctrl+S). Each page is straightened,
  enhanced and written to your folder in the chosen format.</li>
</ol>

<h3>Scanning from a scanner</h3>
<p>Press <b>Scan from scanner…</b>, choose the device and a resolution (300 DPI is right for
most work), then <b>Scan</b>. A document feeder pulls every page in the tray; on a flatbed
press <b>Scan again</b> for another page. This uses the scanner support built into Windows,
so no extra software is needed. If no scanner is listed, check it is switched on and
connected, then press <b>Look again</b>.</p>

<h3>Choosing the output folder</h3>
<p>SmartScan remembers the folder you pick. Use <b>Change…</b> next to <b>Save to</b>, the
<b>File → Choose output folder…</b> menu item (Ctrl+D), or the Settings dialog (Ctrl+,).
The toolbar's <b>Folder</b> button opens the folder in Explorer.</p>

<h3>Cleanup modes</h3>
<ul>
  <li><b>Auto</b> – picks Color for documents with photos or colour stamps, otherwise Gray. Start here.</li>
  <li><b>Color</b> – natural colour with a white background.</li>
  <li><b>Gray</b> – classic photocopier look, small files.</li>
  <li><b>B&amp;W</b> – highest contrast for plain text; smallest PDFs.</li>
  <li><b>Original</b> – only straightens the page, keeps everything else.</li>
</ul>

<h3>Tips for good results</h3>
<ul>
  <li>Keep documents flat, without overlapping, and inside the photo.</li>
  <li>A background that contrasts with the paper (a dark desk, a coloured mat) helps.</li>
  <li>Shoot from above; avoid strong shadows and glare.</li>
  <li>Each document needs its own visible outline – stacked pages are scanned as one.</li>
  <li>Higher-resolution photos produce sharper scans.</li>
</ul>

<h3>Keyboard shortcuts</h3>
<table cellpadding="4">
  <tr><td><b>Ctrl+O</b></td><td>Add photos</td></tr>
  <tr><td><b>Ctrl+Shift+N</b></td><td>Scan from scanner</td></tr>
  <tr><td><b>Ctrl+V</b></td><td>Paste image</td></tr>
  <tr><td><b>Ctrl+R</b></td><td>Re-detect documents in the current photo</td></tr>
  <tr><td><b>Ctrl+S</b></td><td>Scan &amp; Save</td></tr>
  <tr><td><b>Ctrl+D</b></td><td>Choose the output folder</td></tr>
  <tr><td><b>← / →</b></td><td>Previous / next page or photo</td></tr>
  <tr><td><b>E</b></td><td>Exclude / include the selected document</td></tr>
  <tr><td><b>Delete</b></td><td>Remove the selected photo</td></tr>
  <tr><td><b>Ctrl+,</b></td><td>Settings</td></tr>
  <tr><td><b>F1</b></td><td>This guide</td></tr>
</table>

<h3>Where are my files?</h3>
<p>Unless you change it, scans go to <b>Documents\\SmartScan</b> in your user folder.
File names follow the pattern from Settings, for example
<code>Scan_2026-11-20_14-05-33_1.pdf</code>.</p>
"""


class HelpDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("How to use SmartScan")
        self.resize(640, 620)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(GUIDE_HTML)
        browser.setStyleSheet("QTextBrowser { background: white; border: 1px solid #d7dbe3; border-radius: 8px; padding: 12px; }")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 12)
        layout.addWidget(browser)
        layout.addWidget(buttons)


def bundled_guide_dir() -> Path | None:
    """Directory holding HOW-TO-USE.md for this run.

    Inside a PyInstaller build the guide sits in the bundle's root
    (``sys._MEIPASS``); when run from source it lives in the project root.
    """
    import sys

    base = getattr(sys, "_MEIPASS", None)
    candidates = [Path(base)] if base else []
    candidates.append(Path(__file__).resolve().parents[2])
    for candidate in candidates:
        if (candidate / "HOW-TO-USE.md").is_file():
            return candidate
    return None


def write_guide_files(target_dir: Path) -> list[Path]:
    """Write the plain-text guide next to the executable (used by the installer)."""
    target_dir.mkdir(parents=True, exist_ok=True)
    text = (
        "SMARTSCAN - HOW TO USE\n"
        "======================\n\n"
        "1. Get the images in\n"
        "   'Scan from scanner...' (Ctrl+Shift+N) pulls pages from a scanner;\n"
        "   'Add photos...' (Ctrl+O) or drag files; Ctrl+V pastes a screenshot.\n"
        "   Several small documents can be in one photo.\n\n"
        "2. Check the outlines\n"
        "   Each document is detected automatically and outlined in blue.\n"
        "   The right pane previews the straightened, cleaned-up page.\n"
        "   Use 'Re-detect' (Ctrl+R) if a document was missed.\n\n"
        "3. Exclude what you do not need\n"
        "   Select a page in the preview strip and press E.\n\n"
        "4. Scan & Save\n"
        "   Press 'Scan & Save' (Ctrl+S). Pages are written to your folder\n"
        "   as PDF/JPG/PNG/TIFF, named from the pattern in Settings.\n\n"
        "SCANNER\n"
        "  Toolbar > 'Scan from scanner', pick the device and 300 DPI, press Scan.\n"
        "  A document feeder pulls every page; on a flatbed press 'Scan again'.\n"
        "  Uses the scanner support built into Windows - no extra software.\n\n"
        "OUTPUT FOLDER\n"
        "  'Change...' next to 'Save to', File > Choose output folder (Ctrl+D)\n"
        "  or Settings (Ctrl+,). Default: Documents\\SmartScan.\n\n"
        "CLEANUP MODES\n"
        "  Auto - smart choice (Color for photos/stamps, Gray for text)\n"
        "  Color - natural colour, white background\n"
        "  Gray - photocopier look, small files\n"
        "  B&W - maximum contrast for text\n"
        "  Original - straighten only\n\n"
        "TIPS\n"
        "  - Keep documents flat, not overlapping, inside the photo.\n"
        "  - A contrasting background (dark desk) detects best.\n"
        "  - Shoot from above; avoid shadows and glare.\n"
        "  - Higher-resolution photos give sharper scans.\n\n"
        "SHORTCUTS\n"
        "  Ctrl+O add photos   Ctrl+Shift+N scanner  Ctrl+V paste\n"
        "  Ctrl+R re-detect\n"
        "  Ctrl+S scan & save  Ctrl+D folder     Ctrl+, settings\n"
        "  Left/Right pages    E exclude         Delete remove photo\n"
        "  F1 this guide\n"
    )
    txt = target_dir / "HOW-TO-USE.txt"
    txt.write_text(text, encoding="utf-8")
    return [txt]
