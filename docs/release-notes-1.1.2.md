## What's fixed in 1.1.2

### "The parameter is incorrect" when scanning

Version 1.1.1 reached your scanner — it was listed as `HP LaserJet M1005 MFP (flatbed)` —
then failed with `E_INVALIDARG` before any page was transferred.

The cause was a wrong property ID in the scanner script. It wrote `0` to **WIA property
6151**, believing that switched off automatic deskew. 6151 is actually
**`WIA_IPS_XEXTENT` — the horizontal scan width in pixels**, and `0` is not a valid width,
so the driver rejected it. The same block also wrote 6155 as if it were the lamp; 6155 is
**`WIA_IPS_CONTRAST`**.

In 1.1.2 the script only ever sets the three properties every scanner must support:
**`CUR_INTENT` (6146), `XRES` (6147), `YRES` (6148)**. Extents, deskew, lamp and contrast
are left to the driver — SmartScan crops and straightens the page itself, so the scanner
never needs to.

### Also fixed: a bug that would have broken the next step

The transfer asked for "TIFF" using the GUID `B96B3CB0`, which is **GIF**; TIFF is
`B96B3CB1`. A file named `.tif` would have held GIF bytes, which the rest of the app
cannot open — a successful scan followed by "not a readable image". Every page is now
opened and checked as soon as it arrives, so this class of fault is caught at scan time.

### Robustness

- **Every property write is individually guarded.** One unsupported or out-of-range value
  can no longer sink a whole scan.
- **Automatic fallback:** if the requested settings fail, the driver's untouched defaults
  are tried (reconnecting restores them), then a lower resolution. A scan at 200 DPI beats
  an error dialog, and the dialog tells you when it happened.
- **Formats are tried in order:** TIFF, PNG, BMP, JPEG — older WIA 1.0 drivers often refuse
  TIFF outright and only handle BMP.
- **The failure message is actionable.** Instead of "The parameter is incorrect" you get
  the offending property and what to do next.

### New: "Diagnose…" button

The scanner dialog can now save a **report of everything the driver exposes** — every
property, its current value, its valid range or list, and which settings it accepted or
refused. It is written to a text file you can send with a bug report.

This exists because the scanner path cannot be tested without the hardware: three rounds
of guesswork would have been one round with this file.

### Tests

**82 tests** (13 new). The new ones pin the WIA constants to Microsoft's documented values,
so writing a property like 6151 again fails the build rather than your scan:

- `WIA_IPS_XEXTENT` / `WIA_IPS_CONTRAST` must never be written;
- only 6146/6147/6148 may be set, and only via named constants;
- the TIFF GUID must be `…CB1` and `…CB0` must not appear;
- the defaults and 200-DPI fallbacks must exist;
- unreadable or mislabelled pages are rejected or skipped.

### Upgrading

Install over 1.1.1. Settings are kept.

> Still unverified: an actual scan on your HP M1005. If it fails again, press
> **Diagnose…**, save the report and send it — the property table will show exactly what
> that driver wants instead of us guessing.
