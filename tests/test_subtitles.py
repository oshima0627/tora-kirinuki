from scripts.subtitles import parse_vtt

VTT = """WEBVTT
Kind: captions
Language: ja

00:00:01.000 --> 00:00:03.000
<c>希望</c>金額は

00:00:03.000 --> 00:00:05.000
希望金額は500万円

00:00:05.000 --> 00:00:07.000
希望金額は500万円

00:00:07.000 --> 00:00:09.000
事業内容を説明します
"""


def test_タグを除去する():
    assert "<c>" not in parse_vtt(VTT)[0][1]


def test_行が伸びたら差し替えるが最初の出現時刻を保つ():
    # 「希望金額は」→「希望金額は500万円」と伸びた場合、確定した本文を残しつつ
    # 時刻は最初に現れた 1.0 のままにする。切り出し位置がずれると意味が変わるため
    assert parse_vtt(VTT)[0] == (1.0, "希望金額は500万円")


def test_ローリング表示の重複を潰して伸びた行に差し替える():
    lines = [line for _, line in parse_vtt(VTT)]
    assert lines == ["希望金額は500万円", "事業内容を説明します"]


def test_ヘッダ行は無視する():
    assert all(l not in ("WEBVTT", "Kind: captions") for _, l in parse_vtt(VTT))


def test_空文字なら空リストを返す():
    assert parse_vtt("") == []
