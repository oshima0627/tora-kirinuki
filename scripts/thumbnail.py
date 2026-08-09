#!/usr/bin/env python3
"""サムネイルの描画。

競合の上位サムネ（数百万回再生）を実際に落として調べた型を再現する。

  ・**黒帯は置かない。** 文字は顔の上に直接載せ、縁取りだけで読ませる
  ・**縁は2重。** 色地＋差し色の縁＋黒縁。1重だと背景に負ける
  ・**1行の中で文字サイズを変える**（抑揚）。強い語だけ極端に大きい
  ・掛け合いは**左右に2人**を全高で並べ、引用は**斜めの赤リボン**に黄文字
  ・隅に小さい補助ラベル（白文字＋太い黒縁）
  ・赤・黄・白・黒の高彩度のみ

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

RED = (234, 26, 34)
YELLOW = (255, 214, 0)
WHITE = (255, 255, 255)
BLACK = (12, 12, 14)
COLORS = {"r": RED, "y": YELLOW, "w": WHITE}
# 縁の差し色。競合は「赤地に黄縁」「白地に赤縁」を多用する
EDGE = {"r": YELLOW, "y": BLACK, "w": RED}

# 元動画は上下にテロップを焼き込む。顔が残る帯だけを使う
PANEL_TOP, PANEL_BOTTOM = 0.155, 0.02


def cutout(frame: Image.Image):
    """人物だけを抜いた RGBA を返す。rembg が無ければ None。"""
    try:
        from rembg import remove
    except ImportError:
        return None
    try:
        return remove(frame.convert("RGB")).convert("RGBA")
    except Exception:                                   # noqa: BLE001
        return None


def person_center(frame: Image.Image) -> float | None:
    """人物の横方向の中心（0..1）。抜けなければ None。

    顔検出は使わない。OpenCV 5 は Haar カスケードを廃止しており、
    後継の FaceDetectorYN は別途モデルが要る。**人物を抜けばその輪郭が
    そのまま位置を教えてくれる**ので、検出器は不要だった。
    """
    person = cutout(frame)
    if person is None:
        return None
    box = person.getbbox()
    return ((box[0] + box[2]) / 2) / frame.width if box else None


BLUR_BAND = 0.30      # 下からこの割合を強くぼかす（元テロップを潰す）


def _blur_caption_band(img: Image.Image) -> Image.Image:
    """元動画のテロップが乗る下帯だけを強くぼかす。

    **切り落とさずにぼかす。** 落とすと顎まで切れるフレームがあり、
    かといって残すとこちらの文字と二重になる。ぼかせば被写界深度のように
    見えて顔は大きいまま、元の文字だけが読めなくなる。
    """
    w, h = img.size
    band_top = int(h * (1 - BLUR_BAND))
    blurred = img.filter(ImageFilter.GaussianBlur(w // 12))

    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rectangle([0, band_top, w, h], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(h // 22))   # 境目をぼかす
    return Image.composite(blurred, img, mask)


def crop_panel(bg: Image.Image, x: float, out: tuple[int, int]) -> Image.Image:
    """out の比率で切り出す。x は横方向の中心（0..1）。"""
    bw, bh = bg.size
    top = int(bh * PANEL_TOP)
    keep_h = int(bh * (1 - PANEL_TOP - PANEL_BOTTOM))
    keep_w = min(bw, int(keep_h * out[0] / out[1]))
    left = max(0, min(bw - keep_w, int(bw * x) - keep_w // 2))
    panel = bg.crop((left, top, left + keep_w, top + keep_h)).resize(out, Image.LANCZOS)
    return _blur_caption_band(panel)


def compose_faces(frames: list[Image.Image], xs: list[float | None] | None = None,
                  size: tuple[int, int] = SIZE, cut: bool = False) -> Image.Image:
    """掛け合いの2人を左右に全高で並べる。

    **既定は全面写真（cut=False）。** 競合の2人掛け合い型は切り抜きではなく
    全面写真を並べている。切り抜きを使うのは多人数コラージュ型のほう。
    実際に抜いてみたところ、人物が端に寄ったパネルでは分離に失敗した。
    cut=True にすると、ぼかした背景の上に抜いた人物を置く。
    """
    w, h = size
    n = len(frames)
    pw = w // n
    xs = list(xs or [None] * n)

    img = Image.new("RGB", size, BLACK)
    for i, fr in enumerate(frames):
        x = xs[i] if i < len(xs) and xs[i] is not None else 0.5
        # **先にパネル領域へ切ってから抜く。** フレーム全体に掛けると画面内の
        # 別の人物や机まで残り、1人に絞れない（実際にそうなった）
        panel = crop_panel(fr.convert("RGB"), x, (pw, h))

        person = cutout(panel) if cut else None
        if person is None:
            img.paste(panel, (i * pw, 0))
            continue

        # 背景は同じ画をぼかして暗く沈める。人物だけが立ち、元のテロップも潰れる
        back = panel.filter(ImageFilter.GaussianBlur(22))
        img.paste(Image.blend(back, Image.new("RGB", back.size, BLACK), 0.55),
                  (i * pw, 0))
        img.paste(person, (i * pw, 0), person)

    d = ImageDraw.Draw(img)
    for i in range(1, n):
        d.rectangle([i * pw - 3, 0, i * pw + 2, h], fill=BLACK)
    return img


def _line_width(d: ImageDraw.ImageDraw, segs: list[dict], base: int) -> int:
    return sum(int(d.textlength(s["t"], font=pick_font(int(base * s.get("s", 1.0)))))
               for s in segs)


def _max_scale(segs: list[dict]) -> float:
    return max((s.get("s", 1.0) for s in segs), default=1.0)


def _fit_base(d: ImageDraw.ImageDraw, lines: list[list[dict]], max_w: int,
              start: int) -> int:
    """全行が幅に収まる最大の基準サイズ。

    縁は文字の左右にはみ出すが textlength に含まれない。足してから判定する。
    """
    base = start
    while base > 30:
        if all(_line_width(d, segs, base) + int(base * _max_scale(segs) / 2.4) <= max_w
               for segs in lines):
            return base
        base -= 4
    return 30


def _draw_line(d: ImageDraw.ImageDraw, cx: int, baseline: int,
               segs: list[dict], base: int) -> None:
    """1行を中央揃えで描く。縁は黒→差し色の2重。サイズが違っても下端を揃える。"""
    x = cx - _line_width(d, segs, base) // 2
    for s in segs:
        size = int(base * s.get("s", 1.0))
        f = pick_font(size)
        key = s.get("c", "r")
        fill, edge = COLORS.get(key, RED), EDGE.get(key, BLACK)
        outer, inner = max(9, size // 7), max(4, size // 14)
        d.text((x, baseline), s["t"], font=f, fill=fill,
               stroke_width=outer, stroke_fill=BLACK, anchor="ls")
        d.text((x, baseline), s["t"], font=f, fill=fill,
               stroke_width=inner, stroke_fill=edge, anchor="ls")
        d.text((x, baseline), s["t"], font=f, fill=fill, anchor="ls")
        x += int(d.textlength(s["t"], font=f))


def _ribbon(img: Image.Image, text: str, size: tuple[int, int]) -> None:
    """斜めの赤リボンに黄文字。競合が引用を載せるときの定番。"""
    w, h = size
    f = pick_font(int(h * 0.082))
    tw = int(ImageDraw.Draw(img).textlength(text, font=f))
    pad = int(h * 0.035)

    band = Image.new("RGBA", (tw + pad * 2, int(h * 0.15)), RED + (255,))
    bd = ImageDraw.Draw(band)
    bd.text((pad, band.height // 2), text, font=f, fill=YELLOW,
            stroke_width=max(3, f.size // 12), stroke_fill=BLACK, anchor="lm")
    band = band.rotate(6, expand=True, resample=Image.BICUBIC)
    img.paste(band, ((w - band.width) // 2, int(h * 0.05)), band)


def render_thumbnail(bg: Image.Image, lines: list[list[dict]], badge: str = "",
                     ribbon: str = "", size: tuple[int, int] = SIZE) -> Image.Image:
    """背景に極太文字を載せる。**黒帯は置かない。**

    lines は行のリスト。各行は {"t": 文字, "c": "r"|"y"|"w", "s": 倍率} の並び。
    """
    w, h = size
    img = bg.convert("RGB") if bg.size == size else crop_panel(bg, 0.5, size)
    lines = [segs for segs in (lines or []) if segs]

    d = ImageDraw.Draw(img)
    m = int(w * 0.03)
    base = _fit_base(d, lines, w - m * 2, int(h * 0.30)) if lines else 0

    heights = [int(base * _max_scale(segs) * 1.02) for segs in lines]
    y = h - int(h * 0.09) if lines else h
    for segs, lh in zip(reversed(lines), reversed(heights)):
        _draw_line(d, w // 2, y, segs, base)
        y -= lh

    if ribbon.strip():
        _ribbon(img, ribbon, size)

    if badge.strip():
        bf = pick_font(int(h * 0.055))
        d.text((m, int(h * 0.045)), badge, font=bf, fill=WHITE,
               stroke_width=max(4, bf.size // 8), stroke_fill=BLACK)
    return img
