from PIL import Image

from scripts.thumbnail import compose_photos, render_thumbnail

BG = Image.new("RGB", (1920, 1080), (90, 100, 110))
PHOTO = Image.new("RGB", (1280, 720), (90, 100, 110))

TOP = [{"t": "粗利は1棟", "c": "r"}, {"t": "20万円", "c": "y"}]
BUBBLES = [{"t": "挑戦できます?", "c": "r", "side": "l"},
           {"t": "したい", "c": "m", "side": "r"}]
BOTTOM = [{"t": "倍にして返してもらおう", "c": "r"}]


def test_1280x720で返る():
    assert render_thumbnail(PHOTO, TOP, BUBBLES, BOTTOM).size == (1280, 720)


def test_何も指定しなくても落ちない():
    assert render_thumbnail(PHOTO).size == (1280, 720)


def test_上部は黒帯になる():
    # 元動画の募集告知はここで隠れる
    assert render_thumbnail(PHOTO, TOP).getpixel((20, 10)) == (8, 8, 10)


def test_黒帯の下は写真のまま():
    assert render_thumbnail(PHOTO, TOP).getpixel((20, 700)) != (8, 8, 10)


def test_1行の中で色を変えられる():
    a = render_thumbnail(PHOTO, [{"t": "テスト", "c": "r"}])
    b = render_thumbnail(PHOTO, [{"t": "テスト", "c": "y"}])
    assert list(a.getdata()) != list(b.getdata())


def test_吹き出しの向きを変えると結果が変わる():
    a = render_thumbnail(PHOTO, bubbles=[{"t": "あ", "c": "r", "side": "l"}])
    b = render_thumbnail(PHOTO, bubbles=[{"t": "あ", "c": "r", "side": "r"}])
    assert list(a.getdata()) != list(b.getdata())


def test_長い文字列でも落ちない():
    render_thumbnail(PHOTO, [{"t": "あ" * 40, "c": "r"}],
                     [{"t": "い" * 40, "c": "m", "side": "l"}],
                     [{"t": "う" * 40, "c": "r"}])


def test_吹き出しを何枚重ねても落ちない():
    render_thumbnail(PHOTO, bubbles=[{"t": f"発言{i}", "c": "r", "side": "l"}
                                     for i in range(6)])


def test_写真は左右に並ぶ():
    assert compose_photos([BG, BG], [0.3, 0.6]).size == (1280, 720)


def test_写真は黒帯のぶん下げて敷く():
    img = compose_photos([BG, BG], [0.5, 0.5])
    assert img.getpixel((640, 5)) == (8, 8, 10)
    assert img.getpixel((320, 700)) != (8, 8, 10)


def test_元フレームの上部は使わない():
    # 募集告知が写り込まない高さまで落としてから使う
    from scripts.thumbnail import PHOTO_TOP
    assert PHOTO_TOP >= 0.15


def test_下段は縁ではなく下地で読ませる():
    # 三重の縁は画数の多い漢字の内側を塗り潰す。幕を敷いて縁を無くした
    plain = render_thumbnail(PHOTO)
    veiled = render_thumbnail(PHOTO, bottom=BOTTOM)
    assert sum(veiled.getpixel((5, 715))) < sum(plain.getpixel((5, 715)))


def test_幕は下ほど濃い():
    img = render_thumbnail(PHOTO, bottom=BOTTOM)
    assert sum(img.getpixel((5, 715))) < sum(img.getpixel((5, 560)))


def test_下段が無ければ幕は出ない():
    assert render_thumbnail(PHOTO, TOP).getpixel((5, 715)) == (90, 100, 110)


def test_相手の発言はマゼンタではない():
    from scripts.thumbnail import COLORS
    r, g, b = COLORS["m"]
    assert (r, g, b) != (255, 0, 220)
    assert b > r
