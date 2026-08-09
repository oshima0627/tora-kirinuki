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
# 元映像は16:9。**クロップしない。** 中央を1:1で抜くと、令和の虎Secondが
# 画面の端に出す氏名テロップや告知が途中で切れて雑に見える（実ビルドで確認）。
# 幅いっぱいに16:9のまま置き、余った上下を図解に使う。
# 映像は小さくなるが、「図解でわかる」を名乗る以上そちらが本体になる。
SHORT_SIZE = (1080, 1920)
SHORT_VIDEO = (1080, 608)    # 16:9 を幅1080に合わせた実寸
SHORT_VIDEO_Y = 560


def render_short_frame(hook: str, footer: str,
                       size: tuple[int, int] = SHORT_SIZE) -> Image.Image:
    """縦型の下地。映像を重ねる中央部分は透過にして返す。"""
    w, h = size
    vy, vh = SHORT_VIDEO_Y, SHORT_VIDEO[1]

    img = Image.new("RGBA", size, BG_TOP + (255,))
    d = ImageDraw.Draw(img)

    # 映像の穴。ここに overlay する
    d.rectangle([0, vy, w, vy + vh], fill=(0, 0, 0, 0))

    m = int(w * 0.075)
    avail = w - m * 2

    # 上：フック。冒頭2秒で読ませるので大きく
    d.rectangle([0, 0, int(w * 0.018), vy], fill=RED + (255,))
    hook = (hook or "").strip()
    if hook:
        f = pick_font(int(h * 0.044))
        lines = wrap(d, hook, f, avail)[:4]
        line_h = int(h * 0.055)
        y = max(int(h * 0.03), (vy - line_h * len(lines)) // 2)
        for ln in lines:
            d.text((m, y), ln, font=f, fill=INK + (255,))
            y += line_h

    # 下：図解。映像が小さいぶんここが本体になる
    by = vy + vh
    d.rectangle([m, by + int(h * 0.040), m + avail, by + int(h * 0.040) + 6],
                fill=GOLD + (255,))
    footer = (footer or "").strip()
    if footer:
        f = pick_font(int(h * 0.040))
        y = by + int(h * 0.085)
        for ln in wrap(d, footer, f, avail)[:5]:
            d.text((m, y), ln, font=f, fill=INK + (255,))
            y += int(h * 0.052)

    d.text((m, h - int(h * 0.048)), "続きは本編で｜図解でわかる令和の虎",
           font=pick_font(int(h * 0.022)), fill=MUTED + (255,))
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
