from PIL import Image

from scripts.thumbnail import render_thumbnail

BG = Image.new("RGB", (1920, 1080), (90, 100, 110))


def test_1280x720で返る():
    assert render_thumbnail(BG, "粗利は1棟20万円").size == (1280, 720)


def test_2行でも1行でも落ちない():
    render_thumbnail(BG, "粗利は1棟20万円")
    render_thumbnail(BG, "粗利は1棟20万円", "それでも200万円ALL")


def test_バッジ付きでも落ちない():
    render_thumbnail(BG, "粗利は1棟20万円", "それでも200万円ALL", badge="関西版 77人目")


def test_長い文字列でも落ちない():
    render_thumbnail(BG, "あ" * 40, "い" * 40, badge="う" * 20)


def test_空文字でも落ちない():
    render_thumbnail(BG, "", "", badge="")


def test_文字が乗って背景と変わる():
    plain = render_thumbnail(BG, "")
    withtext = render_thumbnail(BG, "粗利は1棟20万円", "それでも200万円ALL")
    assert list(plain.getdata()) != list(withtext.getdata())


def test_縦横比の違う背景でも指定サイズに収まる():
    tall = Image.new("RGB", (1080, 1920), (30, 30, 30))
    assert render_thumbnail(tall, "テスト").size == (1280, 720)


def test_切り出しは16対9を保つ():
    # 上下を落とすだけだと比率が崩れ、リサイズで顔が縦に伸びる
    from scripts.thumbnail import _crop_16x9
    c = _crop_16x9(BG)
    assert abs(c.width / c.height - 16 / 9) < 0.02
