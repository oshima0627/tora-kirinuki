#!/usr/bin/env python3
"""チャンネルのアイコンとバナーを作る。

  python scripts/build_brand.py            # work/_brand/ に icon.png と banner.png
  python scripts/build_brand.py --guide    # バナーに安全領域の枠を重ねた確認用も出す

権利者のロゴ・画像・キャラクターは使わない（各社ガイドラインで禁止）。
令和の虎のロゴは「赤いリング＋赤い筆文字＋金の人物シルエット＋イナズマ」で、
虎の絵は存在しない。そのため意匠は複製せず、誰の占有物でもない配色だけを共有する。

虎はこのスクリプトで一から描き起こした図形。
額の縞を右肩上がりの棒グラフにして、「虎」と「図解」を1つのマークにしている。

────────────────────────────────────────────────────────────
造形の方針

  面は1枚。目・鼻・縞は上に線を乗せず、地を抜いて（ネガティブスペースで）作る。
  乗せると要素が増えて散らかり、24pxで潰れる。抜けば輪郭だけが残る。

  曲線を使わない。白目・口・筆致のギザつきは可愛い方向に寄るので入れない。
────────────────────────────────────────────────────────────

バナーの寸法

  アップロードは 2560x1440。全デバイスで見えるのは中央 1546x423 だけ。
  スマホではこの帯しか出ない。文字とマークは必ずここに収める。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.draw import (BG_BOTTOM, BG_TOP, GOLD, INK, MUTED,  # noqa: E402
                          RED, fit_font, pick_font)

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "_brand"

# 配色とフォントは scripts/draw.py に集約し、図解カードと共有している
LINE = INK       # 見出し
SUB = MUTED

BANNER_W, BANNER_H = 2560, 1440
SAFE_W, SAFE_H = 1546, 423
SAFE = ((BANNER_W - SAFE_W) // 2, (BANNER_H - SAFE_H) // 2,
        (BANNER_W + SAFE_W) // 2, (BANNER_H + SAFE_H) // 2)

TITLE = "図解でわかる令和の虎"
SUB_LINE = "令和の虎Second 切り抜き"

# ── 虎の造形（0,0)-(1,1) の正規化座標。左右対称、直線のみ ──────────────

# 輪郭。耳の間を凹ませると猫ではなく虎に見える
HEAD = [
    (0.50, 0.17), (0.66, 0.09), (0.78, 0.00), (0.85, 0.23),
    (1.00, 0.45), (0.94, 0.73), (0.68, 0.97), (0.50, 1.00),
    (0.32, 0.97), (0.06, 0.73), (0.00, 0.45), (0.15, 0.23),
    (0.22, 0.00), (0.34, 0.09),
]

# 目。眉と一体の鋭いスラッシュ1本にする。内側を下げると険しくなる
EYE_L = [(0.175, 0.455), (0.410, 0.545), (0.410, 0.620), (0.175, 0.530)]
EYE_R = [(0.825, 0.455), (0.590, 0.545), (0.590, 0.620), (0.825, 0.530)]

NOSE = [(0.440, 0.700), (0.560, 0.700), (0.500, 0.800)]

# 頬の縞。先を細らせた楔
CHEEK = [
    [(0.000, 0.565), (0.165, 0.515), (0.165, 0.580), (0.000, 0.635)],
    [(0.035, 0.710), (0.190, 0.660), (0.190, 0.725), (0.055, 0.775)],
    [(1.000, 0.565), (0.835, 0.515), (0.835, 0.580), (1.000, 0.635)],
    [(0.965, 0.710), (0.810, 0.660), (0.810, 0.725), (0.945, 0.775)],
]

# 額の縞 = 右肩上がりの棒グラフ。(中心x, 高さ比)
# 右肩上がりの塊は重心が右に寄るので、幾何中心より少し左に置いて釣り合わせる
FOREHEAD_BARS = [(0.355, 0.42), (0.470, 0.68), (0.585, 1.00)]
BAR_TOP, BAR_BOTTOM, BAR_W = 0.225, 0.435, 0.070

CLEAR = (0, 0, 0, 0)


def _tiger(size: int) -> Image.Image:
    """虎の頭を RGBA で返す。4倍で描いて縮小し、斜辺を滑らかにする。

    ImageDraw は RGBA に対して合成ではなく上書きするので、
    透明で塗れば地を抜ける。目・鼻・縞はすべてこの抜きで作る。
    """
    ss = 4
    s = size * ss
    img = Image.new("RGBA", (s, s), CLEAR)
    d = ImageDraw.Draw(img)
    P = lambda pts: [(x * s, y * s) for x, y in pts]  # noqa: E731

    d.polygon(P(HEAD), fill=RED + (255,))

    for shape in (EYE_L, EYE_R, NOSE, *CHEEK):
        d.polygon(P(shape), fill=CLEAR)

    for cx, hr in FOREHEAD_BARS:
        top = BAR_BOTTOM - (BAR_BOTTOM - BAR_TOP) * hr
        box = [(cx - BAR_W / 2) * s, top * s, (cx + BAR_W / 2) * s, BAR_BOTTOM * s]
        # 最も高い1本だけ金で置く。残りは抜く
        d.rectangle(box, fill=GOLD + (255,) if hr == 1.0 else CLEAR)

    return img.resize((size, size), Image.LANCZOS)


def _ground(w: int, h: int) -> Image.Image:
    """ほぼ無地。グラデーションは気づかない程度に留める。"""
    img = Image.new("RGB", (w, h), BG_TOP)
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=tuple(
            int(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOTTOM)))
    return img


def build_icon(size: int = 800) -> Path:
    img = _ground(size, size)

    # 24px前後で表示されるので、虎の頭だけを大きく置く。文字は入れない
    d = int(size * 0.74)
    tiger = _tiger(d)
    img.paste(tiger, ((size - d) // 2, int(size * 0.13)), tiger)

    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "icon.png"
    img.save(p)
    print(f"✓ {p}  {img.size}  {p.stat().st_size / 1024:.0f} KB")
    return p


def build_banner(guide: bool = False) -> Path:
    img = _ground(BANNER_W, BANNER_H)
    d = ImageDraw.Draw(img)

    # 耳まで安全領域に収める。はみ出すとスマホで切れる
    tiger_d = int(SAFE_H * 0.74)
    tiger_x = SAFE[0] + 60
    tiger = _tiger(tiger_d)
    img.paste(tiger, (tiger_x, BANNER_H // 2 - tiger_d // 2), tiger)

    # マークと文字の間に金の細い縦罫を1本。余白を作りつつ視線を送る
    rule_x = tiger_x + tiger_d + 70
    d.rectangle([rule_x, BANNER_H // 2 - int(SAFE_H * 0.26),
                 rule_x + 5, BANNER_H // 2 + int(SAFE_H * 0.26)], fill=GOLD)

    tx = rule_x + 70
    avail = SAFE[2] - tx - 40

    f_title = fit_font(d, TITLE, avail, 132)
    b = d.textbbox((0, 0), TITLE, font=f_title)
    d.text((tx - b[0], BANNER_H // 2 - (b[3] - b[1]) - 26 - b[1]),
           TITLE, font=f_title, fill=LINE)

    f_sub = fit_font(d, SUB_LINE, avail, 46)
    d.text((tx, BANNER_H // 2 + 26), SUB_LINE, font=f_sub, fill=SUB)

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
