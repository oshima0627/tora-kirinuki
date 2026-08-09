from scripts.fetch_source import pick_ja_vtt


def test_手動字幕を自動生成より優先する():
    info = {
        "subtitles": {"ja": [{"ext": "vtt", "url": "manual-url"}]},
        "automatic_captions": {"ja": [{"ext": "vtt", "url": "auto-url"}]},
    }
    assert pick_ja_vtt(info) == ("manual-url", "manual", "ja")


def test_手動が無ければ自動生成にフォールバックする():
    info = {"automatic_captions": {"ja": [{"ext": "vtt", "url": "auto-url"}]}}
    assert pick_ja_vtt(info) == ("auto-url", "auto", "ja")


def test_ja_origも見る():
    info = {"automatic_captions": {"ja-orig": [{"ext": "vtt", "url": "u"}]}}
    assert pick_ja_vtt(info) == ("u", "auto", "ja-orig")


def test_vtt以外は選ばない():
    info = {"subtitles": {"ja": [{"ext": "srv3", "url": "x"}]}}
    assert pick_ja_vtt(info) == (None, None, None)


def test_日本語字幕が無ければNoneを返す():
    assert pick_ja_vtt({"subtitles": {"en": [{"ext": "vtt", "url": "x"}]}}) == (None, None, None)
