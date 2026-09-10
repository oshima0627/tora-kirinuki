# -*- coding: utf-8 -*-
"""ショートの概要欄に入れる長尺リンク。

**2026-09-10 に長尺の毎日制作をやめた**（8/20以降の22本は外れ値2本を除くと
20本で91再生＝1本4.6）。長尺が無いショートを上げられるようにする必要がある。

代わりの導線は作らない。**概要欄のリンクは実測で 82,514再生中10再生**
（`SHORTS_CONTENT_LINKS`）で、作り込む価値が無いことが分かっている
（docs/2026-09-10-analytics.md）。回遊は画面の中（論点カード・トレーラー）で作る。
"""

import json

import pytest

from scripts import upload_youtube as U

DESC = "【元動画】タイトル\nhttps://www.youtube.com/watch?v=SRC\n\n本文です。\n"


def ledger(tmp_path, videos: dict):
    p = tmp_path / "published.json"
    p.write_text(json.dumps({"videos": videos}, ensure_ascii=False),
                 encoding="utf-8")
    return p


def test_長尺があれば差し込む(tmp_path, monkeypatch):
    monkeypatch.setattr(U, "PUBLISHED", ledger(tmp_path, {
        "2026-09-01-x": {"url": "https://www.youtube.com/watch?v=LONG"}}))
    out = U.with_long_form_link({"id": "2026-09-01-x-short"}, DESC)
    assert U.FUNNEL_HEAD in out
    assert "https://www.youtube.com/watch?v=LONG" in out


def test_元動画URLの後ろに入る(tmp_path, monkeypatch):
    monkeypatch.setattr(U, "PUBLISHED", ledger(tmp_path, {
        "2026-09-01-x": {"url": "https://www.youtube.com/watch?v=LONG"}}))
    lines = U.with_long_form_link({"id": "2026-09-01-x-short"}, DESC).split("\n")
    assert lines[1] == "https://www.youtube.com/watch?v=SRC"
    assert lines[3] == U.FUNNEL_HEAD


def test_長尺が無ければ落とさずに省く(tmp_path, monkeypatch):
    # **以前はここで die していた。** 長尺を作らなくなったので上がらなくなる
    monkeypatch.setattr(U, "PUBLISHED", ledger(tmp_path, {}))
    out = U.with_long_form_link({"id": "2026-09-01-x-short"}, DESC)
    assert out == DESC
    assert U.FUNNEL_HEAD not in out


def test_元動画のリンクは必ず残る(tmp_path, monkeypatch):
    # MCN の条件。長尺の有無に関わらず落としてはいけない
    monkeypatch.setattr(U, "PUBLISHED", ledger(tmp_path, {}))
    out = U.with_long_form_link({"id": "2026-09-01-x-short"}, DESC)
    assert "https://www.youtube.com/watch?v=SRC" in out


def test_長尺そのものには差し込まない(tmp_path, monkeypatch):
    monkeypatch.setattr(U, "PUBLISHED", ledger(tmp_path, {}))
    assert U.with_long_form_link({"id": "2026-09-01-x"}, DESC) == DESC


def test_二重には入れない(tmp_path, monkeypatch):
    monkeypatch.setattr(U, "PUBLISHED", ledger(tmp_path, {
        "2026-09-01-x": {"url": "https://www.youtube.com/watch?v=LONG"}}))
    once = U.with_long_form_link({"id": "2026-09-01-x-short"}, DESC)
    assert U.with_long_form_link({"id": "2026-09-01-x-short"}, once) == once


def test_2本目のショートでも長尺を見つける(tmp_path, monkeypatch):
    monkeypatch.setattr(U, "PUBLISHED", ledger(tmp_path, {
        "2026-09-01-x": {"url": "https://www.youtube.com/watch?v=LONG"}}))
    out = U.with_long_form_link({"id": "2026-09-01-x-short2"}, DESC)
    assert "https://www.youtube.com/watch?v=LONG" in out
