#!/usr/bin/env python3
"""描画の共通部品。チャンネルアート（build_brand）と図解カード（cards）で共有する。

配色はチャンネルのブランドに揃える。白地に赤、差し色に金。
令和の虎の意匠（赤いリング・筆文字ロゴ・人物シルエット・イナズマ）は使わない。
"""

from __future__ import annotations

from pathlib import Path

from PIL import ImageDraw, ImageFont

FONT_SANS = [
    r"C:\Windows\Fonts\YuGothB.ttc",
    r"C:\Windows\Fonts\meiryob.ttc",
    r"C:\Windows\Fonts\msgothic.ttc",
]

RED = (214, 34, 42)
GOLD = (226, 158, 34)
BG_TOP = (255, 255, 255)
BG_BOTTOM = (243, 243, 246)
INK = (24, 24, 28)
MUTED = (122, 122, 132)


def pick_font(size: int) -> ImageFont.FreeTypeFont:
    for p in FONT_SANS:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def fit_font(draw: ImageDraw.ImageDraw, text: str, max_w: int,
             start: int) -> ImageFont.FreeTypeFont:
    """幅に収まる最大サイズのフォントを返す。"""
    size = start
    while size > 14:
        f = pick_font(size)
        b = draw.textbbox((0, 0), text, font=f)
        if b[2] - b[0] <= max_w:
            return f
        size -= 2
    return pick_font(14)


def wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont,
         max_w: int) -> list[str]:
    """日本語は単語境界が無いので、幅を見て1文字ずつ折り返す。"""
    lines, cur = [], ""
    for ch in text:
        b = draw.textbbox((0, 0), cur + ch, font=font)
        if b[2] - b[0] > max_w and cur:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines
