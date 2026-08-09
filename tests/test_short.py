import pytest

from scripts.cards import render_short_frame
from scripts.recipe import validate_short
from tests.test_recipe import base

HEAD = [[{"t": "粗利は1棟", "c": "w"}, {"t": "20万円", "c": "r"}],
        [{"t": "それでも", "c": "w"}, {"t": "満額200万円", "c": "r"}]]
QUOTE = [[{"t": "倍にして返してもらおう", "c": "r"}]]


def with_short(**over) -> dict:
    r = base()
    r["short"] = {"start": 2300.0, "end": 2350.0,
                  "hook": "粗利は1棟20万円。それでも満額200万円",
                  "head": HEAD, "quote": QUOTE}
    r["short"].update(over)
    return r


def test_正しいショートは通る():
    validate_short(with_short())


def test_shortが無ければ落ちる():
    with pytest.raises(ValueError, match="short"):
        validate_short(base())


def test_開始が終了以上なら落ちる():
    with pytest.raises(ValueError, match="short.clip"):
        validate_short(with_short(start=2350.0, end=2300.0))


def test_フックが空なら落ちる():
    # 縦型は冒頭2秒で離脱が決まる。フック無しで出す意味がない
    with pytest.raises(ValueError, match="hook"):
        validate_short(with_short(hook=""))


def test_3分を超えたら落ちる():
    with pytest.raises(ValueError, match="180"):
        validate_short(with_short(start=0.0, end=181.0))


def test_縦型フレームは1080x1920で返る():
    assert render_short_frame(HEAD, QUOTE).size == (1080, 1920)


def test_中央に映像用の穴が空いている():
    img = render_short_frame(HEAD, QUOTE)
    assert img.mode == "RGBA"
    assert img.getpixel((540, 960))[3] == 0


def test_上下は黒帯で不透明():
    # 元動画の告知と字幕をここで覆い隠す
    img = render_short_frame(HEAD, QUOTE)
    for y in (60, 1860):
        px = img.getpixel((30, y))
        assert px[3] == 255
        assert px[:3] == (0, 0, 0)


def test_1行の中で色を変えられる():
    a = render_short_frame([[{"t": "テスト", "c": "w"}]])
    b = render_short_frame([[{"t": "テスト", "c": "r"}]])
    assert list(a.getdata()) != list(b.getdata())


def test_長い文字列でも落ちない():
    render_short_frame([[{"t": "あ" * 40, "c": "w"}]],
                       [[{"t": "い" * 40, "c": "r"}]])


def test_何も指定しなくても落ちない():
    assert render_short_frame().size == (1080, 1920)
