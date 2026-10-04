"""Generate the original BrowserTrace application icon.

Draws a minimal forensic symbol -- a browser window beneath a detective's fedora
with a crimson magnifying glass tracing the history -- as vector-style geometry,
renders it at every Windows icon size and writes both ``icon.ico`` and ``icon.png``
into ``browsertrace/resources``.

Usage:
    python scripts/make_icon.py
"""

from __future__ import annotations

import os
import sys

from PIL import Image, ImageDraw

ACCENT = "#C7383E"
ACCENT_BRIGHT = "#E05A60"
ACCENT_RING = "#8F242A"
BG = "#101317"
WINDOW_STROKE = "#E8EBEE"
BAR = "#4E5660"
CONTENT = "#343B44"
HAT = "#C3CCD6"
HAT_SHADOW = "#93A0AD"
OK = "#57B06B"
AMBER = "#C2A24A"

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT_DIR = os.path.join(ROOT, "browsertrace", "resources")
SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256, 512]


def draw_canvas(base: int = 1024) -> Image.Image:
    s = base
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def u(f):
        return f / 100.0 * s

    def rounded(cx, cy, w, h, radius, fill=None, outline=None, width=None):
        x0 = cx - w / 2
        y0 = cy - h / 2
        d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=radius,
                            fill=fill, outline=outline, width=int(width) if width else 0)

    # ---- tile background -------------------------------------------------
    pad = u(2.2)
    d.rounded_rectangle([pad, pad, s - pad, s - pad], radius=u(22), fill=BG)
    d.rounded_rectangle([pad, pad, s - pad, s - pad], radius=u(22),
                        outline=ACCENT_RING, width=int(u(1.1)))

    # ---- detective fedora (top-right, behind the magnifier) --------------
    hat_cx = u(61)
    hat_top = u(17)
    brim_w = u(34)
    brim_h = u(6.2)
    crown_w = u(24)
    crown_h = u(12)
    # brim
    rounded(hat_cx, hat_top + brim_h / 2, brim_w, brim_h, u(3.1), HAT)
    # crown (dome)
    d.rounded_rectangle(
        [hat_cx - crown_w / 2, hat_top + brim_h - crown_h, hat_cx + crown_w / 2, hat_top + brim_h],
        radius=u(10), fill=HAT,
    )
    # band
    d.rounded_rectangle(
        [hat_cx - crown_w / 2, hat_top + brim_h - u(5.6), hat_cx + crown_w / 2, hat_top + brim_h],
        radius=u(2.2), fill=ACCENT_BRIGHT,
    )

    # ---- browser window --------------------------------------------------
    win_w = u(56)
    win_h = u(40)
    win_cx = u(49)
    win_cy = u(58)
    rounded(win_cx, win_cy, win_w, win_h, u(4.5), outline=WINDOW_STROKE, width=u(2.0))
    # title-bar dots
    dot_r = u(1.25)
    for i, color in enumerate((ACCENT_BRIGHT, AMBER, OK)):
        cx = win_cx - win_w / 2 + u(4.6) + i * u(3.4)
        d.ellipse([cx - dot_r, win_cy - win_h / 2 + u(4.6) - dot_r,
                   cx + dot_r, win_cy - win_h / 2 + u(4.6) + dot_r], fill=color)
    # address bar
    bar_w = u(38)
    bar_h = u(4.6)
    rounded(win_cx, win_cy - win_h / 2 + u(11), bar_w, bar_h, u(2.3), outline=BAR, width=u(1.4))
    # content skeleton lines
    line_h = u(1.7)
    content_x = win_cx - win_w / 2 + u(6.5)
    y_start = win_cy - win_h / 2 + u(18)
    widths = [u(20), u(30), u(16), u(27), u(12)]
    yy = y_start
    for i, wline in enumerate(widths):
        d.rounded_rectangle([content_x, yy, content_x + wline, yy + line_h],
                            radius=line_h / 2, fill=CONTENT)
        yy += u(4.2)

    # ---- magnifying glass (crimson) --------------------------------------
    glass_r = u(12.5)
    glass_cx = win_cx + win_w * 0.09
    glass_cy = win_cy - win_h * 0.16
    d.ellipse([glass_cx - glass_r, glass_cy - glass_r, glass_cx + glass_r, glass_cy + glass_r],
              outline=ACCENT_BRIGHT, width=int(u(2.6)))
    d.ellipse([glass_cx - glass_r, glass_cy - glass_r, glass_cx + glass_r, glass_cy + glass_r],
              outline=ACCENT, width=int(u(0.6)))
    # glass window showing a url line detail
    d.line([glass_cx - glass_r * 0.55, glass_cy, glass_cx + glass_r * 0.55, glass_cy],
           fill=WINDOW_STROKE, width=int(u(1.0)))
    # handle pointing down-right
    hx0 = glass_cx + glass_r * 0.62
    hy0 = glass_cy + glass_r * 0.62
    hx1 = hx0 + u(12.5)
    hy1 = hy0 + u(12.5)
    d.line([hx0, hy0, hx1, hy1], fill=ACCENT_BRIGHT, width=int(u(3.0)))
    d.line([hx0, hy0, hx1, hy1], fill=ACCENT, width=int(u(1.0)))
    # subtle sheen
    sheen_r = glass_r * 0.28
    d.ellipse([glass_cx - glass_r * 0.35, glass_cy - glass_r * 0.55,
               glass_cx - glass_r * 0.35 + sheen_r, glass_cy - glass_r * 0.55 + sheen_r],
              fill="#4E5660")

    return img


def render(size: int, base: Image.Image) -> Image.Image:
    return base.resize((size, size), Image.LANCZOS)


def main() -> int:
    base = draw_canvas(1024)

    os.makedirs(OUT_DIR, exist_ok=True)

    png_path = os.path.join(OUT_DIR, "icon.png")
    base.save(png_path)

    ico_path = os.path.join(OUT_DIR, "icon.ico")
    frames = [render(s, base) for s in SIZES]
    frames[-1].save(ico_path, format="ICO", sizes=[(s, s) for s in SIZES])

    print(f"wrote {png_path}")
    print(f"wrote {ico_path} ({len(SIZES)} resolutions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())