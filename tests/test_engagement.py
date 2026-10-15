# -*- coding: utf-8 -*-
"""問いかけテロップと概要欄1行目（docs/engagement.md、2026-10-15）。"""

import pytest

from scripts import upload_youtube as U
from scripts.build_clip import CARD_SEC, CTA_SEC, cta_plan
from scripts.build_short import SHORT_CTA_SEC, closing_cta
from scripts.recipe import (CTA_END_DEFAULT, build_description, comment_prompt,
                            cta_question, cta_start_text, short_cta_text,
                            validate)
from tests.test_recipe import base


def test_旧レシピでも既定の問いが出る():
    assert cta_question(base()) == "あなたが虎なら出資する？しない？"


def test_支援型の回は支援を問う():
    r = base(); r["cards"]["brief"]["amount"] = "社長FC版（希望額なし）"
    assert cta_question(r) == "あなたが虎なら支援する？しない？"


def test_cta_questionが最優先():
    r = base(); r["question"] = "Q1？"; r["cta_question"] = "この事業の改善案をコメントで"
    assert cta_question(r) == "この事業の改善案をコメントで"
    assert comment_prompt(r) == "この事業の改善案をコメントで"   # 二重に足さない


def test_冒頭テロップは最初の問いまで():
    assert cta_start_text(base()) == "あなたが虎なら出資する？最後に答えを聞きます"


def test_ショートの締め():
    assert short_cta_text(base()) == "あなたが虎なら出資する？しない？理由もコメントで"


def test_公式や見返りは落とす():
    r = base(); r["cta_question"] = "公式の判断どう思う？"
    with pytest.raises(ValueError, match="公式"):
        validate(r)
    r = base(); r["cta_end"] = "高評価してくれた方にプレゼント"
    with pytest.raises(ValueError):
        validate(r)


def test_長尺は冒頭と終盤に出る():
    r = base()                                  # 413秒、論点は90秒地点
    plan = cta_plan(r, 413.0)
    assert len(plan) == 2
    (t1, s1, e1, top1), (t2, s2, e2, top2) = plan
    assert s1 >= CARD_SEC and e1 - s1 == CTA_SEC and top1 == 0.0
    assert e2 <= 413.0 - CARD_SEC and t2 == CTA_END_DEFAULT


def test_論点カードとぶつかれば避ける():
    r = base()
    r["cards"]["points"] = [{"at": 2210.0 + 5.0, "text": "x"}]
    (_, s1, e1, top1), _ = cta_plan(r, 413.0)
    assert top1 == 0.0 and s1 >= 5.0 + 3.5


def test_避けられなければ下に積む():
    r = base()
    r["cards"]["points"] = [{"at": 2210.0 + t, "text": "x"} for t in range(0, 60, 3)]
    (_, s1, _, top1), _ = cta_plan(r, 413.0)
    assert top1 > 0 and s1 == CARD_SEC + 0.5


def test_ctaを切れば出ない():
    r = base(); r["cta"] = False
    assert cta_plan(r, 413.0) == []
    assert closing_cta(r, 55.0) is None


def test_ショートは最後の数秒():
    c = closing_cta(base(), 55.0)
    assert c["at"] == 55.0 - SHORT_CTA_SEC and c["sec"] == SHORT_CTA_SEC


def test_問いが1行目でも長尺リンクは元動画URLの直後(tmp_path, monkeypatch):
    import json
    p = tmp_path / "published.json"
    p.write_text(json.dumps({"videos": {"2026-08-10-example": {
        "url": "https://www.youtube.com/watch?v=LONG"}}}), encoding="utf-8")
    monkeypatch.setattr(U, "PUBLISHED", p)
    r = base()
    out = U.with_long_form_link(
        {"id": "2026-08-10-example-short", "source_url": r["source_url"]},
        build_description(r)).split("\n")
    assert "コメント" in out[0]
    assert out[2] == r["source_url"]
    assert out[4] == U.FUNNEL_HEAD and out[5].endswith("LONG")
