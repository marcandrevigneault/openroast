#!/usr/bin/env python3
"""Generate multi-resolution app icons from the source PNG.

Reads docs/coffeebean-nobg.png and produces:
- packaging/icon.ico  (multi-size Windows icon: 16–256 px)
- packaging/icon.png  (256x256 system tray / general use)

Usage:
    python packaging/generate_icons.py
"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "docs" / "coffeebean-nobg.png"
OUT_ICO = ROOT / "packaging" / "icon.ico"
OUT_PNG = ROOT / "packaging" / "icon.png"

ICO_SIZES = [16, 32, 48, 64, 128, 256]


def _make_square(img: Image.Image, size: int) -> Image.Image:
    """Resize *img* into a *size*x*size* square, preserving aspect ratio.

    The source image is centered on a transparent background.
    """
    # Thumbnail preserves aspect ratio (never upscales beyond original)
    thumb = img.copy()
    thumb.thumbnail((size, size), Image.LANCZOS)

    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    offset_x = (size - thumb.width) // 2
    offset_y = (size - thumb.height) // 2
    canvas.paste(thumb, (offset_x, offset_y), thumb)
    return canvas


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(f"Source image not found: {SOURCE}")

    src = Image.open(SOURCE).convert("RGBA")

    # --- icon.png (256x256) ---
    png256 = _make_square(src, 256)
    png256.save(OUT_PNG, format="PNG")
    print(f"Wrote {OUT_PNG}  ({OUT_PNG.stat().st_size:,} bytes)")

    # --- icon.ico (multi-size) ---
    # Pillow's ICO writer resizes the source to each requested size,
    # so we pass the largest version and let it downsample.
    png256.save(
        OUT_ICO,
        format="ICO",
        sizes=[(s, s) for s in ICO_SIZES],
    )
    print(f"Wrote {OUT_ICO}  ({OUT_ICO.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
