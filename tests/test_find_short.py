# -*- coding: utf-8 -*-
"""ショート区間の総当たり探索。

**HANDOFF.md に手書きのスニペットとして置かれていたものを実装に移した。**
スニペットは 65〜73秒が直書きで、9/7〜9/12 の6本が全部 69.5〜74.6秒になった
直接の原因だった（docs/2026-09-10-analytics.md）。
"""

from PIL import Image

from scripts.moments import is_letterboxed, short_candidates


def cues(*pairs) -> list[dict]:
    return [{"t": t, "line": line} for t, line in pairs]


BAND = cues(
    (900.0, "前の話が終わりました。"),
    (905.0, "ここから新しい話が始まります。"),   # 文頭。905+55=960 に終端がある
    (930.0, "途中の発言です。"),
    (960.0, "ここで終わります。"),
    (975.0, "さらに続きます。"),
)


def test_文頭で巻き戻し0の開始点だけを返す():
    got = short_candidates(BAND, 890.0, 970.0, 50.0, 58.0)
    assert [c["start"] for c in got] == [905.0]


def test_窓に入る終端の候補を尺つきで返す():
    got = short_candidates(BAND, 890.0, 970.0, 50.0, 58.0)
    assert got[0]["lengths"] == [55.0]          # 960.0 - 905.0


def test_窓の外の終端は返さない():
    # 975.0 まで取ると70秒。50〜58秒の窓の外なので候補に出さない
    got = short_candidates(BAND, 890.0, 970.0, 50.0, 58.0)
    assert 70.0 not in got[0]["lengths"]


def test_窓を変えれば別の終端が出る():
    # **既定を変えられることがこの実装の眼目。** スニペットは65〜73秒が直書きだった
    got = short_candidates(BAND, 890.0, 970.0, 65.0, 73.0)
    assert got[0]["lengths"] == [70.0]          # 975.0 - 905.0


def test_帯の外は見ない():
    assert short_candidates(BAND, 0.0, 100.0, 50.0, 58.0) == []


def test_終端が無い開始点は落とす():
    only = cues((900.0, "前の話が終わりました。"), (905.0, "ここから話が始まります。"))
    assert short_candidates(only, 890.0, 970.0, 50.0, 58.0) == []


def test_発話の途中は候補にしない():
    # 巻き戻しが起きる＝文頭に着地していない。ここから切ると前提が入らない
    mid = cues((900.0, "前の話が終わりました。"),
               (905.0, "ここから新しい話が始まります。"),
               (908.0, "で、その続きです。"),          # 接続詞。文頭ではない
               (960.0, "ここで終わります。"),
               (963.0, "終わりました。"))
    assert [c["start"] for c in short_candidates(mid, 890.0, 970.0, 50.0, 58.0)] == [905.0]


def solid(v: int) -> Image.Image:
    return Image.new("RGB", (64, 64), (v, v, v))


def test_上下が黒い絵はレターボックスと判定する():
    img = solid(200)
    img.paste(Image.new("RGB", (64, 8), (2, 2, 2)), (0, 0))
    img.paste(Image.new("RGB", (64, 8), (2, 2, 2)), (0, 56))
    assert is_letterboxed(img) is True


def test_明るい絵はレターボックスではない():
    assert is_letterboxed(solid(200)) is False


def test_片側だけ黒いのはレターボックスではない():
    # 夜のシーンで上だけ暗いことがある。両側そろって初めて黒帯
    img = solid(200)
    img.paste(Image.new("RGB", (64, 8), (2, 2, 2)), (0, 0))
    assert is_letterboxed(img) is False


def test_全面が暗い絵はレターボックスではない():
    # 暗転のフレーム。黒帯とは別物なので、区間を落とす理由にしない
    assert is_letterboxed(solid(3)) is False
