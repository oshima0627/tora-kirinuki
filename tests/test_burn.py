"""ショートに焼く字幕の割り付け。

いままでショートは PNG を1枚焼いて65秒ずっと重ねていた。会話は進むのに
文字は動かないので、聞き取れない部分を字幕で補えず、
**画面の人物が固定の台詞を言っているように見える**（実際は別人の発言）。
"""

from scripts.subtitles import burn_plan, risky_lines


def cues(*pairs) -> list[dict]:
    return [{"t": t, "line": line} for t, line in pairs]


def test_区間内のキューを相対秒で返す():
    c = cues((100.0, "本気なんですよ。"), (103.0, "ほんまに?"))
    plan = burn_plan(c, 100.0, 106.0)
    assert [(p["start"], p["text"]) for p in plan] == [
        (0.0, "本気なんですよ。"), (3.0, "ほんまに?")]


def test_キューは次のキューの直前まで出す():
    c = cues((100.0, "本気なんですよ。"), (103.0, "ほんまに?"))
    assert burn_plan(c, 100.0, 106.0)[0]["end"] == 3.0


def test_最後のキューは区間の終わりまで出す():
    c = cues((100.0, "本気なんですよ。"), (103.0, "ほんまに?"))
    assert burn_plan(c, 100.0, 106.0)[-1]["end"] == 6.0


def test_区間の頭に掛かっているキューは0秒から出す():
    # 巻き戻しが効かず「そのまま」で着地したときに起きる
    c = cues((98.0, "喋っている途中です"), (103.0, "ほんまに?"))
    assert burn_plan(c, 100.0, 106.0)[0]["start"] == 0.0


def test_区間の外のキューは入らない():
    c = cues((50.0, "ずっと前"), (100.0, "本気なんですよ。"), (200.0, "ずっと後"))
    assert [p["text"] for p in burn_plan(c, 100.0, 106.0)] == ["本気なんですよ。"]


def test_音の注記だけのキューは焼かない():
    # 「[笑い]」を字幕として出しても意味は伝わらない
    c = cues((100.0, "本気なんですよ。"), (102.0, "[笑い]"), (104.0, "ほんまに?"))
    assert [p["text"] for p in burn_plan(c, 100.0, 106.0)] == [
        "本気なんですよ。", "ほんまに?"]


def test_長いキューは読める長さに割る():
    # 実測で最長12.0秒・107文字のキューがある。1枚で出しても読めない
    long = "いや、そうだからそれで別に流せるから今日ごめんなさいの流れにして、まあ別に牛タンと今の話に流せるからです"
    plan = burn_plan(cues((100.0, long), (112.0, "次の発言です。")), 100.0, 120.0, max_chars=24)
    assert len(plan) > 2
    assert all(len(p["text"]) <= 24 for p in plan)


def test_割っても元のキューの時間からはみ出さない():
    long = "あ" * 96
    plan = burn_plan(cues((100.0, long), (112.0, "次の発言です。")), 100.0, 120.0, max_chars=24)
    split = [p for p in plan if p["text"].startswith("あ")]
    assert split[0]["start"] == 0.0
    assert split[-1]["end"] == 12.0


def test_割った断片は時間が重ならず隙間も空かない():
    plan = burn_plan(cues((100.0, "あ" * 96), (112.0, "次の発言です。")), 100.0, 120.0,
                     max_chars=24)
    split = [p for p in plan if p["text"].startswith("あ")]
    for a, b in zip(split, split[1:]):
        assert a["end"] == b["start"]


def test_割るときは句読点を優先する():
    c = cues((100.0, "本気なんですよ。本気で来てるんです。"), (110.0, "次の発言です。"))
    texts = [p["text"] for p in burn_plan(c, 100.0, 115.0, max_chars=12)]
    assert "本気なんですよ。" in texts


def test_字幕が無ければ空を返す():
    assert burn_plan([], 100.0, 106.0) == []


def test_数字を含む行を名指しする():
    # ASRは実測で「土橋さん→その悪さん」「焼き鳥3級→焼き鳥産」と崩れる。
    # 令和の虎は金額が命なので、焼く前に必ず人の目に掛ける
    plan = burn_plan(cues((100.0, "開業は約700万円です。"), (103.0, "なるほど")),
                     100.0, 106.0)
    assert [p["text"] for p in risky_lines(plan)] == ["開業は約700万円です。"]


def test_数字が無ければ名指ししない():
    plan = burn_plan(cues((100.0, "本気なんですよ。")), 100.0, 106.0)
    assert risky_lines(plan) == []


def test_パーセントや単位も危ない行として拾う():
    plan = burn_plan(cues((100.0, "FL率が四十%台に振れています。")), 100.0, 106.0)
    assert len(risky_lines(plan)) == 1


def test_音の注記を挟んでも前のキューが途切れない():
    # ASRは長い発話の直後に「[鼻息]」のようなキューを差し込む。そこで
    # 打ち切ると、107文字が0.29秒に詰め込まれ、その後12秒が無字幕になった
    c = cues((100.0, "あ" * 96), (100.3, "[鼻息]"), (112.0, "次の発言です。"))
    split = [p for p in burn_plan(c, 100.0, 120.0, max_chars=24)
             if p["text"].startswith("あ")]
    assert split[-1]["end"] == 12.0


def test_行の途中にある音の注記は消す():
    # 「うわ[笑い]」をそのまま焼いても読み手には意味がない
    c = cues((100.0, "絶対ない。[笑い]"), (103.0, "次"))
    assert burn_plan(c, 100.0, 106.0)[0]["text"] == "絶対ない。"


def test_短すぎる余りは前の断片にくっつける():
    # 25文字を24で割ると「か。」だけの1枚が0.2秒だけ出る
    c = cues((100.0, "結構マイナスになることばっか言ってるじゃないですか。"), (110.0, "次の発言です。"))
    texts = [p["text"] for p in burn_plan(c, 100.0, 115.0, max_chars=24)]
    assert texts[0] == "結構マイナスになることばっか言ってるじゃないですか。"


def test_1文字だけのキューは焼かない():
    # ASRは「ほ」「お」を独立したキューとして吐く。0.5秒だけ1文字が出ても
    # 読めないし、直前の字幕を途中で消してしまう
    c = cues((100.0, "本気なんですよ。"), (101.0, "ほ"), (104.0, "ほんまに?"))
    plan = burn_plan(c, 100.0, 106.0)
    assert [p["text"] for p in plan] == ["本気なんですよ。", "ほんまに?"]
    assert plan[0]["end"] == 4.0        # 落としたぶん前の字幕が伸びる


def test_断片の先頭に小書き仮名や句読点を残さない():
    # 「…思っち」「ゃった。」のように語の途中で割れると読めない
    # 実データで「…思っち」「ゃった。」に割れた行をそのまま使う
    line = ("いや、そうだからそれで別に流せるから今日ごめんなさいの流れにして、ま、"
            "別に牛タと別に今のサンキューの人に流せるからごめんなさいにしよって"
            "してるんじゃないかなって思っちゃった。")
    texts = [p["text"] for p in
             burn_plan(cues((100.0, line), (112.0, "次の発言です。")), 100.0, 120.0, max_chars=24)]
    assert not any(t[0] in "ゃゅょっぁぃぅぇぉー、。" for t in texts)


def test_一瞬しか出ない字幕は次と繋げる():
    # ASRは「FC」「版も出て…」のように語を割って別キューにする。実測で0.28秒。
    # 読めないうえに点滅するので、繋げて1枚にする
    c = cues((100.0, "はじめの発言です。"), (103.0, "FC"), (103.3, "版も出ています。"),
             (107.0, "おわりの発言です。"))
    plan = burn_plan(c, 100.0, 110.0)
    merged = [p for p in plan if "版も出ています。" in p["text"]]
    assert merged[0]["text"] == "FC版も出ています。"
    assert merged[0]["start"] == 3.0        # 音に合わせて短いほうの頭から出す


def test_最後の字幕が一瞬なら前と繋げる():
    c = cues((100.0, "はじめの発言です。"), (109.8, "です"))
    assert [p["text"] for p in burn_plan(c, 100.0, 110.0)] == ["はじめの発言です。です"]


def test_長い無音のあいだ字幕を出しっぱなしにしない():
    # VTRや音楽で字幕が途切れる区間がある。直前の発言をそこまで引き延ばすと、
    # 画面の言葉と音が何十秒もずれる
    c = cues((100.0, "本気なんですよ。"), (160.0, "ずっとあとの発言です。"))
    assert burn_plan(c, 100.0, 170.0)[0]["end"] <= 8.0
