from scripts.signals import lexical_marks, loudness_scores, parse_astats

ASTATS = """frame:0    pts:0       pts_time:0
lavfi.astats.Overall.RMS_level=-inf
frame:1    pts:672     pts_time:0.2
lavfi.astats.Overall.RMS_level=-40.0
frame:2    pts:1632    pts_time:0.6
lavfi.astats.Overall.RMS_level=-30.0
frame:3    pts:2592    pts_time:1.4
lavfi.astats.Overall.RMS_level=-20.0
frame:4    pts:3552    pts_time:2.1
lavfi.astats.Overall.RMS_level=-10.0
"""


def test_astatsを秒ごとの平均dBにまとめる():
    assert parse_astats(ASTATS) == [
        {"t": 0.0, "db": -35.0},     # -40 と -30 の平均
        {"t": 1.0, "db": -20.0},
        {"t": 2.0, "db": -10.0},
    ]


def test_無音のinfは捨てる():
    assert all(e["db"] != float("-inf") for e in parse_astats(ASTATS))


def test_出力が空なら空リスト():
    assert parse_astats("") == []


def test_局所平均より大きい区間ほど高スコアになる():
    env = [{"t": float(i), "db": -30.0} for i in range(60)]
    env[30]["db"] = -10.0                      # ここだけ突出させる
    scores = loudness_scores(env, baseline_sec=60.0)
    peak = next(s for s in scores if s["t"] == 30.0)
    assert peak["score"] == max(s["score"] for s in scores)
    assert peak["score"] > 0.5


def test_平坦な音量ならスコアは低いまま():
    env = [{"t": float(i), "db": -30.0} for i in range(60)]
    assert max(s["score"] for s in loudness_scores(env, baseline_sec=60.0)) == 0.0


def test_詰めの語彙を拾う():
    cues = [{"t": 10.0, "line": "お前には何も任せられない"}]
    marks = lexical_marks(cues)
    assert marks[0]["seconds"] == 10
    assert marks[0]["kind"] == "詰め"


def test_金額の語彙を拾う():
    marks = lexical_marks([{"t": 5.0, "line": "希望金額は500万円です"}])
    assert marks[0]["kind"] == "金額"


def test_判定の語彙を拾う():
    marks = lexical_marks([{"t": 900.0, "line": "私は出資します"}])
    assert marks[0]["kind"] == "判定"


def test_該当しない行は拾わない():
    assert lexical_marks([{"t": 1.0, "line": "こんにちは"}]) == []


def test_同じ行に複数種あればそれぞれ拾う():
    marks = lexical_marks([{"t": 3.0, "line": "500万円は無理です"}])
    assert {m["kind"] for m in marks} == {"金額", "詰め"}
