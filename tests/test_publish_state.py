"""published.json の付け替え。

同じレシピIDで上げ直すとき、エントリを残したままだと --schedule が
既存の動画を予約し直すだけで新しいビルドが上がらない。
"""
from scripts.upload_youtube import retire


def _data():
    return {"videos": {
        "a-short": {"youtube_video_id": "OLD1", "url": "u1",
                    "publish_at": "2026-08-26T03:00:00Z"},
        "b-short": {"youtube_video_id": "OLD2", "url": "u2"},
    }}


def test_退役させると予約が外れて新規アップロードに落ちる():
    d = retire(_data(), "a-short")
    assert "a-short" not in d["videos"]
    assert "b-short" in d["videos"]


def test_旧IDは捨てずに残す():
    # 消すと旧動画の行方が分からなくなる。実測で published.json に無い
    # private動画が6本たまっていた
    d = retire(_data(), "a-short")
    assert d["retired"] == [{"recipe_id": "a-short", "youtube_video_id": "OLD1",
                             "url": "u1", "publish_at": "2026-08-26T03:00:00Z"}]


def test_無いIDを退役させても壊れない():
    d = retire(_data(), "無い")
    assert len(d["videos"]) == 2 and "retired" not in d


def test_二度退役させると積み上がる():
    d = retire(retire(_data(), "a-short"), "b-short")
    assert [r["recipe_id"] for r in d["retired"]] == ["a-short", "b-short"]
    assert d["videos"] == {}
