"""ショートの下帯に焼く字幕の描画。

映像の上に重ねるオーバーレイなので、字幕を置く下帯以外はすべて透過で返す。
"""

from scripts.cards import (SHORT_BOTTOM, SHORT_SIZE, SHORT_TOP,
                           render_short_caption)

W, H = SHORT_SIZE
BAND_TOP = int(H * (1 - SHORT_BOTTOM))


def opaque_rows(img) -> list[int]:
    px = img.load()
    return [y for y in range(0, H, 4)
            if any(px[x, y][3] > 0 for x in range(0, W, 4))]


def test_縦型と同じ大きさの透過画像で返る():
    img = render_short_caption("本気なんですよ。")
    assert img.size == SHORT_SIZE
    assert img.mode == "RGBA"


def test_字幕は下帯の中だけに描く():
    # 上帯には見出しが、中央には映像がある。踏むと両方読めなくなる
    rows = opaque_rows(render_short_caption("本気なんですよ。"))
    assert rows
    assert min(rows) >= BAND_TOP


def test_映像の領域を踏まない():
    img = render_short_caption("あ" * 24)
    assert img.getpixel((W // 2, int(H * SHORT_TOP) + 100))[3] == 0


def test_空文字なら何も描かない():
    assert opaque_rows(render_short_caption("")) == []


def test_長い字幕は折り返して下帯に収まる():
    rows = opaque_rows(render_short_caption("結構マイナスになることばっか言ってるじゃないですか。"))
    assert min(rows) >= BAND_TOP
    assert max(rows) < H


def test_折り返しても文字を落とさない():
    # `wrap(...)[:2]` で本文を黙って切り落とし、事業内容が「送客してもらう座」で
    # 終わったまま3本投稿してしまった前科がある。字幕でも同じことをしない
    from scripts.cards import caption_lines
    assert "".join(caption_lines("あ" * 60)) == "あ" * 60


def test_収まるところまで文字を小さくする():
    from scripts.cards import caption_lines
    assert len(caption_lines("あ" * 60)) <= 3


def test_短い字幕は1行で出す():
    from scripts.cards import caption_lines
    assert caption_lines("本気なんですよ。") == ["本気なんですよ。"]


def test_映像は16対9のまま置く():
    # 横にトリミングすると元動画の焼き込みテロップが左右で切れて読めなくなる。
    # 実測で「マイナスな発言が多い」が「ナスな発言が多」になっていた
    video_h = H - int(H * SHORT_TOP) - int(H * SHORT_BOTTOM)
    assert abs(W / video_h - 16 / 9) < 0.02
