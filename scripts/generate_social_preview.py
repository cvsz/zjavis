"""Generate a JARVIS social preview image locally (no external credits needed).

Produces a 1200x630 OpenGraph/social preview PNG at
docs/assets/social-preview.png using only Pillow (already a dev dependency
transitively available). Dark navy background with a subtle circuit-board
grid, a glowing AI core, and clean typography.
"""

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUTPUT = Path(__file__).resolve().parents[1] / "docs" / "assets" / "social-preview.png"
WIDTH, HEIGHT = 1200, 630

# Palette
BG = "#0B1120"
GRID = "#141B33"
CORE_GLOW = "#00D4FF"
CORE = "#FFFFFF"
TEXT = "#FFFFFF"
SUBTEXT = "#9AA5B1"
ACCENT_RING = "#1E3A8A"


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load a DejaVu Sans font falling back to the default bitmap font."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def main() -> None:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    # Subtle circuit-board grid
    step = 40
    for x in range(0, WIDTH, step):
        draw.line([(x, 0), (x, HEIGHT)], fill=GRID, width=1)
    for y in range(0, HEIGHT, step):
        draw.line([(0, y), (WIDTH, y)], fill=GRID, width=1)

    # Accent corner brackets
    bracket_color = ACCENT_RING
    bracket_w = 6
    bracket_len = 120
    margin = 40
    # top-left
    draw.line(
        [(margin, margin), (margin + bracket_len, margin)],
        fill=bracket_color,
        width=bracket_w,
    )
    draw.line(
        [(margin, margin), (margin, margin + bracket_len)],
        fill=bracket_color,
        width=bracket_w,
    )
    # top-right
    draw.line(
        [(WIDTH - margin - bracket_len, margin), (WIDTH - margin, margin)],
        fill=bracket_color,
        width=bracket_w,
    )
    draw.line(
        [(WIDTH - margin, margin), (WIDTH - margin, margin + bracket_len)],
        fill=bracket_color,
        width=bracket_w,
    )
    # bottom-left
    draw.line(
        [(margin, HEIGHT - margin), (margin + bracket_len, HEIGHT - margin)],
        fill=bracket_color,
        width=bracket_w,
    )
    draw.line(
        [(margin, HEIGHT - margin - bracket_len), (margin, HEIGHT - margin)],
        fill=bracket_color,
        width=bracket_w,
    )
    # bottom-right
    draw.line(
        [
            (WIDTH - margin - bracket_len, HEIGHT - margin),
            (WIDTH - margin, HEIGHT - margin),
        ],
        fill=bracket_color,
        width=bracket_w,
    )
    draw.line(
        [
            (WIDTH - margin, HEIGHT - margin - bracket_len),
            (WIDTH - margin, HEIGHT - margin),
        ],
        fill=bracket_color,
        width=bracket_w,
    )

    # Glowing AI core (arc-reactor inspired)
    cx, cy = WIDTH // 2, HEIGHT // 2 - 20
    core_r = 95
    glow_layers = 14
    for i in range(glow_layers, 0, -1):
        r = core_r + i * 6
        alpha = max(0, 255 - i * 16)
        glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(0, 212, 255, alpha))
        img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
        draw = ImageDraw.Draw(img)

    # Core ring
    draw.ellipse(
        [cx - core_r, cy - core_r, cx + core_r, cy + core_r], outline=CORE_GLOW, width=4
    )
    draw.ellipse(
        [cx - core_r + 10, cy - core_r + 10, cx + core_r - 10, cy + core_r - 10],
        outline=CORE_GLOW,
        width=2,
    )

    # Radial rays from core
    for angle in range(0, 360, 18):
        import math

        rad = math.radians(angle)
        x2 = cx + int(math.cos(rad) * (core_r + 120))
        y2 = cy + int(math.sin(rad) * (core_r + 120))
        draw.line([(cx, cy), (x2, y2)], fill=CORE_GLOW, width=2)

    # Central core dot
    draw.ellipse([cx - 14, cy - 14, cx + 14, cy + 14], fill=CORE)

    # Typography
    title_font = _load_font(78, bold=True)
    sub_font = _load_font(30, bold=False)

    title = "JARVIS"
    subtitle = "Personal AI Operating System"

    tw = draw.textlength(title, font=title_font)
    sw = draw.textlength(subtitle, font=sub_font)

    ty = HEIGHT // 2 + 110
    draw.text(((WIDTH - tw) / 2, ty), title, font=title_font, fill=TEXT)
    draw.text(((WIDTH - sw) / 2, ty + 70), subtitle, font=sub_font, fill=SUBTEXT)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUTPUT, "PNG")
    print(f"Wrote {OUTPUT} ({WIDTH}x{HEIGHT})")


if __name__ == "__main__":
    main()
