"""Turning a photo + detected quads into finished scanned pages.

Kept free of Qt so it can be tested headlessly and reused by a CLI.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

from .enhance import enhance
from .naming import DEFAULT_TEMPLATE, render_name, unique_path
from .perspective import auto_upright, estimate_paper_aspect, quad_to_image

# 300 dpi is the usual "document scan" quality.  Small crops are upscaled a
# little for readability, but never far: interpolation adds no detail, it only
# makes text look bigger (and the PDF larger).
SCAN_DPI = 300
MAX_UPSCALE = 1.6
MAX_LONG_SIDE = 4500

# Nominal physical width (mm) for known paper shapes, used to pick output px.
_PAPER_WIDTH_MM = {
    "A4": 210.0,
    "Letter": 215.9,
    "A5": 148.0,
    "Legal": 215.9,
    "receipt": 80.0,
    "card": 85.6,
}


@dataclass
class Page:
    """A page ready to be saved."""

    image: np.ndarray                 # BGR
    source: str = ""
    note: str = ""
    dpi: int = SCAN_DPI

    @property
    def width(self) -> int:
        return int(self.image.shape[1])

    @property
    def height(self) -> int:
        return int(self.image.shape[0])


@dataclass
class SaveResult:
    files: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def output_size_for(quad_width: float, quad_height: float) -> tuple[int, int, float | None]:
    """Pick output pixel dimensions and the paper aspect to snap to.

    The returned aspect is only used when the measured quad is *already* close
    to a known paper shape.  Shaping a quad with a very different proportion
    would have to invent or drop area -- pulling background into the page --
    so in that case the measured proportions are kept.
    """
    width = max(1.0, float(quad_width))
    height = max(1.0, float(quad_height))
    longest = max(width, height)
    aspect = estimate_paper_aspect(width, height)
    if aspect is not None:
        measured = height / width
        closeness = abs(math.log(measured / aspect))
        if closeness > math.log(1.30):
            aspect = None  # too far from any known paper, keep as measured

    if aspect is None:
        # Unknown shape: ~300 dpi-ish on the long side, but never invent pixels.
        target_long = min(MAX_LONG_SIDE, max(900.0, longest * 1.45))
        if height >= width:
            out_h = min(target_long, height * MAX_UPSCALE)
            out_w = out_h * width / height
        else:
            out_w = min(target_long, width * MAX_UPSCALE)
            out_h = out_w * height / width
        return max(1, int(round(out_w))), max(1, int(round(out_h))), None

    paper_name = _paper_name_for(aspect)
    width_mm = _PAPER_WIDTH_MM.get(paper_name, 210.0)
    target_short = width_mm / 25.4 * SCAN_DPI
    target_long = target_short * aspect
    portrait = height >= width
    if portrait:
        out_h = min(target_long, height * MAX_UPSCALE, MAX_LONG_SIDE)
        out_w = out_h / aspect
    else:
        out_w = min(target_long, width * MAX_UPSCALE, MAX_LONG_SIDE)
        out_h = out_w * aspect
    return max(1, int(round(out_w))), max(1, int(round(out_h))), aspect


def _paper_name_for(aspect: float) -> str:
    known = {
        "A4": 297 / 210,
        "Letter": 279.4 / 215.9,
        "A5": 210 / 148,
        "Legal": 355.6 / 215.9,
        "receipt": 3.2,
        "card": 85.6 / 53.98,
    }
    return min(known, key=lambda k: abs(math.log(aspect / known[k])))


def scan_page(
    photo: np.ndarray,
    quad: np.ndarray,
    *,
    mode: str = "magic",
    margin_px: int = 0,
    deskew: bool = True,
) -> Page:
    """Dewarp, upright and enhance one document from *photo*."""
    quad = np.asarray(quad, np.float32)
    width = float(
        (np.linalg.norm(quad[1] - quad[0]) + np.linalg.norm(quad[2] - quad[3])) / 2.0
    )
    height = float(
        (np.linalg.norm(quad[3] - quad[0]) + np.linalg.norm(quad[2] - quad[1])) / 2.0
    )
    out_w, out_h, aspect = output_size_for(width, height)

    warped = quad_to_image(
        photo,
        quad,
        margin_px=margin_px,
        out_size=(out_w, out_h),
    )
    if deskew:
        warped = auto_upright(warped)
    final = enhance(warped, mode)
    return Page(image=final)


def scan_many(
    photo: np.ndarray,
    quads: list[np.ndarray],
    *,
    mode: str = "magic",
    margin_px: int = 0,
    progress=None,
) -> list[Page]:
    pages: list[Page] = []
    for i, quad in enumerate(quads):
        pages.append(scan_page(photo, quad, mode=mode, margin_px=margin_px))
        if progress is not None:
            progress(i + 1, len(quads))
    return pages


# --------------------------------------------------------------------------- #
# Saving
# --------------------------------------------------------------------------- #
def to_pil(page: Page, *, for_pdf: bool = False) -> Image.Image:
    """Convert a page to PIL. B&W pages become 1-bit images for tiny PDFs."""
    arr = page.image
    if for_pdf and _is_bilevel(arr):
        import cv2

        gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
        return Image.fromarray(gray, mode="L").convert("1")
    return Image.fromarray(arr[:, :, ::-1], mode="RGB")


def _is_bilevel(image: np.ndarray) -> bool:
    """True when the page is pure black & white (the B&W enhancement mode)."""
    if image.size == 0:
        return False
    sample = image[:: max(1, image.shape[0] // 200), :: max(1, image.shape[1] // 200)]
    unique = np.unique(sample)
    return len(unique) <= 2 and set(np.ravel(unique).tolist()).issubset({0, 255})


def save_pages(
    pages: list[Page],
    out_dir: str | Path,
    *,
    fmt: str = "pdf",
    name_template: str = DEFAULT_TEMPLATE,
    jpeg_quality: int = 90,
    combine_pdf: bool = True,
    when: datetime | None = None,
) -> SaveResult:
    """Write *pages* into *out_dir* using the chosen format."""
    folder = Path(out_dir).expanduser()
    result = SaveResult()
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        result.errors.append(f"Cannot create output folder {folder}: {exc}")
        return result
    if not pages:
        result.errors.append("No pages to save.")
        return result

    fmt = fmt.lower()
    when = when or datetime.now()
    try:
        if fmt == "pdf" and combine_pdf:
            stem = render_name(name_template, index=1, total=len(pages), when=when)
            path = unique_path(folder, stem, "pdf")
            images = [to_pil(p, for_pdf=True) for p in pages]
            images[0].save(
                path,
                "PDF",
                save_all=True,
                append_images=images[1:],
                resolution=float(pages[0].dpi),
                quality=int(jpeg_quality),
            )
            result.files.append(path)
            return result

        suffix = {"pdf": "pdf", "jpg": "jpg", "jpeg": "jpg", "png": "png", "tiff": "tiff"}.get(fmt)
        if suffix is None:
            result.errors.append(f"Unsupported format: {fmt}")
            return result
        for i, page in enumerate(pages, start=1):
            stem = render_name(name_template, index=i, total=len(pages), when=when)
            path = unique_path(folder, stem, suffix)
            image = to_pil(page)
            if suffix in ("jpg", "pdf"):
                image.save(path, "JPEG" if suffix == "jpg" else "PDF",
                           quality=int(jpeg_quality), resolution=float(page.dpi))
            elif suffix == "png":
                image.save(path, "PNG", dpi=(page.dpi, page.dpi))
            else:
                image.save(path, "TIFF", compression="tiff_lzw", dpi=(page.dpi, page.dpi))
            result.files.append(path)
    except Exception as exc:  # noqa: BLE001 - surfaced to the user in the UI
        result.errors.append(f"Saving failed: {exc}")
    return result


def estimate_size_bytes(pages: list[Page], fmt: str, jpeg_quality: int = 90) -> int:
    """Rough size estimate for the UI (no disk writes)."""
    import io

    total = 0
    for page in pages[:3]:
        buf = io.BytesIO()
        image = to_pil(page)
        if fmt in ("jpg", "pdf"):
            image.save(buf, "JPEG", quality=int(jpeg_quality))
        elif fmt == "png":
            image.save(buf, "PNG")
        else:
            image.save(buf, "TIFF", compression="tiff_lzw")
        total += buf.tell()
    if len(pages) > 3:
        total = int(total / min(3, len(pages)) * len(pages))
    return total
