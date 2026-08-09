#!/usr/bin/env python3
"""サムネイルの描画。

競合の上位サムネ（数百万回再生）を調べて分かった型:

  ・人物の顔が主役。大きく置く
  ・極太ゴシックを中央に横断させる。2行以内
  ・黒の太い縁取り
  ・**1行の中で文字サイズを変える**（抑揚）。強い語だけ極端に大きい
  ・赤・黄・白・黒の高彩度

**文言は元動画で実際に話されていることだけを使う。** ガイドラインが禁じている
のは「出演者の名誉・信用を害し、または人格を侮辱する文字表記」であって、
発言の引用ではない。逆に、話していないことを盛るのは誇張になるのでしない。

**引用はASR字幕から取らない。** 元動画が焼き込んでいる公式テロップを映像で
読んで使う。実際、ASRは「倍にして返してもらう」、公式テロップは
「倍にして返してもらおう」で食い違っていた。

色の使い分け:
  赤  主となる一言
  黄  掛け合いの相手側の言葉
  白  事実・数字の補足
"""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFilter

from scripts.draw import pick_font

SIZE = (1280, 720)

RED = (234, 26, 34)
YELLOW = (255, 214, 0)
WHITE = (255, 255, 255)
BLACK = (12, 12, 14)
COLORS = {"r": RED, "y": YELLOW, "w": WHITE}

# 元動画は下部に字幕・氏名・金額のテロップを、上部に注記と募集告知を焼き込む。
# そのまま使うとこちらの文字とぶつかるので、顔が残る帯だけを使う。
CROP_TOP, CROP_BOTTOM = 0.17, 0.28


# パネルは横長なので、1枚もの（CROP_TOP/BOTTOM）ほど上を落とさなくてよい。
# 落としすぎると頭が切れる
PANEL_TOP, PANEL_BOTTOM = 0.16, 0.20


def crop_panel(bg: Image.Image, x: float, out: tuple[int, int]) -> Image.Image:
    """顔を切り出して out の比率に収める。x は横方向の中心（0..1）。

    掛け合いを左右に並べるときに使う。上下はテロップ帯を落とす。
    """
    bw, bh = bg.size
    top = int(bh * PANEL_TOP)
    keep_h = int(bh * (1 - PANEL_TOP - PANEL_BOTTOM))
    keep_w = min(bw, int(keep_h * out[0] / out[1]))
    left = max(0, min(bw - keep_w, int(bw * x) - keep_w // 2))
    return bg.crop((left, top, left + keep_w, top + keep_h)).resize(out, Image.LANCZOS)


# 顔を並べる高さ。全高にすると半分幅×全高＝8:9になり、16:9の素材から切ると
# 極端に寄ってしまう。上部に収めれば横長のまま切れるので寄りが穏やかになり、
# 下に文字帯も生まれる
FACE_H = 0.63


def compose_faces(frames: list[Image.Image], xs: list[float],
                  size: tuple[int, int] = SIZE) -> Image.Image:
    """掛け合いの2人を左右に並べる。競合の上位サムネで最も多い型。"""
    w, h = size
    img = Image.new("RGB", size, BLACK)
    pw, ph = w // len(frames), int(h * FACE_H)
    for i, fr in enumerate(frames):
        panel = crop_panel(fr.convert("RGB"), xs[i] if i < len(xs) else 0.5, (pw, ph))
        img.paste(panel, (i * pw, 0))
    d = ImageDraw.Draw(img)
    for i in range(1, len(frames)):          # 境目。2枚であることを分からせる
        d.rectangle([i * pw - 3, 0, i * pw + 2, ph], fill=BLACK)
    return img


def _crop_16x9(bg: Image.Image) -> Image.Image:
    """テロップ帯を避けた 16:9 の窓を切り出す。

    上下を落とすだけだと 16:9 でなくなり、リサイズで顔が縦に伸びる。
    残す高さから幅を逆算して比率を保つ（結果として顔に寄る）。
    """
    bw, bh = bg.size
    top = int(bh * CROP_TOP)
    keep_h = int(bh * (1 - CROP_TOP - CROP_BOTTOM))
    keep_w = min(bw, int(keep_h * 16 / 9))
    return bg.crop(((bw - keep_w) // 2, top, (bw - keep_w) // 2 + keep_w, top + keep_h))


def _line_width(d: ImageDraw.ImageDraw, segs: list[dict], base: int) -> int:
    return sum(int(d.textlength(s["t"], font=pick_font(int(base * s.get("s", 1.0)))))
               for s in segs)


def _max_scale(segs: list[dict]) -> float:
    return max((s.get("s", 1.0) for s in segs), default=1.0)


def _fit_base(d: ImageDraw.ImageDraw, lines: list[list[dict]], max_w: int,
              start: int) -> int:
    """全行が幅に収まる最大の基準サイズ。行ごとの倍率はここに掛かる。

    縁取りは文字の左右にはみ出す。textlength には含まれないので、
    その分を足してから判定しないと端が切れる。
    """
    base = start
    while base > 30:
        if all(_line_width(d, segs, base) + int(base * _max_scale(segs) / 3) <= max_w
               for segs in lines):
            return base
        base -= 4
    return 30


def _draw_line(d: ImageDraw.ImageDraw, cx: int, baseline: int,
               segs: list[dict], base: int) -> None:
    """1行を中央揃えで描く。サイズが違っても下端（ベースライン）を揃える。"""
    x = cx - _line_width(d, segs, base) // 2
    for s in segs:
        size = int(base * s.get("s", 1.0))
        f = pick_font(size)
        fill = COLORS.get(s.get("c", "r"), RED)
        stroke = max(7, size // 8)
        # 黒縁は2度描く。1度だと大きい文字で縁が痩せて背景に負ける
        for sw in (stroke, max(3, stroke // 2)):
            d.text((x, baseline), s["t"], font=f, fill=fill,
                   stroke_width=sw, stroke_fill=BLACK, anchor="ls")
        x += int(d.textlength(s["t"], font=f))


def render_thumbnail(bg: Image.Image, lines: list[list[dict]],
                     badge: str = "", size: tuple[int, int] = SIZE) -> Image.Image:
    """背景（動画のフレーム）に極太文字を載せる。

    lines は行のリスト。各行はセグメントのリストで、
    {"t": 文字列, "c": "r"|"y"|"w", "s": サイズ倍率} を取る。
    """
    w, h = size
    # 既に合成済み（掛け合いの2枚並べ）ならそのまま使う
    img = (bg.convert("RGB") if bg.size == size
           else _crop_16x9(bg).convert("RGB").resize(size, Image.LANCZOS))

    lines = [segs for segs in (lines or []) if segs]

    if lines:
        # 文字が乗る下側だけ沈める。全面を暗くすると顔が死ぬ
        shade = Image.new("L", size, 0)
        ImageDraw.Draw(shade).rectangle([0, int(h * 0.36), w, h], fill=165)
        img = Image.composite(Image.new("RGB", size, BLACK),
                              img, shade.filter(ImageFilter.GaussianBlur(70)))

    d = ImageDraw.Draw(img)
    m = int(w * 0.035)
    base = _fit_base(d, lines, w - m * 2, int(h * 0.30)) if lines else 0

    # 最大倍率の行が一番背が高い。行送りはそれに合わせる
    heights = [int(base * _max_scale(segs) * 1.06) for segs in lines]
    # ベースラインより下に伸びる字（う・す・らなど）と縁取りのぶん余白を取る。
    # 足りないと最終行の下端が切れる
    y = h - int(h * 0.11) if lines else h
    for segs, lh in zip(reversed(lines), reversed(heights)):
        _draw_line(d, w // 2, y, segs, base)
        y -= lh

    if badge.strip():
        bf = pick_font(int(h * 0.058))
        bw = int(d.textlength(badge, font=bf)) + int(w * 0.032)
        bh = int(h * 0.098)
        d.rectangle([m, int(h * 0.045), m + bw, int(h * 0.045) + bh], fill=RED)
        d.text((m + int(w * 0.016), int(h * 0.045) + int(bh * 0.15)), badge,
               font=bf, fill=WHITE)
    return img
