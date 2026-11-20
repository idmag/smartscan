# How to use SmartScan

SmartScan turns a photo of several small documents into clean, straightened scans and
saves them to your folder.

## The four steps

1. **Get the images in** — three ways, all equivalent:
   - **Scan from scanner…** (Ctrl+Shift+N) pulls pages straight from a scanner connected
     to this PC, one page or a whole document feeder.
   - **Add photos…** (Ctrl+O) or drag image files onto the window.
   - **Ctrl+V** pastes a screenshot.

   One photo can hold several documents.
2. **Check the outlines** — every document is found automatically and outlined in blue;
   the right pane previews the straightened page. Drag a corner handle to fix an outline,
   or press **Re-detect** (Ctrl+R) to try again.
3. **Drop what you don't want** — select a page in the strip along the bottom and press
   **E** (or **Exclude**).
4. **Scan & Save** — press **Scan & Save** (Ctrl+S). The pages are straightened, cleaned
   up, and written to the output folder.

## Scanning from a scanner

Press **Scan from scanner…** in the toolbar (or **File → Scan from scanner…**). Pick the
device, choose a resolution (300 DPI is right for most work), load the pages, and press
**Scan**. A document feeder pulls every page in the tray; on a flatbed, press **Scan
again** for the next page. Scanned pages then behave exactly like photos: outlines are
detected, previewed, and saved with everything else.

SmartScan uses the scanner support built into Windows (WIA), so no extra driver or
software is needed beyond what Windows already installed for your scanner. If no
scanner is listed, check it is switched on and connected, then press **Look again**.

Documents are found whether they are lighter or darker than what they lie on, so a
coloured card on a white scanner lid works. On a table, white paper on a pale surface is
also found: paper is smooth where a desk has grain, and that difference is used when the
colours are too close to judge. Paper that is almost exactly the lid's own white — a few
grey levels away — cannot be separated from it; lay a coloured sheet behind such pages.

If a scan fails, press **Diagnose…** and save the report — it lists what your scanner
driver supports, which is what's needed to fix it.

## The output folder

Use **Change…** next to **Save to**, **File → Choose output folder…** (Ctrl+D), or
**Settings** (Ctrl+,). SmartScan remembers your choice, so you only do this once.
**Open folder** shows the results. The default is `Documents\SmartScan`.

## Cleanup modes

| Mode | Use it for |
| --- | --- |
| **Auto** | Start here — Color when the document has photos or stamps, Gray otherwise. |
| **Color** | Natural colour on a white background. |
| **Gray** | Photocopier look; small files. |
| **B&W** | Maximum contrast for plain text; smallest PDFs. |
| **Original** | Straightening only, everything else untouched. |

## File formats

Pick the format in **Settings**. **PDF** puts the whole batch into one multi-page
document; **JPG**, **PNG** and **TIFF** save one file per page. All scans are 300 DPI.
File names follow a template, for example `Scan_2026-11-20_14-05-33_1.pdf`.

## Getting the best results

- Lay the documents flat, **not overlapping**, fully inside the photo.
- A background that contrasts with the paper detects best — a dark desk or a coloured mat.
- Photograph from above; avoid strong shadows and glare.
- More megapixels give sharper scans.

## Keyboard shortcuts

| Keys | Action |
| --- | --- |
| Ctrl+O | Add photos |
| Ctrl+V | Paste an image |
| Ctrl+R | Re-detect documents in the current photo |
| Ctrl+S | Scan & Save |
| Ctrl+D | Choose the output folder |
| ← / → | Previous / next page or photo |
| E | Exclude / include the selected document |
| Delete | Remove the selected photo |
| Ctrl+, | Settings |
| F1 | This guide |

The same guide is in the app under **Help → How to use** (F1), and as
`HOW-TO-USE.txt` next to the installed program.
