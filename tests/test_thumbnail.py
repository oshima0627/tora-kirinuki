from PIL import Image

from scripts.thumbnail import _crop_16x9, render_thumbnail

BG = Image.new("RGB", (1920, 1080), (90, 100, 110))

LINES = [
    [{"t": "「挑戦できます?」", "c": "y"}],
    [{"t": "倍", "c": "r", "s": 1.6}, {"t": "にして返してもらおう", "c": "r"}],
]


def test_1280x720で返る():
    assert render_thumbnail(BG, LINES).size == (1280, 720)


def test_行が空でも落ちない():
    assert render_thumbnail(BG, []).size == (1280, 720)
    assert render_thumbnail(BG, [[]]).size == (1280, 720)


def test_バッジ付きでも落ちない():
    render_thumbnail(BG, LINES, badge="関西版 77人目")


def test_長い文字列でも落ちない():
    render_thumbnail(BG, [[{"t": "あ" * 40, "c": "r"}]], badge="う" * 20)


def test_倍率が大きくても落ちない():
    render_thumbnail(BG, [[{"t": "倍", "c": "r", "s": 3.0}, {"t": "返す", "c": "r"}]])


def test_文字が乗ると背景と変わる():
    assert list(render_thumbnail(BG, []).getdata()) != \
        list(render_thumbnail(BG, LINES).getdata())


def test_色を変えると結果も変わる():
    a = render_thumbnail(BG, [[{"t": "テスト", "c": "r"}]])
    b = render_thumbnail(BG, [[{"t": "テスト", "c": "y"}]])
    assert list(a.getdata()) != list(b.getdata())


def test_抑揚をつけると結果が変わる():
    flat = render_thumbnail(BG, [[{"t": "倍", "c": "r"}, {"t": "返す", "c": "r"}]])
    accent = render_thumbnail(BG, [[{"t": "倍", "c": "r", "s": 1.8},
                                    {"t": "返す", "c": "r"}]])
    assert list(flat.getdata()) != list(accent.getdata())


def test_縦横比の違う背景でも指定サイズに収まる():
    tall = Image.new("RGB", (1080, 1920), (30, 30, 30))
    assert render_thumbnail(tall, LINES).size == (1280, 720)


def test_切り出しは16対9を保つ():
    # 上下を落とすだけだと比率が崩れ、リサイズで顔が縦に伸びる
    c = _crop_16x9(BG)
    assert abs(c.width / c.height - 16 / 9) < 0.02
