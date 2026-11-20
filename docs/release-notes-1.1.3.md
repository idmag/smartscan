## What's fixed in 1.1.3

### "No documents found" after a successful scan

Version 1.1.2 made the scanner work: your HP LaserJet M1005 produced a real 300 DPI page,
and the picture of the postcard on the glass was plainly there. SmartScan then said
**"No documents found"**.

The finder only accepted a document if it was **brighter than its surroundings** — an
assumption that holds when you photograph paper on a desk, and fails completely on a
scanner. A flatbed lid is white, so a coloured, grey or printed document lying on it is
*darker*, not brighter. Your postcard measured **−53 grey levels** against the lid: a
perfect, unmistakable outline, thrown away for having the wrong sign. The detector was
never wrong about *where* the card was — it scored the outline a perfect 1.00 overlap
with the card — it just refused to believe it.

### What changed

A document is now accepted when it stands out from its surroundings **in either
direction**, subject to the evidence being as strong:

| Situation | Required step | Measured |
| --- | --- | --- |
| Photo: light paper on a desk | brighter by **35** grey levels | +50 to +190 |
| Scan: document on a white lid | darker by **28** grey levels | −41 to −59 |
| Shadows, wood grain, mask noise | rejected | 7 to 16 |
| A page's own boxes and rules | rejected | −17 to +29 |

- **Two thresholds, because the two cases are not equally ambiguous.** On a photo, light
  patches in the background are common, so the brighter direction keeps the higher bar.
  A scanner lid is uniform, so the darker direction can be judged more finely — but it
  must still show a real brightness step, never an outline alone. A crisp rectangle drawn
  *inside* a page has no brightness step, and stays rejected.
- **Edge evidence is required for candidates the geometry is unsure about.** A quad that
  is darker than its surroundings was not what the page masks were tuned for, so it must
  sit on a genuinely strong edge (roughly twice the score needed in the bright case),
  otherwise it is discarded.
- **One bad candidate can no longer spoil the rest.** Scores are normalised against the
  strongest *substantial* candidate in the frame. Previously a few tiny, high-contrast
  specks of dust on the glass set the scale, and a real page — which has a soft, wide
  edge — was rated far too low and dropped.
- **Edge evidence now carries most of the score,** so two pages in one frame separate on
  their own outlines instead of competing on size alone.

### Known limitation

Paper that is only a few grey levels away from the lid — white paper on a white scanner
lid, measured at −6 to −12 — is still not found, and no brightness threshold can find it.
Lay a coloured sheet or a dark mat behind such pages, or leave the lid open and
photograph the bed.

### Tests

**87 tests** (5 new), run against simulated flatbed scenes as well as photos:

- the yellow postcard from your scan is found (synthetic lid, perfect overlap);
- a grey card on the same lid is found;
- two cards side by side are found as two separate documents;
- an **empty** scanner bed produces no documents;
- rectangles *inside* a page are still rejected.

The 24-photo regression sweep is unchanged: 21 of 24 found perfectly, exactly as before
this change, so photographs are not affected.

### Upgrading

Install over 1.1.2. Settings are kept.
