#!/usr/bin/env python3
"""サムネイルの描画。

競合の上位サムネ（数百万回再生）を調べて分かった型:

  ・人物の顔が主役。切り抜いて大きく置く
  ・極太ゴシックを中央に横断させる。2行以内、1行6〜9文字
  ・黒の太い縁取り。二重縁（白+赤、赤+黄）も多い
  ・赤・黄・白・黒の高彩度
  ・四隅に小さい補助文字

**文言は真似しない。** 上位は「意味不明」「ボロクソ」「誇張しすぎ」といった
言葉を使っているが、権利者ガイドラインは「出演者の名誉・信用を害し、または
人格を侮辱する文字表記」を禁じている。受付メールにも「ルールの隙間や
ギリギリを狙う行為は警告なしで削除」とある。

視認性の技法だけ採り、**文言は数字と事実にする。** 競合が全員「顔＋煽り文字」
なので同じ土俵では埋もれる。図解チャンネルなら数字を主役にするほうが筋が通る。
"""

from __future__ import annotations

import re

from PIL import Image, ImageDraw, ImageFilter

from scripts.draw import GOLD, RED, pick_font

SIZE = (1280, 720)
WHITE = (255, 255, 255)
BLACK = (16, 16, 18)

# 数字と単位は金で抜く。図解チャンネルとしての主役を目立たせる
NUM_RE = re.compile(r"(\d[\d,]*\s*(?:万円|億円|万|円|棟|人|%|％)?)")


def _fit(draw: ImageDraw.ImageDraw, text: str, max_w: int, start: int) -> int:
    """幅に収まる最大のフォントサイズを返す。"""
    size = start
    while size > 28:
        f = pick_font(size)
        if draw.textlength(text, font=f) <= max_w:
            return size
        size -= 4
    return 28


def _stroked_line(d: ImageDraw.ImageDraw, x: int, y: int, text: str,
                  size: int, accent: bool = True) -> None:
    """極太＋二重縁で1行描く。数字だけ金にする。"""
    f = pick_font(size)
    stroke = max(6, size // 9)

    cx = x
    for part in NUM_RE.split(text):
        if not part:
            continue
        fill = GOLD if (accent and NUM_RE.fullmatch(part)) else WHITE
        # 外側の黒縁 → 内側の色。縁を2回描くと輪郭が締まる
        d.text((cx, y), part, font=f, fill=fill,
               stroke_width=stroke, stroke_fill=BLACK)
        d.text((cx, y), part, font=f, fill=fill,
               stroke_width=max(2, stroke // 3), stroke_fill=BLACK)
        cx += int(d.textlength(part, font=f))


# 元動画は下部に字幕・氏名・金額のテロップを、上部に注記と募集告知を焼き込む。
# そのまま使うとこちらの文字と必ずぶつかるので、顔が残る中央の帯だけを使う。
CROP_TOP, CROP_BOTTOM = 0.17, 0.28


def _crop_16x9(bg: Image.Image) -> Image.Image:
    """テロップ帯を避けた 16:9 の窓を切り出す。

    上下を落とすだけだと 16:9 でなくなり、リサイズで顔が縦に伸びる。
    残す高さから幅を逆算して、比率を保ったまま中央を切る（結果として寄る）。
    """
    bw, bh = bg.size
    top = int(bh * CROP_TOP)
    keep_h = int(bh * (1 - CROP_TOP - CROP_BOTTOM))
    keep_w = min(bw, int(keep_h * 16 / 9))
    left = (bw - keep_w) // 2
    return bg.crop((left, top, left + keep_w, top + keep_h))


def render_thumbnail(bg: Image.Image, line1: str, line2: str = "",
                     badge: str = "", size: tuple[int, int] = SIZE) -> Image.Image:
    """背景（動画のフレーム）に極太文字を載せる。"""
    w, h = size
    img = _crop_16x9(bg).convert("RGB").resize(size, Image.LANCZOS)

    # 文字の下half を少し沈めてコントラストを稼ぐ。全面を暗くすると顔が死ぬ
    shade = Image.new("L", size, 0)
    ds = ImageDraw.Draw(shade)
    ds.rectangle([0, int(h * 0.42), w, h], fill=150)
    shade = shade.filter(ImageFilter.GaussianBlur(60))
    img = Image.composite(Image.new("RGB", size, BLACK), img, shade)

    d = ImageDraw.Draw(img)
    m = int(w * 0.045)
    avail = w - m * 2

    lines = [l for l in (line1, line2) if (l or "").strip()]
    sizes = [_fit(d, l, avail, int(h * 0.20)) for l in lines]
    unified = min(sizes) if lines else 0           # 2行のサイズを揃える

    total = sum(int(s * 1.18) for s in [unified] * len(lines))
    y = h - total - int(h * 0.07)
    for l in lines:
        _stroked_line(d, m, y, l, unified)
        y += int(unified * 1.18)

    if badge.strip():
        # 左上の小さな見出し。競合が四隅に置くのと同じ役割だが、煽らず事実を書く
        bf = pick_font(int(h * 0.062))
        bw = int(d.textlength(badge, font=bf)) + int(w * 0.035)
        bh = int(h * 0.105)
        d.rectangle([m, int(h * 0.05), m + bw, int(h * 0.05) + bh], fill=RED)
        d.text((m + int(w * 0.017), int(h * 0.05) + int(bh * 0.16)), badge,
               font=bf, fill=WHITE)
    return img
