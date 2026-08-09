from scripts.moments import find_candidates, score_grid, snap_to_cues

CUES = [{"t": 0.0, "line": "冒頭"}, {"t": 28.0, "line": "本題"},
        {"t": 58.0, "line": "詰め"}, {"t": 95.0, "line": "判定"}]


def base_signals() -> dict:
    return {"loudness": [], "lexical": [], "comment_marks": [], "heatmap": []}


def test_信号が空ならスコアも空():
    assert score_grid(base_signals(), duration=10) == {}


def test_音量だけでもスコアがつく():
    s = base_signals()
    s["loudness"] = [{"t": 5.0, "score": 1.0}]
    assert score_grid(s, duration=10)[5] > 0


def test_ヒートマップが無くても候補が出る():
    # ヒートマップは30本中7本にしか存在しないので、これが出ないと大半の動画で詰む
    s = base_signals()
    s["loudness"] = [{"t": float(t), "score": 1.0 if t == 60 else 0.1}
                     for t in range(120)]
    got = find_candidates(s, CUES, duration=120, count=1, length=40.0)
    assert len(got) == 1


def test_音量と詰め語彙が重なると単純加算より高くなる():
    loud = [{"t": 50.0, "score": 1.0}]
    only_loud = score_grid({**base_signals(), "loudness": loud}, duration=60)[50]
    only_lex = score_grid(
        {**base_signals(),
         "lexical": [{"seconds": 50, "kind": "詰め", "word": "お前", "line": ""}]},
        duration=60)[50]
    both = score_grid(
        {**base_signals(), "loudness": loud,
         "lexical": [{"seconds": 50, "kind": "詰め", "word": "お前", "line": ""}]},
        duration=60)[50]
    assert both > only_loud + only_lex


def test_金額語彙は詰めより軽い():
    def at(kind):
        return score_grid(
            {**base_signals(),
             "lexical": [{"seconds": 10, "kind": kind, "word": "x", "line": ""}]},
            duration=20)[10]
    assert at("金額") < at("詰め")


def test_コメント言及は件数が少なくても強く効く():
    s = {**base_signals(),
         "comment_marks": [{"seconds": 10, "count": 1, "samples": ["x"]}]}
    assert score_grid(s, duration=20)[10] >= 0.3


def test_区間の端を字幕の切れ目に寄せる():
    assert snap_to_cues(30.0, 60.0, CUES) == (28.0, 58.0)


def test_字幕が無ければ元の区間を返す():
    assert snap_to_cues(30.0, 60.0, []) == (30.0, 60.0)


def test_候補は重ならない():
    s = base_signals()
    s["loudness"] = [{"t": float(t), "score": 1.0 if t in (50, 60) else 0.0}
                     for t in range(300)]
    got = find_candidates(s, [], duration=300, count=2, length=60.0)
    assert len(got) < 2 or got[0]["end"] <= got[1]["start"] or got[1]["end"] <= got[0]["start"]


def test_候補はスコアの高い順に返る():
    s = base_signals()
    s["loudness"] = [{"t": float(t), "score": 0.0} for t in range(600)]
    s["loudness"][100]["score"] = 0.5
    s["loudness"][400]["score"] = 1.0
    got = find_candidates(s, [], duration=600, count=2, length=60.0)
    assert got[0]["score"] >= got[1]["score"]
    assert got[0]["start"] <= 400 <= got[0]["end"]
