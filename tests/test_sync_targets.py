# -*- coding: utf-8 -*-
"""sync_metadata が同期する対象。

**`recipe.get("short")` を直接読んでいたので、`shorts`（配列）で2本目以降を
書いたレシピはショートが1本も同期されなかった**（2026-09-10 に発見）。
ショート2本目は 2026-09-07 に実装して以降まだ1本も上げていない経路だった。
"""

from scripts.sync_metadata import targets

BASE = {"id": "2026-09-01-x", "title": "長尺のタイトル", "tags": ["令和の虎"]}


def test_長尺だけなら1件():
    assert [k for k, _, _ in targets(dict(BASE))] == ["2026-09-01-x"]


def test_shortが単数なら2件():
    r = dict(BASE, short={"start": 0.0, "end": 55.0, "hook": "h", "title": "短1"})
    assert [k for k, _, _ in targets(r)] == ["2026-09-01-x", "2026-09-01-x-short"]


def test_shortsが配列なら本数ぶん返す():
    r = dict(BASE, shorts=[{"start": 0.0, "end": 55.0, "hook": "h1", "title": "短1"},
                           {"start": 100.0, "end": 155.0, "hook": "h2", "title": "短2"}])
    assert [k for k, _, _ in targets(r)] == [
        "2026-09-01-x", "2026-09-01-x-short", "2026-09-01-x-short2"]


def test_2本目のタイトルは2本目のものを使う():
    r = dict(BASE, shorts=[{"start": 0.0, "end": 55.0, "hook": "h1", "title": "短1"},
                           {"start": 100.0, "end": 155.0, "hook": "h2", "title": "短2"}])
    assert [t for _, t, _ in targets(r)] == ["長尺のタイトル", "短1", "短2"]


def test_titleが無ければhookを使う():
    r = dict(BASE, shorts=[{"start": 0.0, "end": 55.0, "hook": "フックの文"}])
    assert [t for _, t, _ in targets(r)][1] == "フックの文"


def test_ショートにはShortsタグが付く():
    r = dict(BASE, shorts=[{"start": 0.0, "end": 55.0, "hook": "h"}])
    assert targets(r)[1][2] == ["令和の虎", "Shorts"]
