# -*- coding: utf-8 -*-
"""ショートに論点カード（図解）を入れる。

**チャンネル名は「図解でわかる令和の虎」だが、論点カードは build_clip.py に
しか無く、ショートには1枚も入っていなかった。** 図解は286再生の長尺の中に
あり、91,469再生のショートには無い（docs/2026-09-10-analytics.md）。

置き場所は上帯。実測（n=19）で3秒地点の残存は全19本が113%以上あり、
差がつくのは7〜10秒地点（上位88〜98% / 下位74〜76%）。**落ち始めるところに
2つ目の情報を出す。**
"""

import pytest

from scripts.cards import SHORT_SIZE, render_short_point, short_point_lines
from scripts.recipe import points_of, validate_short
from tests.test_short import with_short


def test_縦型と同じ大きさで返る():
    assert render_short_point("本部も店も利益を取る構造").size == SHORT_SIZE


def test_上帯は不透明():
    img = render_short_point("本部も店も利益を取る構造")
    assert img.getpixel((30, 60))[3] == 255


def test_上帯は黒ではなくカードの地色():
    # 黒帯のままだと見出しと区別がつかない。長尺の論点カードと同じ地色にする
    img = render_short_point("本部も店も利益を取る構造")
    assert img.getpixel((300, 60))[:3] != (0, 0, 0)


def test_映像の穴は透過のまま():
    img = render_short_point("本部も店も利益を取る構造")
    assert img.getpixel((540, 960))[3] == 0


def test_下帯は透過のまま():
    # **ここを覆うと字幕が消える。** 字幕はショートの主役なので譲らない
    img = render_short_point("本部も店も利益を取る構造")
    assert img.getpixel((540, 1860))[3] == 0


def test_空文字なら何も描かない():
    img = render_short_point("")
    assert img.getpixel((30, 60))[3] == 0


def test_文字を黙って落とさない():
    # `wrap(...)[:2]` で本文を切り落として3本投稿した前科がある（cards.py）
    text = "加盟金150万円のうち本部と店舗で利益をどう分けるかが決まっていない"
    assert "".join(short_point_lines(text)) == text


def test_長い文字列でも落ちない():
    render_short_point("あ" * 120)


# --- レシピ側 -------------------------------------------------------------

def test_pointsが無ければ空():
    assert points_of(with_short()) == []


def test_pointsを読める():
    r = with_short(points=[{"at": 7.0, "sec": 3.5, "text": "本部と店で利益を分ける"}])
    assert [p["at"] for p in points_of(r)] == [7.0]


def test_区間の外に置いたら落ちる():
    # 55秒のショートに at=90 は入らない
    r = with_short(points=[{"at": 90.0, "sec": 3.5, "text": "はみ出す"}])
    with pytest.raises(ValueError, match="区間"):
        validate_short(r)


def test_終端をはみ出したら落ちる():
    r = with_short(points=[{"at": 53.0, "sec": 5.0, "text": "はみ出す"}])
    with pytest.raises(ValueError, match="区間"):
        validate_short(r)


def test_textが空なら落ちる():
    r = with_short(points=[{"at": 7.0, "sec": 3.5, "text": "  "}])
    with pytest.raises(ValueError, match="text"):
        validate_short(r)


def test_重なったら落ちる():
    r = with_short(points=[{"at": 7.0, "sec": 4.0, "text": "1枚目"},
                           {"at": 9.0, "sec": 4.0, "text": "2枚目"}])
    with pytest.raises(ValueError, match="重なって"):
        validate_short(r)


def test_正しく置けば通る():
    r = with_short(points=[{"at": 7.0, "sec": 3.5, "text": "本部と店で利益を分ける"},
                           {"at": 20.0, "sec": 3.5, "text": "加盟金は150万円"}])
    assert not any("point" in w for w in validate_short(r))


def test_落ち始める前に出ていないと警告する():
    # 差がつくのは7〜10秒。20秒に置いても、落ちたあとになる
    r = with_short(points=[{"at": 20.0, "sec": 3.5, "text": "遅すぎる"}])
    warnings = validate_short(r)
    assert any("7〜10秒" in w for w in warnings)


def test_最終行が1文字にならない():
    # 「両方が取れるほど儲かるの／か」のように1文字だけ残ると読みにくい。
    # 文字を落とすわけにはいかないので、字を小さくして詰める
    lines = short_point_lines("本部も店も利益を取る。両方が取れるほど儲かるのか")
    assert len(lines[-1]) >= 2
    assert "".join(lines) == "本部も店も利益を取る。両方が取れるほど儲かるのか"


def test_詰めきれなくても文字は落とさない():
    text = "あ" * 200
    assert "".join(short_point_lines(text)) == text
