# -*- coding: utf-8 -*-
"""ショートの ffmpeg フィルタ連鎖。

**論点カードを足すときに入力番号と [v..] の番号がずれると、
ffmpeg は黙って別の画像を重ねる。** 目で見るまで気づけないので、
連鎖の文字列そのものを検証する。
"""

from scripts.build_short import filter_chain

PLAN = [{"start": 0.0, "end": 2.0, "text": "あ"},
        {"start": 2.0, "end": 4.0, "text": "い"}]
POINTS = [{"at": 7.0, "sec": 3.5, "text": "論点1"}]


def test_カードが無ければ従来どおり():
    chain, last, n = filter_chain(PLAN, [])
    assert last == "[v3]"          # 下地 + 字幕2枚
    assert n == 3                  # frame + 字幕2枚
    assert "point" not in chain


def test_字幕の入力番号は2から始まる():
    chain, _, _ = filter_chain(PLAN, [])
    assert "[v1][2:v]overlay" in chain
    assert "[v2][3:v]overlay" in chain


def test_カードは字幕の後ろに積む():
    # 字幕の上に重ねる。**逆にすると字幕がカードに隠れる**
    chain, last, n = filter_chain(PLAN, POINTS)
    assert "[v3][4:v]overlay" in chain
    assert last == "[v4]"
    assert n == 4


def test_カードの表示時間が入る():
    chain, _, _ = filter_chain(PLAN, POINTS)
    assert "enable='between(t,7.000,10.500)'" in chain


def test_カードが2枚でも番号が続く():
    chain, last, n = filter_chain(
        PLAN, [{"at": 7.0, "sec": 3.0, "text": "1"},
               {"at": 20.0, "sec": 3.0, "text": "2"}])
    assert "[v3][4:v]overlay" in chain
    assert "[v4][5:v]overlay" in chain
    assert last == "[v5]"
    assert n == 5


def test_字幕が無くてもカードだけ積める():
    chain, last, n = filter_chain([], POINTS)
    assert "[v1][2:v]overlay" in chain
    assert last == "[v2]"
    assert n == 2
