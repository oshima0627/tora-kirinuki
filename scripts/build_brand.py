#!/usr/bin/env python3
"""チャンネルのアイコンとバナーを作る。

  python scripts/build_brand.py            # work/_brand/ に icon.png と banner.png
  python scripts/build_brand.py --guide    # バナーに安全領域の枠を重ねた確認用も出す

権利者のロゴ・画像・キャラクターは使わない（各社ガイドラインで禁止）。
虎はこのスクリプトで一から描き起こした図形で、権利者の意匠とは無関係。
額の縞を右肩上がりの棒グラフにして、「虎」と「図解」を1つのマークにしている。

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


DARK = (12, 16, 30)
AMBER_DEEP = (198, 126, 34)

MUZZLE = (252, 214, 152)
EYE_WHITE = (250, 246, 236)

# 虎の頭の輪郭。左右対称、(0,0)-(1,1) の正規化座標。
# 耳の間をいったん凹ませると、猫ではなく虎の頭に見える。
HEAD = [
    (0.50, 0.15), (0.62, 0.10), (0.70, 0.11), (0.80, 0.00),
    (0.88, 0.19), (0.97, 0.40), (1.00, 0.59), (0.92, 0.79),
    (0.74, 0.95), (0.50, 1.00), (0.26, 0.95), (0.08, 0.79),
    (0.00, 0.59), (0.03, 0.40), (0.12, 0.19), (0.20, 0.00),
    (0.30, 0.11), (0.38, 0.10),
]

EAR_R = [(0.80, 0.045), (0.860, 0.170), (0.730, 0.125)]
EAR_L = [(0.20, 0.045), (0.140, 0.170), (0.270, 0.125)]

# 眉。目の上に角度をつけて置くと、虎らしい険しさが出る
BROW_R = [(0.78, 0.455), (0.585, 0.505), (0.595, 0.555), (0.790, 0.510)]
BROW_L = [(0.22, 0.455), (0.415, 0.505), (0.405, 0.555), (0.210, 0.510)]

EYE_R = (0.585, 0.740, 0.575, 0.650)     # (x1, x2, y1, y2)
EYE_L = (0.260, 0.415, 0.575, 0.650)
PUPIL_R = (0.640, 0.690, 0.585, 0.645)
PUPIL_L = (0.310, 0.360, 0.585, 0.645)

NOSE = [(0.425, 0.680), (0.575, 0.680), (0.500, 0.770)]

# 頬の縞。先を細らせたいので線ではなく多角形で持つ
CHEEK = [
    [(0.000, 0.520), (0.150, 0.480), (0.150, 0.520), (0.005, 0.560)],
    [(0.015, 0.640), (0.160, 0.605), (0.158, 0.645), (0.030, 0.680)],
    [(1.000, 0.520), (0.850, 0.480), (0.850, 0.520), (0.995, 0.560)],
    [(0.985, 0.640), (0.840, 0.605), (0.842, 0.645), (0.970, 0.680)],
]

# 額の縞 = 右肩上がりの棒グラフ。(中心x, 高さ比)
# 右肩上がりの塊は重心が右に寄るので、幾何中心より少し左に置いて見た目を釣り合わせる
FOREHEAD_BARS = [(0.348, 0.42), (0.463, 0.68), (0.578, 1.00)]
BAR_TOP, BAR_BOTTOM, BAR_W = 0.205, 0.415, 0.072


def _tiger(size: int) -> Image.Image:
    """虎の頭を RGBA で返す。4倍で描いて縮小し、輪郭を滑らかにする。"""
    ss = 4
    s = size * ss
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    P = lambda pts: [(x * s, y * s) for x, y in pts]  # noqa: E731
    B = lambda x1, x2, y1, y2: [x1 * s, y1 * s, x2 * s, y2 * s]  # noqa: E731

    d.polygon(P(HEAD), fill=AMBER + (255,))
    for ear in (EAR_L, EAR_R):
        d.polygon(P(ear), fill=AMBER_DEEP + (255,))

    # 口まわりを明るくして、鼻と口を浮かせる
    d.ellipse(B(0.330, 0.670, 0.660, 0.900), fill=MUZZLE + (255,))

    for st in CHEEK:
        d.polygon(P(st), fill=DARK + (255,))

    for cx, hr in FOREHEAD_BARS:
        top = BAR_BOTTOM - (BAR_BOTTOM - BAR_TOP) * hr
        d.rounded_rectangle(
            [(cx - BAR_W / 2) * s, top * s, (cx + BAR_W / 2) * s, BAR_BOTTOM * s],
            radius=int(s * 0.013),
            fill=(LINE if hr == 1.0 else DARK) + (255,))

    for eye in (EYE_L, EYE_R):
        d.ellipse(B(*eye), fill=EYE_WHITE + (255,))
    for pup in (PUPIL_L, PUPIL_R):
        d.ellipse(B(*pup), fill=DARK + (255,))
    for brow in (BROW_L, BROW_R):
        d.polygon(P(brow), fill=DARK + (255,))

    d.polygon(P(NOSE), fill=DARK + (255,))

    # 口。鼻先から下ろした短い縦線と、その左右に垂れる2つの弧（‿‿）
    w = int(s * 0.026)
    d.line([0.500 * s, 0.760 * s, 0.500 * s, 0.800 * s], fill=DARK + (255,), width=w)
    d.arc(B(0.395, 0.505, 0.755, 0.855), 0, 180, fill=DARK + (255,), width=w)
    d.arc(B(0.495, 0.605, 0.755, 0.855), 0, 180, fill=DARK + (255,), width=w)

    return img.resize((size, size), Image.LANCZOS)


def _place_tiger(img: Image.Image, x: int, cy: int, d: int) -> int:
    """虎の頭を左上x・垂直中心cyに置き、右端のxを返す。"""
    tiger = _tiger(d)
    img.paste(tiger, (x, cy - d // 2), tiger)
    return x + d


def build_icon(size: int = 800) -> Path:
    img = _ground(size, size)

    glow = Image.new("RGB", (size, size), (0, 0, 0))
    ImageDraw.Draw(glow).ellipse(
        [size * 0.12, size * 0.10, size * 0.88, size * 0.86],
        fill=tuple(int(v * 0.22) for v in AMBER))
    from PIL import ImageChops
    img = ImageChops.screen(img, glow.filter(ImageFilter.GaussianBlur(size // 9)))

    # アイコンは24px程度でも判別できる必要があるので、虎の頭だけを大きく置く。
    # 「図解」の文字はチャンネル名が担うので入れない。
    d = int(size * 0.76)
    tiger = _tiger(d)
    img.paste(tiger, ((size - d) // 2, int(size * 0.10)), tiger)

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

    # 耳まで安全領域に収める。はみ出すとスマホで切れる
    tiger_d = int(SAFE_H * 0.82)
    right = _place_tiger(img, SAFE[0] + 50, BANNER_H // 2, tiger_d)

    d = ImageDraw.Draw(img)
    tx = right + 80
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
