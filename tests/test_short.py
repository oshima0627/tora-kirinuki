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


def test_推奨より長いショートは警告になる():
    # 落とさない。尺は素材で決まることもある。ただし黙って通すと
    # 132秒のショート（実績0〜2再生）がまた出る
    from scripts.recipe import validate_short
    r = {"short": {"start": 0.0, "end": 130.0, "hook": "h"}}
    warnings = validate_short(r)
    assert any("完走されにくい" in w for w in warnings)


def test_推奨に収まれば警告は出ない():
    from scripts.recipe import validate_short
    assert validate_short({"short": {"start": 0.0, "end": 65.0, "hook": "h"}}) == []


def cue_list(*pairs) -> list[dict]:
    return [{"t": t, "line": line} for t, line in pairs]


def test_区間に字幕が無ければ落ちる():
    # 字幕を焼けない＝意味が伝わらない。それがコメントの原因だった
    cues = cue_list((10.0, "ぜんぜん違う場所の話です。"))
    with pytest.raises(ValueError, match="字幕"):
        validate_short(with_short(start=2300.0, end=2350.0), cues)


def test_字幕があれば通る():
    cues = cue_list((2300.0, "ここから話が始まります。"), (2310.0, "続きです。"))
    validate_short(with_short(start=2300.0, end=2350.0), cues)


def test_巻き戻した結果3分を超えたら落ちる():
    cues = cue_list((0.0, "前の話が終わりました。"), (5.0, "ここから長い話です。"))
    with pytest.raises(ValueError, match="180"):
        validate_short(with_short(start=6.0, end=186.0), cues)


def test_巻き戻したぶんも警告の尺に含める():
    # 65秒のつもりが巻き戻しで76秒になることがある。黙って通さない
    cues = cue_list((0.0, "前の話が終わりました。"), (5.0, "ここから話が始まります。"))
    warnings = validate_short(with_short(start=16.0, end=81.0), cues)
    assert any("完走されにくい" in w for w in warnings)


def test_開始が発話の途中なら警告する():
    cues = cue_list((0.0, "前の話が終わりました。"), (5.0, "ここから話が始まります。"))
    warnings = validate_short(with_short(start=8.0, end=60.0), cues)
    assert any("5.0" in w for w in warnings)
