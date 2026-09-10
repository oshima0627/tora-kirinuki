# -*- coding: utf-8 -*-
"""固定コメントの問い。

**コメントは32日間で合計7件。** 問いかけが画面にも概要欄にも1度も出ていない
（docs/2026-09-10-analytics.md）。判定が割れる回だけ、問いを1つ投げる。

**ピン留めは YouTube Data API v3 に無い**（2026-09-10 に discovery を実測。
commentThreads は insert/list のみ、comments に pin は無い）。投稿までを
自動化し、ピン留めは Studio で手でやる。
"""

import pytest

from scripts.recipe import question_of, validate_question
from tests.test_recipe import base


def test_questionが無ければNone():
    assert question_of(base()) is None


def test_questionを読める():
    r = base(); r["question"] = "あなたが虎なら出資しますか?"
    assert question_of(r) == "あなたが虎なら出資しますか?"


def test_前後の空白は落とす():
    r = base(); r["question"] = "  出資しますか?  "
    assert question_of(r) == "出資しますか?"


def test_空文字はNoneと同じ():
    r = base(); r["question"] = "   "
    assert question_of(r) is None


def test_問いになっていなければ落ちる():
    # 「今日も見てね」のような呼びかけを投げても、コメントは増えない
    with pytest.raises(ValueError, match="問い"):
        validate_question("今日も見てくださいね")


def test_疑問符があれば通る():
    validate_question("あなたが虎なら出資しますか?")
    validate_question("あなたが虎なら出資しますか？")


def test_長すぎたら落ちる():
    with pytest.raises(ValueError, match="長すぎ"):
        validate_question("あ" * 300 + "?")


def test_URLは入れさせない():
    # 自分のコメントにリンクを貼るとスパム判定される
    with pytest.raises(ValueError, match="URL"):
        validate_question("詳しくは https://example.com を見てください?")
