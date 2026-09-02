#!/usr/bin/env python3
"""サムネイルの描画。

競合の上位サムネを実際に落として採寸した型をそのまま組む。
基準にしたのは「詰められて不貞腐れる↓／細井社長ブチギレ」（101万回）。

  ┌──────────────────────┐
  │ 黒帯：金＋明るい赤（1行の中で色を変える）    │ 0〜17%
  ├──────────────────────┤
  │  左の人     白い吹き出し      右の人      │ 17〜100%
  │            ・赤文字＝左の発言              │
  │            ・濃紺＝右の発言                │
  │  幕（黒のグラデーション）の上に縁なしの文字  │ 70〜100%
  └──────────────────────┘

**この型は元動画のテロップを結果的に覆い隠す。** 上部の黒帯が告知を、
下部の幕が字幕を沈めるので、切り抜きもぼかしも要らない。
切り抜きチャンネル向けに最適化された型だと分かる。

**2026-09-02 に意匠を作り直した。** それまでは競合をそのまま写して
黒縁＋白縁＋本体の三重で描いていたが、**画数の多い漢字の内側が塗り潰されて
読めなくなっていた**（「体験」「加盟」で実測）。縁で背景に勝つのをやめ、
下地（黒帯・幕・白い吹き出し）で勝つ形に変えた。縁は1本も使っていない。
マゼンタも廃止した。

**文言は元動画で実際に話されていることだけを使う。** ガイドラインが禁じている
のは「出演者の名誉・信用を害し、または人格を侮辱する文字表記」であって、
発言の引用ではない。話していないことを盛るのは誇張になるのでしない。

**引用はASR字幕から取らない。** 元動画が焼き込んでいる公式テロップを映像で
読んで使う。実際、ASRは「倍にして返してもらう」、公式テロップは
「倍にして返してもらおう」で食い違っていた。
"""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFilter

from scripts.draw import pick_font

SIZE = (1280, 720)

RED = (232, 28, 46)
YELLOW = (255, 214, 64)
# 相手の発言。**マゼンタはやめた。** 彩度が高すぎて2018年頃のサムネに見える
NAVY = (28, 52, 92)
WHITE = (255, 255, 255)
BLACK = (8, 8, 10)
COLORS = {"r": RED, "y": YELLOW, "m": NAVY, "w": WHITE, "k": BLACK}

# 暗い下地（上の黒帯・下段の幕）に乗せる色。**同じ赤だと沈んで読めない。**
# 白地の吹き出し用の RED をそのまま黒の上に置くと、幕の上でほとんど識別できなかった
# （2026-09-02 に実測）。明度を上げたぶん、白地では逆に浅く見えるので使い分ける。
ON_DARK = {"r": (255, 82, 96), "y": YELLOW, "m": (150, 196, 255),
           "w": WHITE, "k": BLACK}

BAND_H = 0.165          # 上の黒帯の高さ
PHOTO_TOP = 0.17        # 元フレームの上をこれだけ落とす。募集告知が入らない高さ

# 下段の下地。**縁ではなく幕で読ませる。**
# 以前は黒縁＋白縁＋本体の三重で描いていたが、16文字を幅に詰めると
# フォントが68px前後まで落ち、そこに9pxの黒縁と4pxの白縁が乗って
# 「験」「盟」「社」の内側が塗り潰された（2026-09-02 に実測）。
# 幕を敷けば縁は1本も要らないので、画数が多くても潰れない。
VEIL_H = 0.30
VEIL_ALPHA = 225
VEIL_GAMMA = 1.35


def _fit(d: ImageDraw.ImageDraw, segs: list[dict], max_w: int, start: int) -> int:
    """1行が幅に収まる最大サイズ。"""
    size = start
    while size > 24:
        w = sum(int(d.textlength(s["t"], font=pick_font(size))) for s in segs)
        if w <= max_w:
            return size
        size -= 4
    return 24


def _draw_row(d: ImageDraw.ImageDraw, segs: list[dict], cx: int, baseline: int,
              size: int, palette: dict | None = None) -> None:
    """1行を中央揃えで。セグメントごとに色を変える。**縁は付けない。**"""
    pal = palette or COLORS
    f = pick_font(size)
    total = sum(int(d.textlength(s["t"], font=f)) for s in segs)
    x = cx - total // 2
    for s in segs:
        d.text((x, baseline), s["t"], font=f, anchor="ls",
               fill=pal.get(s.get("c", "r"), pal["r"]))
        x += int(d.textlength(s["t"], font=f))


def _dropped(layer: Image.Image, blur: int = 9, dy: int = 5,
             alpha: int = 120) -> Image.Image:
    """レイヤーの下に影を敷いた新しいレイヤーを返す。

    **黒縁の代わり。** 縁は文字にも輪郭にも食い込むが、影は外側にしか出ない。
    """
    pad = blur * 3
    out = Image.new("RGBA", (layer.width + pad * 2, layer.height + pad * 2),
                    (0, 0, 0, 0))
    tint = Image.new("RGBA", layer.size, BLACK + (0,))
    tint.putalpha(layer.split()[3].point(lambda v: min(alpha, v)))
    shade = Image.new("RGBA", out.size, (0, 0, 0, 0))
    shade.paste(tint, (pad, pad + dy))
    out.alpha_composite(shade.filter(ImageFilter.GaussianBlur(blur)))
    out.alpha_composite(layer, (pad, pad))
    return out


BUBBLE_RADIUS = 0.26     # 高さに対する角丸の半径。ピル型（0.5）は古く見える


def _bubble_layer(text: str, color, max_w: int, side: str) -> Image.Image:
    """白い角丸の吹き出しを1枚作る。side の方向に小さな尻尾を出す。

    **黒縁は付けない。** 5pxの黒縁は輪郭を太らせるだけで、白地の上の文字は
    もともと背景に負けない。浮かせるのは影の仕事にした。
    """
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    size = 52
    while size > 20 and probe.textlength(text, font=pick_font(size)) > max_w * 0.88:
        size -= 2
    f = pick_font(size)
    tw = int(probe.textlength(text, font=f))
    bw, bh = tw + int(size * 1.15), int(size * 1.66)
    tail_w = int(size * 0.42)

    layer = Image.new("RGBA", (bw + tail_w, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    ox = tail_w if side == "l" else 0
    d.rounded_rectangle([ox, 0, ox + bw, bh], radius=int(bh * BUBBLE_RADIUS),
                        fill=WHITE + (255,))
    tail = ([(ox, bh * 0.40), (ox - tail_w, bh * 0.56), (ox, bh * 0.72)]
            if side == "l"
            else [(ox + bw, bh * 0.40), (ox + bw + tail_w, bh * 0.56),
                  (ox + bw, bh * 0.72)])
    d.polygon(tail, fill=WHITE + (255,))
    d.text((ox + bw // 2, bh // 2 + 2), text, font=f, fill=color, anchor="mm")
    return _dropped(layer)


# 吹き出しの横幅の上限。**顔にかからない幅に抑える。**
# 顔を寄りで切ると顔幅がパネルの7割を超え、中央の通路が狭くなる。
# 0.56 だと 2026-09-02 のサムネで両方の顔に被った。狭めると文字が自動で小さくなるが、
# 顔の上に文字が乗るよりは読める（実測で比較して 0.48 にした）。
BUBBLE_MAX_W = 0.48

# 吹き出しの下端をここに合わせる。**目元ではなく口元の高さに置く。**
# 顔は顎に向かって細くなるので、下のほうが左右の余白を取りやすい。
# 目元に置くと、外側に寄せても顔幅が広い位置で当たってしまう。
BUBBLE_BOTTOM = 0.74
BUBBLE_GAP = 0.022

# 被写体をパネル内のどこに置くか。**外側に寄せて中央に通路を作る。**
# 参考サムネは2人を左右の端に寄せ、空いた中央に吹き出しを置いている。
# 中央に顔があると吹き出しが必ず顔に被る（実際に被った）。
OUT_BIAS = 0.34

# 下の極太行。**右下は再生時間のバッジに食われる。**
# YouTube はサムネの右下角に「6:32」の黒バッジを重ねて描く。1280x720 換算で
# おおよそ x=1145..1272 / y=665..700。ここに文字を置くと末尾が読めなくなる。
# 幅を詰めて中央寄せのまま右端を手前で止め、ベースラインも少し上げて避ける。
BOTTOM_MAX_W = 0.88
BOTTOM_BASELINE = 0.075


def compose_photos(frames: list[Image.Image], xs: list[float] | None = None,
                   size: tuple[int, int] = SIZE,
                   biases: list[float] | None = None,
                   tops: list[float] | None = None,
                   bottoms: list[float] | None = None) -> Image.Image:
    """写真を左右に並べる。黒帯の下から下端まで敷き、被写体は外側へ寄せる。

    tops は各写真の上をどれだけ落とすかの個別指定（既定は PHOTO_TOP）。
    立位の人物は頭がフレーム上部に近く、既定値だと頭が切れることがある
    （実例：関西版の進行役が壇上に立つカット）。その場合だけ値を小さくする。

    bottoms は下をどれだけ落とすかの個別指定（既定は0＝フレーム最下端まで使う）。
    元動画の会話テロップは画面下いっぱいに出ることが多く、crop_top では
    避けられない（下端は常にフレーム最下端に固定されるため）。テロップが
    残る場合はその face だけ bottoms を指定する。
    """
    w, h = size
    n = len(frames)
    pw = w // n
    top = int(h * BAND_H)
    ph = h - top
    xs = list(xs or [0.5] * n)

    biases = list(biases or [None] * n)
    tops_frac = list(tops or [None] * n)
    bottoms_frac = list(bottoms or [None] * n)

    img = Image.new("RGB", size, BLACK)
    for i, fr in enumerate(frames):
        fr = fr.convert("RGB")
        fw, fh = fr.size
        photo_top = tops_frac[i] if i < len(tops_frac) and tops_frac[i] is not None else PHOTO_TOP
        photo_bottom = bottoms_frac[i] if i < len(bottoms_frac) and bottoms_frac[i] is not None else 0.0
        keep_h = int(fh * (1 - photo_top - photo_bottom))
        keep_w = min(fw, int(keep_h * pw / ph))
        x = xs[i] if i < len(xs) else 0.5

        # 被写体をパネル内の target の位置に置く。外側の端に寄せる
        b = biases[i] if i < len(biases) and biases[i] is not None else OUT_BIAS
        target = b if i < n / 2 else 1 - b
        left = max(0, min(fw - keep_w, int(fw * x - keep_w * target)))
        bottom_y = int(fh * (1 - photo_bottom))
        panel = fr.crop((left, int(fh * photo_top), left + keep_w, bottom_y))
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
        s = _fit(d, top, int(w * 0.92), int(band_h * 0.88))
        _draw_row(d, top, w // 2, int(band_h * 0.80), s, ON_DARK)

    if bottom:
        # **先に幕を敷いてから文字を置く。** 吹き出しの影が幕に食われないよう
        # 吹き出しより前に描く
        vh = int(h * VEIL_H)
        ramp = Image.new("L", (1, vh))
        for i in range(vh):
            ramp.putpixel((0, i), int(VEIL_ALPHA * (i / vh) ** VEIL_GAMMA))
        veil = Image.new("RGBA", (w, vh), BLACK + (0,))
        veil.putalpha(ramp.resize((w, vh)))
        strip = img.crop((0, h - vh, w, h)).convert("RGBA")
        img.paste(Image.alpha_composite(strip, veil).convert("RGB"), (0, h - vh))
        d = ImageDraw.Draw(img)

    if bubbles:
        layers = [_bubble_layer(b["t"], COLORS.get(b.get("c", "r"), RED),
                                int(w * BUBBLE_MAX_W), b.get("side", "l"))
                  for b in bubbles]
        gap = int(h * BUBBLE_GAP)
        total = sum(l.height for l in layers) + gap * (len(layers) - 1)
        # 下端を口元の高さに合わせ、そこから上へ積む
        y = max(band_h + int(h * 0.02), int(h * BUBBLE_BOTTOM) - total)
        for l in layers:
            img.paste(l, (w // 2 - l.width // 2, y), l)
            y += l.height + gap
        d = ImageDraw.Draw(img)

    if bottom:
        s = _fit(d, bottom, int(w * BOTTOM_MAX_W), int(h * 0.125))
        _draw_row(d, bottom, w // 2, h - int(h * BOTTOM_BASELINE), s, ON_DARK)
    return img
