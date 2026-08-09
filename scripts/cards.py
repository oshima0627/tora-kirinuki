#!/usr/bin/env python3
"""図解カードの描画。

令和の虎は「志願者が事業計画を持ち込む→虎が詰める→出資判定」という
定型構造を持つ。元動画に無い整理をこの3枚で足す。
既存の切り抜きは全員が字幕止まりなので、ここが差別化の実体になる。

  案件カード  冒頭      希望金額 / 事業内容 / 志願者の経歴
  論点カード  詰めどころ 虎の指摘を1行に圧縮（映像に重ねる）
  判定カード  末尾      誰がいくら出したか。決裂ならその理由

配色はチャンネルのアイコン・バナーに揃える（白地に赤、差し色に金）。
"""

from __future__ import annotations

from PIL import Image, ImageDraw

from scripts.draw import (BG_BOTTOM, BG_TOP, GOLD, INK, MUTED, RED,  # noqa: F401
                          fit_font, pick_font, wrap)

SIZE = (1920, 1080)


def _ground(size: tuple[int, int]) -> Image.Image:
    w, h = size
    img = Image.new("RGB", size, BG_TOP)
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=tuple(
            int(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOTTOM)))
    # 左端に赤の帯。3枚のカードに共通の目印にする
    d.rectangle([0, 0, int(w * 0.014), h], fill=RED)
    return img


def _labelled(d: ImageDraw.ImageDraw, x: int, y: int, avail: int,
              label: str, value: str, h: int) -> int:
    """小さいラベルの下に本文を置く。次のyを返す。"""
    value = (value or "").strip()
    if not value:
        return y
    d.text((x, y), label, font=pick_font(int(h * 0.030)), fill=MUTED)
    f = pick_font(int(h * 0.052))
    lines = wrap(d, value, f, avail)[:2]
    yy = y + int(h * 0.042)
    for ln in lines:
        d.text((x, yy), ln, font=f, fill=INK)
        yy += int(h * 0.062)
    return yy + int(h * 0.036)


def render_brief(brief: dict, size: tuple[int, int] = SIZE) -> Image.Image:
    """案件カード。希望金額を主役に置く。"""
    w, h = size
    img = _ground(size)
    d = ImageDraw.Draw(img)
    x = int(w * 0.10)
    avail = w - x - int(w * 0.08)

    amount = (brief.get("amount") or "").strip()
    if amount:
        f = fit_font(d, amount, avail, int(h * 0.125))
        d.text((x, int(h * 0.17)), amount, font=f, fill=RED)

    d.rectangle([x, int(h * 0.345), x + avail, int(h * 0.345) + 4], fill=GOLD)

    y = int(h * 0.42)
    y = _labelled(d, x, y, avail, "事業内容", brief.get("business", ""), h)
    _labelled(d, x, y, avail, "志願者", brief.get("profile", ""), h)
    return img


def render_point(text: str, size: tuple[int, int] = SIZE) -> Image.Image:
    """論点カード。映像に重ねるので帯だけを描いた透過画像を返す。

    **帯は画面上部に置く。** 令和の虎Secondは画面下部に大きなテロップを常時
    焼き込んでいるので、下に置くと必ずぶつかる。実ビルドで確認したところ、
    帯からはみ出した元の文字が上下に残って両方読めなくなった。
    上部にあるのは小さな注記と募集告知だけなので、こちらのほうが被害が小さい。

    帯は不透明にする。半透明だと下の文字が透けて同じことが起きる。
    """
    w, h = size
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    text = (text or "").strip()
    if not text:
        return img

    d = ImageDraw.Draw(img)
    f = pick_font(int(h * 0.058))
    m = int(w * 0.06)
    lines = wrap(d, text, f, w - m * 2 - int(w * 0.03))[:2]

    line_h = int(h * 0.082)
    # 元動画は上部にも小さな注記と募集告知を出す。1行のときでも覆いきれるよう
    # 最低の高さを決めておく。中途半端に覆うと相手の文字の下端だけが残って汚い
    band_h = max(line_h * len(lines) + int(h * 0.048), int(h * 0.17))
    top = 0

    d.rectangle([0, top, w, top + band_h], fill=BG_TOP + (255,))
    d.rectangle([0, top, int(w * 0.014), top + band_h], fill=RED + (255,))

    yy = top + int(h * 0.024)
    for ln in lines:
        d.text((m, yy), ln, font=f, fill=INK + (255,))
        yy += line_h
    return img


# 縦型（Shorts）。
#
# 競合の上位ショートを落として採寸した型に合わせる。
#
#   上部の黒帯   見出し2行（白＋赤の混色、太い黒縁）
#   中央の映像   **16:9を縦にトリミングして顔を大きく**。ここが一番効く
#   下部の黒帯   発言をそのまま字幕で
#
# 16:9をそのまま幅に合わせると映像が小さくなり、縦型として弱い。
# 上下の黒帯は元動画の告知と字幕を覆い隠す役割も兼ねる。
SHORT_SIZE = (1080, 1920)
SHORT_TOP = 0.24             # 上の黒帯
SHORT_BOTTOM = 0.24          # 下の黒帯
SHORT_INK = (250, 250, 252)
SHORT_RED = (240, 40, 44)
SHORT_COLORS = {"w": SHORT_INK, "r": SHORT_RED, "y": (255, 226, 60)}


def _short_row(d: ImageDraw.ImageDraw, segs: list[dict], cx: int, baseline: int,
               size: int) -> None:
    f = pick_font(size)
    total = sum(int(d.textlength(x["t"], font=f)) for x in segs)
    x = cx - total // 2
    for seg in segs:
        col = SHORT_COLORS.get(seg.get("c", "w"), SHORT_INK)
        d.text((x, baseline), seg["t"], font=f, fill=col, anchor="ls",
               stroke_width=max(6, size // 8), stroke_fill=(0, 0, 0))
        d.text((x, baseline), seg["t"], font=f, fill=col, anchor="ls")
        x += int(d.textlength(seg["t"], font=f))


def _short_fit(d: ImageDraw.ImageDraw, rows: list[list[dict]], max_w: int,
               start: int) -> int:
    size = start
    while size > 26:
        if all(sum(int(d.textlength(x["t"], font=pick_font(size))) for x in r)
               + size // 2 <= max_w for r in rows):
            return size
        size -= 3
    return 26


def render_short_frame(head: list[list[dict]] | None = None,
                       quote: list[list[dict]] | None = None,
                       size: tuple[int, int] = SHORT_SIZE) -> Image.Image:
    """縦型の下地。映像を重ねる中央部分は透過にして返す。"""
    w, h = size
    top_h, bot_y = int(h * SHORT_TOP), int(h * (1 - SHORT_BOTTOM))

    img = Image.new("RGBA", size, (0, 0, 0, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([0, top_h, w, bot_y], fill=(0, 0, 0, 0))     # 映像の穴

    m = int(w * 0.05)
    avail = w - m * 2

    head = [r for r in (head or []) if r]
    if head:
        s = _short_fit(d, head, avail, int(h * 0.048))
        lh = int(s * 1.28)
        y = (top_h - lh * len(head)) // 2 + int(s * 0.95)
        for row in head:
            _short_row(d, row, w // 2, y, s)
            y += lh

    quote = [r for r in (quote or []) if r]
    if quote:
        # 下の字幕は見出しより大きくする。縦型では発言が主役になる
        s = _short_fit(d, quote, avail, int(h * 0.065))
        lh = int(s * 1.22)
        y = bot_y + (h - bot_y - lh * len(quote)) // 2 + int(s * 0.95)
        for row in quote:
            _short_row(d, row, w // 2, y, s)
            y += lh
    return img


def render_verdict(verdict: dict, size: tuple[int, int] = SIZE) -> Image.Image:
    """判定カード。誰がいくら出したか。決裂ならその理由。"""
    w, h = size
    img = _ground(size)
    d = ImageDraw.Draw(img)
    x = int(w * 0.10)
    avail = w - x - int(w * 0.08)

    result = (verdict.get("result") or "").strip()
    if result:
        f = fit_font(d, result, avail, int(h * 0.145))
        d.text((x, int(h * 0.24)), result, font=f, fill=RED)

    d.rectangle([x, int(h * 0.455), x + avail, int(h * 0.455) + 4], fill=GOLD)

    detail = (verdict.get("detail") or "").strip()
    if detail:
        f = pick_font(int(h * 0.056))
        yy = int(h * 0.53)
        for ln in wrap(d, detail, f, avail)[:3]:
            d.text((x, yy), ln, font=f, fill=INK)
            yy += int(h * 0.072)
    return img
