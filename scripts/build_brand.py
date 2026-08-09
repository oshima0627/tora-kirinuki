#!/usr/bin/env python3
"""チャンネルのアイコンとバナーを作る。

  python scripts/build_brand.py            # work/_brand/ に icon.png と banner.png
  python scripts/build_brand.py --guide    # バナーに安全領域の枠を重ねた確認用も出す

権利者のロゴ・画像・キャラクターは使わない（各社ガイドラインで禁止）。
虎のモチーフも公式と誤認されうるので避け、「図解」そのものを図案にしている。

────────────────────────────────────────────────────────────
バナーの寸法

  アップロードは 2560x1440。全デバイスで見えるのは中央 1546x423 だけ。
  スマホではこの帯しか出ない。文字は必ずここに収める。
────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "_brand"

FONT_SANS = [
    r"C:\Windows\Fonts\YuGothB.ttc",
    r"C:\Windows\Fonts\meiryob.ttc",
    r"C:\Windows\Fonts\msgothic.ttc",
]

NAVY_TOP = (20, 27, 48)
NAVY_BOTTOM = (9, 12, 24)
AMBER = (240, 168, 60)
LINE = (238, 242, 252)
SUB = (150, 162, 196)

BANNER_W, BANNER_H = 2560, 1440
SAFE_W, SAFE_H = 1546, 423
SAFE = ((BANNER_W - SAFE_W) // 2, (BANNER_H - SAFE_H) // 2,
        (BANNER_W + SAFE_W) // 2, (BANNER_H + SAFE_H) // 2)

TITLE = "図解でわかる令和の虎"
SUB_LINE = "令和の虎Second 切り抜き"


def pick_font(size: int) -> ImageFont.FreeTypeFont:
    for p in FONT_SANS:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def fit_font(draw: ImageDraw.ImageDraw, text: str, max_w: int,
             start: int) -> ImageFont.FreeTypeFont:
    size = start
    while size > 14:
        f = pick_font(size)
        b = draw.textbbox((0, 0), text, font=f)
        if b[2] - b[0] <= max_w:
            return f
        size -= 2
    return pick_font(14)


def _ground(w: int, h: int) -> Image.Image:
    img = Image.new("RGB", (w, h), NAVY_TOP)
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = (y / h) ** 0.9
        d.line([(0, y), (w, y)], fill=tuple(
            int(a + (b - a) * t) for a, b in zip(NAVY_TOP, NAVY_BOTTOM)))
    return img


def _bars(img: Image.Image, x: int, y: int, unit: int, alpha: float = 1.0) -> None:
    """図解の象徴として、伸びる棒グラフを描く。右肩上がりで「わかる」を示す。"""
    d = ImageDraw.Draw(img, "RGBA")
    heights = (0.38, 0.62, 1.0)
    for i, hr in enumerate(heights):
        bh = int(unit * 2.2 * hr)
        bx = x + i * int(unit * 0.78)
        col = AMBER if i == len(heights) - 1 else (108, 124, 168)
        d.rounded_rectangle([bx, y - bh, bx + int(unit * 0.5), y],
                            radius=int(unit * 0.12),
                            fill=col + (int(255 * alpha),))


def build_icon(size: int = 800) -> Path:
    img = _ground(size, size)

    glow = Image.new("RGB", (size, size), (0, 0, 0))
    ImageDraw.Draw(glow).ellipse(
        [size * 0.12, size * 0.10, size * 0.88, size * 0.86],
        fill=tuple(int(v * 0.22) for v in AMBER))
    from PIL import ImageChops
    img = ImageChops.screen(img, glow.filter(ImageFilter.GaussianBlur(size // 9)))

    unit = int(size * 0.13)
    _bars(img, int(size * 0.30), int(size * 0.50), unit)

    d = ImageDraw.Draw(img)
    f = fit_font(d, "図解", int(size * 0.62), int(size * 0.30))
    b = d.textbbox((0, 0), "図解", font=f)
    d.text(((size - (b[2] - b[0])) // 2 - b[0], int(size * 0.56)), "図解",
           font=f, fill=LINE)

    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "icon.png"
    img.save(p)
    print(f"✓ {p}  {img.size}  {p.stat().st_size / 1024:.0f} KB")
    return p


def build_banner(guide: bool = False) -> Path:
    img = _ground(BANNER_W, BANNER_H)

    glow = Image.new("RGB", (BANNER_W, BANNER_H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for fx, fy, r, a in ((0.14, 0.42, 300, 0.20), (0.86, 0.58, 340, 0.16)):
        x, y = int(BANNER_W * fx), int(BANNER_H * fy)
        gd.ellipse([x - r, y - r, x + r, y + r],
                   fill=tuple(int(v * a) for v in AMBER))
    from PIL import ImageChops
    img = ImageChops.screen(img, glow.filter(ImageFilter.GaussianBlur(180)))

    unit = int(BANNER_H * 0.075)
    _bars(img, SAFE[0] + 40, BANNER_H // 2 + int(BANNER_H * 0.055), unit)

    d = ImageDraw.Draw(img)
    tx = SAFE[0] + 40 + int(unit * 2.6) + 90
    avail = SAFE[2] - tx - 30

    f_title = fit_font(d, TITLE, avail, 150)
    b = d.textbbox((0, 0), TITLE, font=f_title)
    ty = BANNER_H // 2 - (b[3] - b[1]) - 30
    d.text((tx - b[0], ty - b[1]), TITLE, font=f_title, fill=LINE)

    ry = BANNER_H // 2 + 10
    d.line([(tx, ry), (tx + min(avail, 640), ry)], fill=(108, 124, 168), width=3)

    f_sub = fit_font(d, SUB_LINE, avail, 52)
    d.text((tx, ry + 30), SUB_LINE, font=f_sub, fill=SUB)

    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "banner.png"
    img.save(p)
    print(f"✓ {p}  {img.size}  {p.stat().st_size / 1024 / 1024:.2f} MB")

    if guide:
        g = img.copy()
        dg = ImageDraw.Draw(g)
        dg.rectangle(SAFE, outline=(255, 80, 80), width=5)
        dg.rectangle([0, SAFE[1], BANNER_W, SAFE[3]], outline=(80, 160, 255), width=3)
        dg.text((SAFE[0] + 10, SAFE[1] - 60), "安全領域 1546x423（全デバイス）",
                font=pick_font(40), fill=(255, 120, 120))
        g.save(OUT / "banner_guide.png")
        print(f"✓ {OUT / 'banner_guide.png'}")
    return p


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--guide", action="store_true", help="安全領域の枠を重ねた確認用も出す")
    a = ap.parse_args()
    build_icon()
    build_banner(a.guide)


if __name__ == "__main__":
    main()
