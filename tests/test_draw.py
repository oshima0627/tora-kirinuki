"""折り返し位置の自然さ。

幅だけで1文字ずつ折っていた頃は、実測13か所のうち12か所が語の途中で
割れていた（「231万5」／「000円」、「立候補して」／「いる」）。
数値＋単位をひとかたまりにし、句読点・かっこ・助詞・ひらがな→漢字の
変わり目まで戻して切るようにした。
"""
from PIL import Image, ImageDraw

from scripts.draw import pick_font, wrap


def _wrap(text: str, max_w: int) -> list[str]:
    d = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    return wrap(d, text, pick_font(66), max_w)


def test_数値と単位は行をまたがない():
    # 「231万5」／「000円」に割れると、行をまたいだ数字が別の額に読める。
    for text in ["ひとりあたり県民所得231万5000円をふやします",
                 "観光収入1兆747億円を2兆円にふやすとしています"]:
        for line in _wrap(text, 700):
            assert not line.endswith(("231万5", "231万", "1兆747", "1兆", "2兆")), line


def test_句読点の直後で切る():
    lines = _wrap("二つ目は子育て。沖縄県こども未来部の予算を見ます。", 620)
    assert lines[0].endswith("。")


def test_語の途中では切らない():
    lines = _wrap("沖縄県知事選挙に立候補している古謝玄太氏の政策です。", 620)
    assert not lines[0].endswith("してい")
    assert not lines[1].startswith("る")


def test_戻しすぎて極端に短い行を作らない():
    lines = _wrap("沖縄県知事選挙に立候補している候補者の政策をここで詳しく読みます。", 700)
    longest = max(len(x) for x in lines)
    for line in lines[:-1]:
        assert len(line) >= longest * 0.5, (line, lines)


def test_英数字の連なりは割れない():
    for line in _wrap("G7の食料品税率は10%でした", 200):
        assert line not in ("G", "7", "1", "0%")


def test_全体が収まるときは1行のまま():
    assert _wrap("短い見出し", 5000) == ["短い見出し"]
