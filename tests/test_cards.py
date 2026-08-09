from scripts.cards import render_brief, render_point, render_verdict


def test_案件カードは指定サイズで返る():
    img = render_brief({"amount": "希望金額 200万円",
                        "business": "注文住宅の材木仕入れ",
                        "profile": "材木屋の三代目"})
    assert img.size == (1920, 1080)


def test_案件カードはサイズを変えられる():
    assert render_brief({"amount": "200万円"}, size=(1280, 720)).size == (1280, 720)


def test_論点カードは帯以外が透過で返る():
    # 映像に重ねるので、帯以外は抜けている必要がある
    img = render_point("原価が見えていないのに値付けはできない")
    assert img.mode == "RGBA"
    assert img.getpixel((10, 10))[3] == 0


def test_論点カードの帯は不透明():
    # 半透明にすると元動画の氏名テロップが透けて重なり、両方読めなくなる
    img = render_point("原価が見えていないのに値付けはできない")
    w, h = img.size
    band = [img.getpixel((w // 2, y))[3] for y in range(h)]
    assert max(band) == 255


def test_判定カードは指定サイズで返る():
    img = render_verdict({"result": "成立", "detail": "1名から200万円"})
    assert img.size == (1920, 1080)


def test_長い文字列でも例外を出さない():
    render_point("あ" * 200)
    render_brief({"amount": "あ" * 60, "business": "い" * 80, "profile": "う" * 80})
    render_verdict({"result": "え" * 40, "detail": "お" * 120})


def test_空の項目があっても落ちない():
    render_brief({"amount": "200万円", "business": "", "profile": ""})
    render_verdict({"result": "", "detail": ""})
    render_point("")


def test_案件カードは保存できる(tmp_path):
    p = tmp_path / "brief.png"
    render_brief({"amount": "希望金額 200万円"}).save(p)
    assert p.stat().st_size > 0
