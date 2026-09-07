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


# 2026-09-07: web_safari が字幕トラックを一切返さなくなった（既存の取得済み動画でも 0 件）。
# 媒体URLの取得には web_safari が要るので、字幕だけ別クライアントで引き直す。
from scripts.fetch_source import resolve_ja_captions


def test_一次抽出に日本語字幕があれば引き直さない():
    info = {"automatic_captions": {"ja": [{"ext": "vtt", "url": "auto-url"}]}}

    def 引き直し():
        raise AssertionError("呼ばれてはいけない")

    assert resolve_ja_captions(info, 引き直し) == ("auto-url", "auto", "ja")


def test_一次抽出に字幕が無ければ別クライアントで引き直す():
    info = {"automatic_captions": {}}
    fallback = {"automatic_captions": {"ja": [{"ext": "vtt", "url": "tv-url"}]}}
    assert resolve_ja_captions(info, lambda: fallback) == ("tv-url", "auto", "ja")


def test_引き直しても無ければNoneを返す():
    assert resolve_ja_captions({}, lambda: {}) == (None, None, None)


def test_引き直しが失敗しても落ちない():
    def 引き直し():
        raise RuntimeError("抽出に失敗")

    assert resolve_ja_captions({}, 引き直し) == (None, None, None)


# 2026-09-07: tv クライアントの automatic_captions では ja が機械翻訳、
# ja-orig が本物のASRだった。ja を先に採ると「150万ドル」「タイガース」のような
# 英語往復訳が入り、金額と固有名詞が全部壊れる。自動生成は ja-orig を優先する。
def test_自動生成ではja_origをjaより優先する():
    info = {"automatic_captions": {
        "ja": [{"ext": "vtt", "url": "翻訳"}],
        "ja-orig": [{"ext": "vtt", "url": "原文"}],
    }}
    assert pick_ja_vtt(info) == ("原文", "auto", "ja-orig")


def test_自動生成にja_origが無ければjaを使う():
    info = {"automatic_captions": {"ja": [{"ext": "vtt", "url": "翻訳しかない"}]}}
    assert pick_ja_vtt(info) == ("翻訳しかない", "auto", "ja")


def test_手動字幕はjaを優先する():
    # 手動字幕は人が書いた日本語なので ja でよい
    info = {"subtitles": {
        "ja": [{"ext": "vtt", "url": "手動ja"}],
        "ja-orig": [{"ext": "vtt", "url": "手動orig"}],
    }}
    assert pick_ja_vtt(info) == ("手動ja", "manual", "ja")


def test_手動jaは自動のja_origより優先される():
    info = {
        "subtitles": {"ja": [{"ext": "vtt", "url": "手動"}]},
        "automatic_captions": {"ja-orig": [{"ext": "vtt", "url": "自動"}]},
    }
    assert pick_ja_vtt(info) == ("手動", "manual", "ja")
