## What's new in 1.1.4

### Paper on a plain, light surface is found

1.1.3 taught SmartScan that a document can be **darker** than the scanner lid. This
release handles the quieter version of the same problem in photographs: **white paper
lying on a pale desk, a beige table or a light-grey mat**, where the paper is only
15–31 grey levels brighter than the surface under it. That is below the 35-level floor,
so 1.1.3 reported "No documents found" on a page that was plainly there.

Brightness is genuinely ambiguous at that margin — a pale desk and white paper are
nearly the same colour, whatever the lighting. **Surface texture is not.** Paper is
smooth; a tabletop is not. On the image SmartScan actually analyses:

| Surface | Roughness just outside the page | Inside the page |
| --- | --- | --- |
| Dark desk | 7.6 | 0.7 |
| Wooden desk | 4.8 | 0.7 |
| Light-grey desk | 2.6 | 0.7 |
| Scanner lid (no grain) | 1.9 | 0.7 |

A page is now accepted when it sits on a **gently textured** surface (2–8 grey levels)
and its own interior is less than **45 %** as rough. The two limits matter:

- A surface *rougher* than 8 grey levels is a printed or patterned cloth, where this
  measure says little — those keep using brightness alone.
- The ring must be gently rough. Ink on a page also leaves a "smooth interior with a
  rough ring around it" signature; the amplitude is what tells a desk from a page of
  text (desks measure 2–8, text rings 15 and up).
- A scanner lid is uniform and *not* textured (about 1.9), so a scan never depends on
  this path — and dust on the glass cannot trigger it.

### Still rejected

- Boxes and rules **inside** a page — verified on low-contrast scenes as well as the
  cropped-scan case from 1.1.3.
- Bare tabletops: 24 empty desk photographs, in all three surface types, produce no
  documents at all.
- Scanned pages behave exactly as in 1.1.3.

### Known limitation

**Light-grey paper on a light-grey desk is still only partly solved.** In small scenes
the paper's own noise (2.4 grey levels) and the desk's (3.2) are too close for a 3-pixel
measure to separate; about 10 of 12 scenes are found. The scale of that measure is set
by the image's working size, so this is a resolution limit rather than a logic one. The
suite records the real number and fails if it drifts, or if the gap closes.

### A message that fits

When nothing is found in a page that came from the scanner, the advice used to talk
about "this photo", better lighting and shadows — none of which you control on a
scanner. The dialog and status line now say where the page came from:

- **Scanned:** the page may be almost the same brightness as the lid; put a coloured
  sheet or a dark mat behind it and scan again; check it is not off the glass; press
  **Diagnose…** if the preview looks blank.
- **Photographed:** keep the whole page in frame, use a plain contrasting surface,
  avoid heavy shadows.

The page list also marks each entry **scanner** or **clipboard**, so it is clear what you
are looking at.

### Tests

**103 tests** (8 new). The detection sweep now covers four paper shapes (A5, A6, a
receipt, a business card) on three desk surfaces at three paper tints — 72 scenes — with
one explicitly pinned known gap. Empty-desk and internal-box negatives run alongside.

### Upgrading

Install over 1.1.3. Settings are kept.
