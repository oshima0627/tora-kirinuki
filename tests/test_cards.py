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
    w, h = img.size
    assert img.mode == "RGBA"
    assert img.getpixel((w // 2, h // 2))[3] == 0


def test_論点カードの帯は画面上部にある():
    # 令和の虎Secondは画面下部に大きなテロップを常時焼き込んでいる。
    # 下に置くと必ずぶつかって両方読めなくなる（実ビルドで確認）
    img = render_point("原価が見えていないのに値付けはできない")
    w, h = img.size
    assert img.getpixel((w // 2, 10))[3] == 255
    assert img.getpixel((w // 2, h - 10))[3] == 0


def test_論点カードの帯は1行でも元動画の上部オーバーレイを覆う高さがある():
    # 中途半端に覆うと相手の文字の下端だけが残って汚くなる（実ビルドで確認）
    img = render_point("短い一行")
    w, h = img.size
    assert img.getpixel((w // 2, int(h * 0.16)))[3] == 255


def test_論点カードの帯は不透明():
    # 半透明だと下の文字が透けて重なり、両方読めなくなる
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


def test_2行に収まる文はそのまま():
    from scripts.cards import overflowing
    assert overflowing("希望金額 200万円", "短い事業内容", "河合 直人（43）", []) == []


def test_はみ出した本文を名指しで返す():
    """`wrap(...)[:2]` は黙って切り落とす。**切れた文が画面に出るほうが害が大きい。**

    実際に事業内容が「送客してもらう座」で切れたまま焼き込まれた。
    """
    from scripts.cards import overflowing
    long_text = "医師と理学療法士が同行する医療サポート付き海外旅行。" * 3
    got = overflowing("希望金額 100万円", long_text, "河合 直人（43）", [])
    assert len(got) == 1
    assert "事業内容" in got[0]


def test_論点カードのはみ出しも拾う():
    from scripts.cards import overflowing
    got = overflowing("100万円", "短い", "短い", ["あ" * 200, "短い論点"])
    assert len(got) == 1
    assert "論点カード1" in got[0]


def test_判定カードの詳細も3行で切られる():
    """`render_verdict` は detail を `wrap(...)[:3]` で切る。

    実ビルドで「3人で均等に受け取る形を選」で終わっていた。
    """
    from scripts.cards import overflowing
    long_detail = "積み上げは270万円に達して希望額200万円を超えた。" * 6
    got = overflowing("100万円", "短い", "短い", [], verdict_detail=long_detail)
    assert len(got) == 1
    assert "判定カード" in got[0]


def test_判定カードが3行に収まればそのまま():
    from scripts.cards import overflowing
    assert overflowing("100万円", "短い", "短い", [],
                       verdict_detail="希望額ちょうどで成立した") == []
