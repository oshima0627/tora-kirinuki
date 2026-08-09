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
PANEL_TOP, PANEL_BOTTOM = 0.155, 0.28


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


# 写真が占める高さ。残りは白地にして、そこに文字を置く。
# 元動画のテロップ帯は切り落とすので二重にならない
PHOTO_H = 0.70


def crop_panel(bg: Image.Image, x: float, out: tuple[int, int]) -> Image.Image:
    """out の比率で切り出す。x は横方向の中心（0..1）。"""
    bw, bh = bg.size
    top = int(bh * PANEL_TOP)
    keep_h = int(bh * (1 - PANEL_TOP - PANEL_BOTTOM))
    keep_w = min(bw, int(keep_h * out[0] / out[1]))
    left = max(0, min(bw - keep_w, int(bw * x) - keep_w // 2))
    return bg.crop((left, top, left + keep_w, top + keep_h)).resize(out, Image.LANCZOS)


def largest_part(person: Image.Image) -> Image.Image:
    """一番大きい塊だけを残す。

    切り抜きは元動画の告知テロップのような高コントラストの断片も拾う。
    人物本体だけを残せば、浮いた文字が消える。
    """
    try:
        import numpy as np
    except ImportError:
        return person

    a = np.array(person)[:, :, 3] > 40
    if not a.any():
        return person

    step = max(1, min(a.shape) // 200)          # 粗い格子で走査して速くする
    small = a[::step, ::step]
    seen = np.zeros_like(small, dtype=bool)
    best, best_n = None, 0
    h, w = small.shape
    for sy in range(h):
        for sx in range(w):
            if not small[sy, sx] or seen[sy, sx]:
                continue
            stack, comp = [(sy, sx)], []
            seen[sy, sx] = True
            while stack:
                y, x = stack.pop()
                comp.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and small[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            if len(comp) > best_n:
                best, best_n = comp, len(comp)

    if best is None:
        return person
    keep = np.zeros_like(small)
    for y, x in best:
        keep[y, x] = True
    mask = np.repeat(np.repeat(keep, step, 0), step, 1)[:a.shape[0], :a.shape[1]]
    out = np.array(person)
    out[:, :, 3] = np.where(mask, out[:, :, 3], 0)
    return Image.fromarray(out, "RGBA")


def crop_region(bg: Image.Image, x: float, wfrac: float = 0.52) -> Image.Image:
    """人物を含む広めの領域を切る。切り抜きに掛ける前段。

    ここで狭く切ると人物が途中で切れ、抜いたときに欠けた形になる。
    **上下は削らない。** 上を削ると頭頂部が欠ける。上端の告知は人物に
    重なっていなければ、抜くときに背景として一緒に消える。
    """
    bw, bh = bg.size
    kw = int(bw * wfrac)
    left = max(0, min(bw - kw, int(bw * x) - kw // 2))
    return bg.crop((left, 0, left + kw, bh))


def compose_faces(frames: list[Image.Image], xs: list[float | None] | None = None,
                  size: tuple[int, int] = SIZE, cut: bool = True) -> Image.Image:
    """白地の上に、抜いた人物を左右に並べる。

    **背景ごと抜くので元動画のテロップは自動的に消える。** 帯を切ったり
    ぼかしたりする必要がない。人物に重ならない位置にテロップがあるシーンを
    選ぶことだけが条件になる。

    人物は縦横比を保ったまま枠に収める。はみ出す側に合わせて縮めるので、
    **顔が切れることがない。**
    """
    w, h = size
    n = len(frames)
    pw, ph = w // n, int(h * PHOTO_H)
    xs = list(xs or [None] * n)

    img = Image.new("RGB", size, WHITE)
    for i, fr in enumerate(frames):
        x = xs[i] if i < len(xs) and xs[i] is not None else 0.5
        region = crop_region(fr.convert("RGB"), x)
        person = cutout(region) if cut else None
        if person is None:
            img.paste(crop_panel(fr.convert("RGB"), x, (pw, ph)), (i * pw, 0))
            continue

        person = largest_part(person)
        box = person.getbbox()
        if box:
            person = person.crop(box)
        # 枠いっぱいだと頭が縁に接する。少し余白を残す
        scale = min(pw / person.width, ph * 0.94 / person.height)
        person = person.resize((max(1, int(person.width * scale)),
                                max(1, int(person.height * scale))), Image.LANCZOS)
        img.paste(person, (i * pw + (pw - person.width) // 2, ph - person.height),
                  person)
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
