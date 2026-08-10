#!/usr/bin/env python3
"""サムネイルの描画。

競合の上位サムネを実際に落として採寸した型をそのまま組む。
基準にしたのは「詰められて不貞腐れる↓／細井社長ブチギレ」（101万回）。

  ┌──────────────────────┐
  │ 黒帯：赤文字＋黄文字（1行の中で色を変える）  │ 0〜17%
  ├──────────────────────┤
  │  左の人     白い吹き出し      右の人      │ 17〜100%
  │            ・赤文字＝左の発言              │
  │            ・桃文字＝右の発言              │
  │  極太の赤文字＋白縁＋黒縁（下に重ねる）      │
  └──────────────────────┘

**この型は元動画のテロップを結果的に覆い隠す。** 上部の黒帯が告知を、
下部の極太文字が字幕を潰すので、切り抜きもぼかしも要らない。
切り抜きチャンネル向けに最適化された型だと分かる。

**文言は元動画で実際に話されていることだけを使う。** ガイドラインが禁じている
のは「出演者の名誉・信用を害し、または人格を侮辱する文字表記」であって、
発言の引用ではない。話していないことを盛るのは誇張になるのでしない。

**引用はASR字幕から取らない。** 元動画が焼き込んでいる公式テロップを映像で
読んで使う。実際、ASRは「倍にして返してもらう」、公式テロップは
「倍にして返してもらおう」で食い違っていた。
"""

from __future__ import annotations

from PIL import Image, ImageDraw

from scripts.draw import pick_font

SIZE = (1280, 720)

RED = (230, 0, 24)
YELLOW = (255, 240, 0)
MAGENTA = (255, 0, 220)
WHITE = (255, 255, 255)
BLACK = (8, 8, 10)
COLORS = {"r": RED, "y": YELLOW, "m": MAGENTA, "w": WHITE, "k": BLACK}

BAND_H = 0.165          # 上の黒帯の高さ
PHOTO_TOP = 0.17        # 元フレームの上をこれだけ落とす。募集告知が入らない高さ


def _stroked(d: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font,
             fill, anchor: str = "ls", halo: bool = True) -> None:
    """黒→白→本体の3重で描く。競合はこの重ね方で背景に負けないようにしている。"""
    size = font.size
    if halo:
        d.text(xy, text, font=font, fill=fill, anchor=anchor,
               stroke_width=max(8, size // 7), stroke_fill=BLACK)
        d.text(xy, text, font=font, fill=fill, anchor=anchor,
               stroke_width=max(4, size // 14), stroke_fill=WHITE)
    d.text(xy, text, font=font, fill=fill, anchor=anchor)


def _fit(d: ImageDraw.ImageDraw, segs: list[dict], max_w: int, start: int) -> int:
    """1行が幅に収まる最大サイズ。縁のはみ出しぶんも見込む。"""
    size = start
    while size > 24:
        w = sum(int(d.textlength(s["t"], font=pick_font(size))) for s in segs)
        if w + size // 2 <= max_w:
            return size
        size -= 4
    return 24


def _draw_row(d: ImageDraw.ImageDraw, segs: list[dict], cx: int, baseline: int,
              size: int, halo: bool = True) -> None:
    """1行を中央揃えで。セグメントごとに色を変える（赤＋黄の混色）。"""
    f = pick_font(size)
    total = sum(int(d.textlength(s["t"], font=f)) for s in segs)
    x = cx - total // 2
    for s in segs:
        _stroked(d, (x, baseline), s["t"], f, COLORS.get(s.get("c", "r"), RED),
                 halo=halo)
        x += int(d.textlength(s["t"], font=f))


def _bubble(img: Image.Image, text: str, color, cx: int, cy: int,
            max_w: int, side: str) -> int:
    """白い角丸の吹き出し。side の方向に小さな尻尾を出す。次の行までの高さを返す。"""
    d0 = ImageDraw.Draw(img)
    size = 52
    while size > 20 and d0.textlength(text, font=pick_font(size)) > max_w * 0.86:
        size -= 2
    f = pick_font(size)
    tw = int(d0.textlength(text, font=f))
    bw, bh = tw + int(size * 1.5), int(size * 1.8)

    layer = Image.new("RGBA", (bw + size, bh + 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    ox = size // 2
    d.rounded_rectangle([ox, 0, ox + bw, bh], radius=bh // 2,
                        fill=WHITE + (255,), outline=BLACK + (255,), width=5)
    tail = ([(ox + 4, bh * 0.34), (0, bh * 0.56), (ox + 4, bh * 0.72)] if side == "l"
            else [(ox + bw - 4, bh * 0.34), (bw + size, bh * 0.56),
                  (ox + bw - 4, bh * 0.72)])
    d.polygon(tail, fill=WHITE + (255,), outline=BLACK + (255,))
    d.text((ox + bw // 2, bh // 2), text, font=f, fill=color, anchor="mm")

    img.paste(layer, (cx - layer.width // 2, cy), layer)
    return bh + int(size * 0.30)


# 被写体をパネル内のどこに置くか。**外側に寄せて中央に通路を作る。**
# 参考サムネは2人を左右の端に寄せ、空いた中央に吹き出しを置いている。
# 中央に顔があると吹き出しが必ず顔に被る（実際に被った）。
OUT_BIAS = 0.34


def compose_photos(frames: list[Image.Image], xs: list[float] | None = None,
                   size: tuple[int, int] = SIZE,
                   biases: list[float] | None = None) -> Image.Image:
    """写真を左右に並べる。黒帯の下から下端まで敷き、被写体は外側へ寄せる。"""
    w, h = size
    n = len(frames)
    pw = w // n
    top = int(h * BAND_H)
    ph = h - top
    xs = list(xs or [0.5] * n)

    biases = list(biases or [None] * n)

    img = Image.new("RGB", size, BLACK)
    for i, fr in enumerate(frames):
        fr = fr.convert("RGB")
        fw, fh = fr.size
        keep_h = int(fh * (1 - PHOTO_TOP))
        keep_w = min(fw, int(keep_h * pw / ph))
        x = xs[i] if i < len(xs) else 0.5

        # 被写体をパネル内の target の位置に置く。外側の端に寄せる
        b = biases[i] if i < len(biases) and biases[i] is not None else OUT_BIAS
        target = b if i < n / 2 else 1 - b
        left = max(0, min(fw - keep_w, int(fw * x - keep_w * target)))
        panel = fr.crop((left, int(fh * PHOTO_TOP), left + keep_w, fh))
        img.paste(panel.resize((pw, ph), Image.LANCZOS), (i * pw, top))
    return img


def render_thumbnail(photo: Image.Image, top: list[dict] | None = None,
                     bubbles: list[dict] | None = None,
                     bottom: list[dict] | None = None,
                     size: tuple[int, int] = SIZE) -> Image.Image:
    """採寸した型で組む。

    top     黒帯に乗せる行。[{"t": 文字, "c": "r"|"y"}, ...]
    bubbles 吹き出し。[{"t": 文字, "c": "r"|"m", "side": "l"|"r"}, ...]
    bottom  下の極太行。[{"t": 文字, "c": "r"|"y"}, ...]
    """
    w, h = size
    img = photo.convert("RGB")
    if img.size != size:
        img = img.resize(size, Image.LANCZOS)
    d = ImageDraw.Draw(img)

    band_h = int(h * BAND_H)
    d.rectangle([0, 0, w, band_h], fill=BLACK)
    if top:
        s = _fit(d, top, int(w * 0.96), int(band_h * 0.95))
        _draw_row(d, top, w // 2, int(band_h * 0.82), s, halo=False)

    if bubbles:
        y = band_h + int(h * 0.035)
        for b in bubbles:
            y += _bubble(img, b["t"], COLORS.get(b.get("c", "r"), RED),
                         w // 2, y, int(w * 0.56), b.get("side", "l"))
        d = ImageDraw.Draw(img)

    if bottom:
        s = _fit(d, bottom, int(w * 0.96), int(h * 0.20))
        _draw_row(d, bottom, w // 2, h - int(h * 0.045), s)
    return img
