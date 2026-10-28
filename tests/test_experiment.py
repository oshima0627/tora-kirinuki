"""2026-10-29〜11-11 の形式実験（docs/experiments-ledger.md）。

数字ズレ型ショート（8〜20秒）・図解まとめ長尺（6〜9分）・締めの文言（判定は本編で）。
**旧形式（50〜58秒のショート・13〜20分の長尺）は従来どおり通ること。**
"""
import copy

import pytest

from scripts.build_clip import cta_plan
from scripts.build_short import closing_cta
from scripts.cards import render_short_cta
from scripts.recipe import (ENDING_HANTEI, build_description, ending_text_of,
                            long_length_warnings, short_cta_sec,
                            short_cta_text, validate, validate_short)
from tests.test_recipe import base

TITLE = "【数字ズレ#3】田渕社長「利益2000万円」なのに2億円が凍結された"


def kazuzure(n: int = 1, series: int = 3, **short_over) -> dict:
    """数字ズレ型ショート＋実験ブロックのレシピ。奇数 n は問い・長尺は matome。"""
    even = n % 2 == 0
    r = base()
    r["cta_question"] = "あなたが虎なら出資する？しない？"
    r["format"] = "standard" if even else "matome"
    if not even:
        r["clip"] = {"start": 1000.0, "end": 1000.0 + 450.0}
    r["short"] = {"start": 2300.0, "end": 2313.0, "format": "kazuzure",
                  "hook": "利益2000万円なのに2億円が凍結", "title": TITLE}
    r["short"].update(short_over)
    r["experiment"] = {
        "id": "2026-10-29-format-test", "n": n, "series_no": series,
        "variant": {"short": "kazuzure", "ending": "hantei" if even else "question",
                    "long": "standard" if even else "matome"}}
    return r


# ---- 旧形式は変わらない ---------------------------------------------------

def test_旧ショートは15秒だと落ちる():
    r = base()
    r["short"] = {"start": 2300.0, "end": 2315.0, "hook": "フック"}
    with pytest.raises(ValueError, match="45"):
        validate_short(r)


def test_旧ショートは50秒台で通り警告も無い():
    r = base()
    r["short"] = {"start": 2300.0, "end": 2355.0, "hook": "フック"}
    assert validate_short(r) == []


def test_旧長尺は尺を検証しない():
    r = base()
    r["clip"] = {"start": 0.0, "end": 120.0}
    validate(r)
    assert long_length_warnings(r) == []


def test_formatもexperimentも無ければ従来の締め():
    r = base()
    r["short"] = {"start": 2300.0, "end": 2355.0, "hook": "フック"}
    assert ending_text_of(r) is None
    assert closing_cta(r, 55.0)["sec"] == 4.0
    assert short_cta_sec(r) == 4.0


def test_ショートのタイトルにも公式は禁止():
    r = base()
    r["short"] = {"start": 2300.0, "end": 2355.0, "hook": "フック",
                  "title": "【公式】令和の虎"}
    with pytest.raises(ValueError, match="公式"):
        validate_short(r)


# ---- A/B 数字ズレ型ショート ------------------------------------------------

def test_数字ズレ型は10から15秒で通る():
    assert validate_short(kazuzure()) == []


def test_数字ズレ型は20秒まで():
    validate_short(kazuzure(end=2320.0))          # ちょうど20秒
    with pytest.raises(ValueError, match="kazuzure"):
        validate_short(kazuzure(end=2320.1))


def test_数字ズレ型は8秒未満は落ちる():
    with pytest.raises(ValueError, match="kazuzure"):
        validate_short(kazuzure(end=2307.9))


def test_数字ズレ型は窓外なら警告():
    w = validate_short(kazuzure(end=2318.0))      # 18秒
    assert any("10〜15秒" in x for x in w)


def test_数字ズレ型はfallbackで50秒台に戻せる():
    r = kazuzure()
    r["short"] = {"start": 2300.0, "end": 2355.0, "hook": "フック", "title": "通常のタイトル"}
    r["experiment"]["variant"]["short"] = "fallback"
    validate(r)
    assert validate_short(r) == []


def test_fallbackなのにkazuzure形式なら落ちる():
    r = kazuzure()
    r["experiment"]["variant"]["short"] = "fallback"
    with pytest.raises(ValueError, match="fallback"):
        validate(r)


def test_タイトルの型():
    with pytest.raises(ValueError, match="【数字ズレ#N】"):
        validate_short(kazuzure(title="田渕社長の数字ズレ"))
    with pytest.raises(ValueError, match="本文"):
        validate_short(kazuzure(title="【数字ズレ#3】"))


def test_タイトルに秒数を入れない():
    with pytest.raises(ValueError, match="秒数"):
        validate_short(kazuzure(title="【数字ズレ#3】12秒で数字が合わない"))
    with pytest.raises(ValueError, match="秒数"):
        validate_short(kazuzure(title="【数字ズレ#3】12 秒で崩れた"))


def test_シリーズ番号とタイトルが合わなければ落ちる():
    with pytest.raises(ValueError, match="series_no"):
        validate_short(kazuzure(series=4))


def test_数字ズレ型のタイトルにも禁止語():
    with pytest.raises(ValueError, match="公認"):
        validate_short(kazuzure(title="【数字ズレ#3】公認の数字"))


# ---- D 締めの文言 ----------------------------------------------------------

def test_偶数nは判定は本編で():
    r = kazuzure(n=2)
    assert ending_text_of(r) == ENDING_HANTEI
    c = closing_cta(r, 13.0)
    assert c["text"] == "判定は本編で"
    assert "コメント" not in c["text"]         # 問いではないので「理由もコメントで」を足さない
    validate(r)


def test_奇数nは従来の問い():
    r = kazuzure(n=1)
    assert ending_text_of(r) is None
    assert "コメント" in closing_cta(r, 13.0)["text"]
    validate(r)


def test_どちらの変種でも概要欄1行目は問い():
    for n in (1, 2):
        first = build_description(kazuzure(n=n)).split("\n")[0]
        assert "？" in first and "コメント" in first and ENDING_HANTEI not in first


def test_数字ズレ型の締めの帯は3秒で結末を隠さない():
    r = kazuzure(n=2)
    c = closing_cta(r, 12.0)
    assert (c["at"], c["sec"]) == (9.0, 3.0)
    assert closing_cta(r, 6.0) is None          # 帯が区間の半分を超えるなら出さない


def test_cta_secは上書きできる():
    assert short_cta_sec(kazuzure(cta_sec=2.0)) == 2.0
    with pytest.raises(ValueError, match="cta_sec"):
        short_cta_sec(kazuzure(cta_sec=9.0))


def test_ending_textに禁止語():
    r = kazuzure(n=2, ending_text="公式の判定は本編で")
    with pytest.raises(ValueError, match="公式"):
        validate(r)


def test_判定は本編での帯が描ける():
    img = render_short_cta(short_cta_text(kazuzure(n=2)))
    assert img.getbbox() is not None


def test_ending_textは問いの無い回でも使える():
    r = base()
    r["short"] = {"start": 2300.0, "end": 2355.0, "hook": "フック", "ending_text": "続きは本編で"}
    assert closing_cta(r, 55.0)["text"] == "続きは本編で"


# ---- C 図解まとめ長尺 -------------------------------------------------------

def test_matomeは6から9分で通る():
    validate(kazuzure(n=1))
    for sec in (360.0, 540.0):
        r = kazuzure(n=1)
        r["clip"] = {"start": 100.0, "end": 100.0 + sec}
        validate(r)


def test_matomeは範囲外で落ちる():
    for sec in (359.0, 541.0, 1184.0):
        r = kazuzure(n=1)
        r["clip"] = {"start": 100.0, "end": 100.0 + sec}
        with pytest.raises(ValueError, match="matome"):
            validate(r)


def test_matomeの長尺でも問いかけは冒頭と終盤に出る():
    plan = cta_plan(kazuzure(n=1), 450.0)
    assert len(plan) == 2 and plan[0][1] < 30.0


def test_偶数nの長尺は従来の13から20分():
    r = kazuzure(n=2)
    r["clip"] = {"start": 0.0, "end": 1184.0}
    validate(r)
    assert long_length_warnings(r) == []
    r["clip"] = {"start": 0.0, "end": 450.0}
    validate(r)                                  # 落とさない
    assert long_length_warnings(r)               # 警告だけ


def test_不明なformatは落ちる():
    r = base()
    r["format"] = "digest"
    with pytest.raises(ValueError, match="format"):
        validate(r)


# ---- experiment ブロック ----------------------------------------------------

def test_偶数と奇数の組み合わせが逆なら落ちる():
    r = kazuzure(n=1)
    r["experiment"]["variant"]["ending"] = "hantei"
    with pytest.raises(ValueError, match="n=1"):
        validate(r)
    r = kazuzure(n=2)
    r["experiment"]["variant"]["long"] = "matome"
    r["format"] = "matome"
    r["clip"] = {"start": 100.0, "end": 550.0}
    with pytest.raises(ValueError, match="n=2"):
        validate(r)


def test_nは開始日からの日数と合わせる():
    r = kazuzure(n=1)
    r["experiment"]["date"] = "2026-10-30"
    validate(r)
    r["experiment"]["date"] = "2026-10-31"
    with pytest.raises(ValueError, match="date"):
        validate(r)


def test_同じ回から2本のショートはプランEなので落ちる():
    r = kazuzure(n=1)
    r["shorts"] = [copy.deepcopy(r["short"]), copy.deepcopy(r["short"])]
    with pytest.raises(ValueError, match="プラン E"):
        validate(r)


def test_experimentでctaを切れない():
    r = kazuzure(n=1)
    r["cta"] = False
    with pytest.raises(ValueError, match="cta"):
        validate(r)


def test_奇数nにending_textは入れない():
    r = kazuzure(n=1, ending_text="判定は本編で")
    with pytest.raises(ValueError, match="ending_text"):
        validate(r)


def test_実験の必須項目():
    r = kazuzure(n=1)
    del r["experiment"]["series_no"]
    with pytest.raises(ValueError, match="series_no"):
        validate(r)
    r = kazuzure(n=1)
    r["experiment"]["n"] = -1
    with pytest.raises(ValueError, match="experiment.n"):
        validate(r)
