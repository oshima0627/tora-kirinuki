# -*- coding: utf-8 -*-
"""1本の長尺につきショートを2本作れるようにする（docs/daily-workflow.md の運用）。

ドキュメントには「recipes/<id>.json の shorts に2つ目を書きます」とあったが、
2026-09-07 時点でコード側に shorts の実装が無く、short（単数）しか読んでいなかった。
"""
import pytest

from scripts.recipe import shorts_of, short_dirname


def _short(start=100.0, end=170.0, hook="フック"):
    return {"start": start, "end": end, "hook": hook}


def test_shortsが無ければshortを1本だけ返す():
    r = {"short": _short()}
    assert shorts_of(r) == [_short()]


def test_shortsがあればその並びを返す():
    a, b = _short(100.0, 170.0), _short(300.0, 368.0, "二本目")
    assert shorts_of({"shorts": [a, b]}) == [a, b]


def test_shortsが優先される():
    a = _short(300.0, 368.0, "二本目")
    r = {"short": _short(), "shorts": [a]}
    assert shorts_of(r) == [a]


def test_どちらも無ければ空():
    assert shorts_of({}) == []


def test_出力ディレクトリ名は1本目がshortで2本目がshort2():
    assert short_dirname("2026-09-10-foo", 0) == "2026-09-10-foo-short"
    assert short_dirname("2026-09-10-foo", 1) == "2026-09-10-foo-short2"


def test_validate_shortはindexで対象を選ぶ():
    from scripts.recipe import validate_short
    r = {
        "shorts": [
            _short(100.0, 170.0, "一本目"),
            {"start": 300.0, "end": 310.0, "hook": "短すぎる"},
        ]
    }
    validate_short(r, None, index=0)          # 70秒なので通る（警告は出る）
    with pytest.raises(ValueError, match="45"):
        validate_short(r, None, index=1)      # 10秒なので落ちる


def test_build_captionはindexで対象を選ぶ():
    from scripts.recipe import build_caption
    r = {
        "id": "x", "title": "長尺タイトル",
        "source_video_id": "abc", "source_url": "https://example.com/x",
        "source_title": "元動画",
        "shorts": [
            {"start": 1.0, "end": 70.0, "hook": "一本目のフック"},
            {"start": 100.0, "end": 170.0, "hook": "二本目のフック"},
        ],
    }
    assert build_caption(r, index=0).startswith("一本目のフック")
    assert build_caption(r, index=1).startswith("二本目のフック")
