"""Generate the SmartScan application icon (run once; output is committed).

    python assets/make_icon.py

Produces assets/smartscan.ico (Windows, multi-size), assets/smartscan.png and
build-time PNG sizes referenced by the PyInstaller spec.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ACCENT = (37, 99, 235, 255)
ACCENT_DARK = (29, 78, 216, 255)
WHITE = (255, 255, 255, 255)
AMBER = (245, 158, 11, 255)
GREY = (203, 213, 225, 255)


def draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    margin = int(size * 0.10)
    radius = int(size * 0.20)
    d.rounded_rectangle(
        [margin, margin, size - margin, size - margin], radius=radius, fill=ACCENT
    )
    # subtle top highlight
    d.rounded_rectangle(
        [margin, margin, size - margin, int(size * 0.46)], radius=radius,
        fill=ACCENT_DARK
    )
    d.rounded_rectangle(
        [margin, int(size * 0.30), size - margin, size - margin], radius=radius, fill=ACCENT
    )
    # sheet of paper
    left, top = int(size * 0.26), int(size * 0.20)
    right, bottom = int(size * 0.74), int(size * 0.84)
    d.rounded_rectangle([left, top, right, bottom], radius=int(size * 0.05), fill=WHITE)
    # text lines
    line_h = max(2, int(size * 0.028))
    for i in range(5):
        y = top + int(size * 0.10) + i * int(size * 0.105)
        if y + line_h > bottom - int(size * 0.05):
            break
        x0 = left + int(size * 0.06)
        x1 = right - int(size * 0.06) - (int(size * 0.10) if i % 2 else 0)
        d.rounded_rectangle([x0, y, x1, y + line_h], radius=line_h // 2, fill=GREY)
    # scan line
    scan_y = int(size * 0.55)
    d.rounded_rectangle(
        [int(size * 0.21), scan_y, int(size * 0.79), scan_y + int(size * 0.05)],
        radius=int(size * 0.025), fill=AMBER,
    )
    return img


def main() -> None:
    root = Path(__file__).resolve().parent
    sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256]
    images = [draw_icon(s) for s in sizes]
    images[-1].save(root / "smartscan.png", "PNG")
    images[-1].save(root / "smartscan.ico", "ICO", sizes=[(s, s) for s in sizes])
    # Individual PNGs for Linux/macOS bundling if ever needed.
    png_dir = root / "png"
    png_dir.mkdir(exist_ok=True)
    for size, image in zip(sizes, images):
        image.save(png_dir / f"smartscan-{size}.png", "PNG")
    print(f"wrote {root / 'smartscan.ico'} and {root / 'smartscan.png'}")


if __name__ == "__main__":
    main()
