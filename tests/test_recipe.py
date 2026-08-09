import pytest

from scripts.recipe import build_description, validate


def base() -> dict:
    return {
        "id": "2026-08-10-example",
        "source_video_id": "TuYYB2N0JGE",
        "source_url": "https://www.youtube.com/watch?v=TuYYB2N0JGE",
        "source_title": "【FULL】｢お前には何も任せられない｣家づくりを語る材木屋に虎が激怒",
        "clip": {"start": 2210.0, "end": 2623.0},
        "cards": {
            "brief": {"amount": "希望金額 200万円",
                      "business": "注文住宅の材木仕入れ",
                      "profile": "材木屋の三代目"},
            "points": [{"at": 2300.0, "text": "原価が見えていないのに値付けはできない"}],
            "verdict": {"result": "成立", "detail": "1名から200万円"},
        },
        "title": "動画タイトル",
        "description": "本文",
        "tags": ["令和の虎", "切り抜き"],
        "expected_channel_id": "UCVrCOqLMVJhdciCFUSg0TOw",
        "privacy_status": "private",
    }


def test_正しいレシピは通る():
    validate(base())


def test_expected_channel_idが無ければ落ちる():
    r = base()
    del r["expected_channel_id"]
    with pytest.raises(ValueError, match="expected_channel_id"):
        validate(r)


def test_金額が空ならビルドさせない():
    # 字幕はASRで金額が崩れる。裏取りしていない数字を公開させないための砦
    r = base()
    r["cards"]["brief"]["amount"] = ""
    with pytest.raises(ValueError, match="amount"):
        validate(r)


def test_cardsごと無くても落ちる():
    r = base()
    del r["cards"]
    with pytest.raises(ValueError, match="amount"):
        validate(r)


def test_開始が終了以上なら落ちる():
    r = base()
    r["clip"] = {"start": 500.0, "end": 100.0}
    with pytest.raises(ValueError, match="clip"):
        validate(r)


def test_元動画URLが無ければ落ちる():
    r = base()
    r["source_url"] = ""
    with pytest.raises(ValueError, match="source_url"):
        validate(r)


def test_概要欄の冒頭に元動画のタイトルとURLが入る():
    d = build_description(base())
    head = d.splitlines()[:2]
    assert head[0].startswith("【元動画】")
    assert head[1] == "https://www.youtube.com/watch?v=TuYYB2N0JGE"


def test_概要欄に本文が含まれる():
    assert "本文" in build_description(base())


def test_概要欄に申請済みである旨が入る():
    assert "ガジェット通信" in build_description(base())


def test_概要欄で公認や許諾を主張しない():
    # 権利者は「あくまでご本人は黙認」という扱いで、公式・公認表記を禁じている
    d = build_description(base())
    assert "公認" not in d
    assert "許諾を得て" not in d
    assert "公式チャンネルではありません" in d


def test_タイトルに公認や公式が入っていたら落ちる():
    for word in ("公式", "公認", "マネーの虎"):
        r = base()
        r["title"] = f"【{word}】切り抜き"
        with pytest.raises(ValueError, match=word):
            validate(r)


def test_タグはハッシュタグとして末尾に付く():
    assert build_description(base()).rstrip().endswith("#令和の虎 #切り抜き")


def test_タグが無くても壊れない():
    r = base()
    r["tags"] = []
    assert "【元動画】" in build_description(r)
