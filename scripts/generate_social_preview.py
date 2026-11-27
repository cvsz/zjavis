"""Generate the JARVIS social preview image (OpenGraph, 1200×630 PNG).

This script creates a local OpenGraph social preview image using Pillow only
— no external image-generation credits or network access required. The output
is written to ``docs/assets/social-preview.png``.

Usage:
    python3 scripts/generate_social_preview.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# --- Configuration ---------------------------------------------------------

OUTPUT_PATH = Path("docs/assets/social-preview.png")
WIDTH = 1200
HEIGHT = 630

# JARVIS brand colors (dark, high-tech, Iron Man inspired)
BG_COLOR = "#0B1120"  # Deep space navy
ACCENT_COLOR = "#00D4FF"  # Arc reactor cyan
TEXT_COLOR = "#FFFFFF"  # White
SECONDARY_COLOR = "#A8B2C1"  # Muted gray-blue

# --- Helpers ---------------------------------------------------------------


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load a TrueType font, falling back to the default bitmap font."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"
        if bold
        else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def generate() -> None:
    """Generate and save the social preview image."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Draw arc-reactor-style accent circle (top-right quadrant)
    cx = int(WIDTH * 0.78)
    cy = int(HEIGHT * 0.28)
    radius = int(HEIGHT * 0.22)
    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        outline=ACCENT_COLOR,
        width=3,
    )
    # Inner rings for detail
    for r in (int(radius * 0.55), int(radius * 0.30)):
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            outline=ACCENT_COLOR,
            width=1,
        )

    # Title text
    title_font = _load_font(64, bold=True)
    title = "JARVIS"
    draw.textbbox((0, 0), title, font=title_font)
    draw.text(
        (int(WIDTH * 0.08), int(HEIGHT * 0.35)),
        title,
        font=title_font,
        fill=TEXT_COLOR,
    )

    # Subtitle text
    sub_font = _load_font(32)
    subtitle = "Personal AI Operating System — Local-first · Secure · Observable"
    draw.textbbox((0, 0), subtitle, font=sub_font)
    draw.text(
        (int(WIDTH * 0.08), int(HEIGHT * 0.52)),
        subtitle,
        font=sub_font,
        fill=SECONDARY_COLOR,
    )

    # Tagline / repository
    tag_font = _load_font(24)
    tagline = "cvsz/zjavis  ·  MIT License"
    draw.text(
        (int(WIDTH * 0.08), int(HEIGHT * 0.62)),
        tagline,
        font=tag_font,
        fill=SECONDARY_COLOR,
    )

    # Bottom accent line
    draw.line(
        [int(WIDTH * 0.08), int(HEIGHT * 0.72), int(WIDTH * 0.92), int(HEIGHT * 0.72)],
        fill=ACCENT_COLOR,
        width=2,
    )

    # Ensure output directory exists
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Save as PNG (optimized)
    img.save(OUTPUT_PATH, format="PNG", optimize=True)
    print(f"Generated social preview: {OUTPUT_PATH} ({WIDTH}x{HEIGHT})")


if __name__ == "__main__":
    generate()
