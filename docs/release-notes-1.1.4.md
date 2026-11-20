## SmartScan 1.1.4

### Better detection on pale desks

SmartScan can now use surface texture as additional evidence when a document is too close in brightness to its background. Smooth paper on a gently textured desk can be found even when brightness alone is inconclusive.

This is a deliberately narrow fallback: the surrounding texture must measure between 1.5 and 8 grey levels, and the interior must be no more than 45% as rough. Existing brightness and edge checks remain in place. Regression tests cover empty desks and boxes printed inside pages as well as real document boundaries.

The quad-fitting fallback also no longer relies on NumPy's removed support for 2D cross products.

### Advice that fits the source

When no documents are found, scanner pages now receive scan-specific advice, including using a contrasting backing and the scanner diagnostic tool. Photographs retain advice about framing, contrast and shadows. The page list also identifies scanner and clipboard sources.

### Known limitations

Light-grey paper on a light-grey desk is still not detected reliably in every test scene. Texture evidence is not a guarantee: paper size, printed content, image resolution and background texture affect it.

White paper on a nearly identical white scanner lid remains difficult to separate. Put a contrasting coloured sheet or dark mat behind the documents and scan again.

### Validation

The local suite passes 104 tests. New coverage includes source-aware guidance, low-contrast paper, empty desks, internal printed boxes, a multi-shape/background/tint sweep and a separate regression measurement for the remaining light-grey-on-grey gap. Physical scanner and Windows GUI testing still require Windows hardware.

### Upgrading

Install over the previous version. Settings are kept.
