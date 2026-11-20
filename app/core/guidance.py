"""Messages shown when a page is loaded or when nothing is found.

Deliberately free of Qt imports: the wording depends on where a page came
from, and it is worth testing that a *scan* is never given photo advice such
as "improve the lighting" — the scanner's lamp and lid are not the user's to
change.  Keeping it here also means these strings are tested on every commit
without a display.
"""

from __future__ import annotations

# Status bar, keyed by "was this page scanned?".
EMPTY_STATUS = {
    False: "No documents found — try a photo with better lighting and contrast.",
    True: "No documents found — the page may be almost the same brightness as the lid.",
}

PHOTO_EMPTY_HELP = (
    "SmartScan could not find a document outline in this photo.\n\n"
    "Tips:\n• Keep the whole document inside the frame\n"
    "• Use a plain, contrasting background\n"
    "• Avoid heavy shadows across the paper"
)

SCAN_EMPTY_HELP = (
    "SmartScan could not find a document outline in this scan.\n\n"
    "The page was scanned, so the lighting and the background are the scanner's own:\n"
    "• Paper almost as white as the lid is the usual cause —\n"
    "  put a coloured sheet or a dark mat behind the page and scan again\n"
    "• Check the page is not shifted off the glass\n"
    "• If the preview looks blank or grey, press Diagnose… in the scan dialog\n"
    "  and save the report"
)


def empty_status(is_scan: bool) -> str:
    """One-line status message for a page where nothing was found."""
    return EMPTY_STATUS[bool(is_scan)]


def empty_help(is_scan: bool) -> str:
    """The dialog body for a page where nothing was found."""
    return SCAN_EMPTY_HELP if is_scan else PHOTO_EMPTY_HELP
