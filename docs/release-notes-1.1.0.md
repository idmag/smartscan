## What's new in 1.1.0

### Scan straight from a scanner

**File → Scan from scanner…** (Ctrl+Shift+N) now pulls pages directly from any scanner
Windows knows about — no separate scanning program, no image files to shuffle.

- **Document feeders:** load the tray, press **Scan** once, and every page is pulled and
  added as its own photo. Flatbeds scan one page per press of **Scan again**.
- **Resolution:** 150 / 200 / 300 / 600 DPI. 300 DPI matches the rest of the app.
- **Remembers your scanner**, so the device is preselected next time.
- Scanned pages go through exactly the same automatic detection, preview, and
  **Scan & Save** as photos.

It uses **WIA**, the scanner interface built into Windows 10 and 11, so nothing extra is
installed. If a scanner is not listed, the dialog says what to check and offers
**Look again** — and **Add photos** still works for images your scanner's own software
saves.

### Under the hood

- The scanner is driven from a short PowerShell script in a child process, so a
  misbehaving driver produces a readable message ("The document feeder is empty",
  "The scanner is busy — another program may be using it") instead of freezing or
  crashing the app.
- Multi-page TIFFs from drivers that ignore "first page only" are split into one file per
  page automatically.
- WIA error codes are translated into plain English.
- 23 new tests cover device listing, output parsing, error mapping, TIFF splitting, and
  the non-Windows fallback — 62 tests in total.

### Upgrading

Install over the previous version; your saved output folder, format and scanner choice
are kept.
