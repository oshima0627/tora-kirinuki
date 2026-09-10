import pytest

from scripts.cards import render_short_frame
from scripts.recipe import validate_short
from tests.test_recipe import base

HEAD = [[{"t": "粗利は1棟", "c": "w"}, {"t": "20万円", "c": "r"}],
        [{"t": "それでも", "c": "w"}, {"t": "満額200万円", "c": "r"}]]
QUOTE = [[{"t": "倍にして返してもらおう", "c": "r"}]]


def with_short(**over) -> dict:
    r = base()
    # 既定は窓（50〜58秒）の中。下限を割ると validate_short が落ちる
    r["short"] = {"start": 2300.0, "end": 2355.0,
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


def test_45秒未満は落ちる():
    # ここを割ると令和の虎の「問い→答え」が1往復も入らない
    with pytest.raises(ValueError, match="45"):
        validate_short(with_short(start=2300.0, end=2344.9))


def test_巻き戻して窓に入れば尺の警告は出ない():
    # 尺はレシピの値ではなく巻き戻し後の長さ（60-5=55秒）で測る。
    # 巻き戻し自体の警告は別に出るので、尺の警告が無いことだけを見る
    cues = cue_list((0.0, "前の話が終わりました。"), (5.0, "ここから話が始まります。"))
    warnings = validate_short(with_short(start=12.0, end=60.0), cues)
    assert not any("50〜58秒" in w for w in warnings)


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


def test_窓より長いショートは警告になる():
    # 落とさない。尺は素材で決まることもあるし、既存レシピをビルドし直せなくなる。
    # ただし黙って通すと、実視聴秒が増えないまま平均視聴率だけ下がる本がまた出る
    from scripts.recipe import validate_short
    r = {"short": {"start": 0.0, "end": 130.0, "hook": "h"}}
    warnings = validate_short(r)
    assert any("完走されにくい" in w for w in warnings)


def test_58秒を超えたら警告になる():
    # 実測（n=19）: 実視聴秒は尺と無相関で中央値39.5秒。尺×平均視聴率 -0.53
    from scripts.recipe import validate_short
    warnings = validate_short({"short": {"start": 0.0, "end": 59.0, "hook": "h"}})
    assert any("完走されにくい" in w for w in warnings)


def test_これまでの70秒は警告になる():
    # **9/7〜9/12 の6本は全部 69.5〜74.6秒だった。** 同じことが起きたら気づける
    from scripts.recipe import validate_short
    warnings = validate_short({"short": {"start": 0.0, "end": 70.9, "hook": "h"}})
    assert any("50〜58秒" in w for w in warnings)


def test_58秒ちょうどは警告しない():
    from scripts.recipe import validate_short
    assert validate_short({"short": {"start": 0.0, "end": 58.0, "hook": "h"}}) == []


def test_50秒ちょうどは警告しない():
    from scripts.recipe import validate_short
    assert validate_short({"short": {"start": 0.0, "end": 50.0, "hook": "h"}}) == []


def test_窓より短ければ警告になる():
    # 45秒は通すが、狙いは50〜58秒。黙って短いほうに寄らないようにする
    from scripts.recipe import validate_short
    warnings = validate_short({"short": {"start": 0.0, "end": 47.0, "hook": "h"}})
    assert any("短い" in w for w in warnings)


def cue_list(*pairs) -> list[dict]:
    return [{"t": t, "line": line} for t, line in pairs]


def test_区間に字幕が無ければ落ちる():
    # 字幕を焼けない＝意味が伝わらない。それがコメントの原因だった
    cues = cue_list((10.0, "ぜんぜん違う場所の話です。"))
    with pytest.raises(ValueError, match="字幕"):
        validate_short(with_short(start=2300.0, end=2350.0), cues)


def test_字幕があれば通る():
    cues = cue_list((2300.0, "ここから話が始まります。"), (2310.0, "続きです。"))
    validate_short(with_short(start=2300.0, end=2368.0), cues)


def test_巻き戻した結果3分を超えたら落ちる():
    cues = cue_list((0.0, "前の話が終わりました。"), (5.0, "ここから長い話です。"))
    with pytest.raises(ValueError, match="180"):
        validate_short(with_short(start=6.0, end=186.0), cues)


def test_巻き戻したぶんも警告の尺に含める():
    # 55秒のつもりが巻き戻しで66秒になることがある。黙って通さない
    cues = cue_list((0.0, "前の話が終わりました。"), (5.0, "ここから話が始まります。"))
    warnings = validate_short(with_short(start=16.0, end=71.0), cues)
    assert any("完走されにくい" in w for w in warnings)


def test_開始が発話の途中なら警告する():
    cues = cue_list((0.0, "前の話が終わりました。"), (5.0, "ここから話が始まります。"))
    warnings = validate_short(with_short(start=8.0, end=75.0), cues)
    assert any("5.0" in w for w in warnings)
