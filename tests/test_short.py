import pytest

from scripts.cards import render_short_frame
from scripts.recipe import validate_short
from tests.test_recipe import base


def with_short(**over) -> dict:
    r = base()
    r["short"] = {"start": 2300.0, "end": 2350.0,
                  "hook": "原価が見えていないのに値付けはできない",
                  "footer": "希望金額 200万円"}
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
    # Shorts として扱われる上限
    with pytest.raises(ValueError, match="180"):
        validate_short(with_short(start=0.0, end=181.0))


def test_元動画の尺を超えていても範囲チェックは通る():
    # 元動画との突き合わせは build_short の preflight が行う
    validate_short(with_short(start=100.0, end=160.0))


def test_縦型フレームは1080x1920で返る():
    img = render_short_frame("フック", "フッター")
    assert img.size == (1080, 1920)


def test_縦型フレームは中央に映像用の穴が空いている():
    # 映像を overlay する領域は透過にしておく
    img = render_short_frame("フック", "フッター")
    assert img.mode == "RGBA"
    assert img.getpixel((540, 420 + 540))[3] == 0


def test_縦型フレームの上下は不透明():
    img = render_short_frame("フック", "フッター")
    assert img.getpixel((540, 100))[3] == 255
    assert img.getpixel((540, 1800))[3] == 255


def test_長い文字列でも落ちない():
    render_short_frame("あ" * 120, "い" * 120)


def test_フッターが空でも落ちない():
    render_short_frame("フック", "")
