from scripts.signals import aggregate_marks, extract_timestamps, parse_heatmap

YT = {
    "frameworkUpdates": {"entityBatchUpdate": {"mutations": [
        {"payload": {"macroMarkersListEntity": {"markersList": {
            "markerType": "MARKER_TYPE_HEATMAP",
            "markers": [
                {"startMillis": "0", "durationMillis": "30000",
                 "intensityScoreNormalized": 0.10},
                {"startMillis": "30000", "durationMillis": "30000",
                 "intensityScoreNormalized": 0.95},
            ]}}}},
    ]}}
}


def test_ヒートマップを秒とスコアに変換する():
    assert parse_heatmap(YT) == [
        {"start": 0.0, "end": 30.0, "score": 0.10},
        {"start": 30.0, "end": 60.0, "score": 0.95},
    ]


def test_ヒートマップが無ければ空リスト():
    assert parse_heatmap({}) == []


def test_ヒートマップ以外のマーカーは拾わない():
    other = {"payload": {"macroMarkersListEntity": {"markersList": {
        "markerType": "MARKER_TYPE_CHAPTERS",
        "markers": [{"startMillis": "0", "durationMillis": "10000"}]}}}}
    assert parse_heatmap(other) == []


def test_mmss形式を秒にする():
    assert extract_timestamps("12:34 ここが好き") == [754]


def test_hmmss形式を秒にする():
    assert extract_timestamps("1:02:03 の場面") == [3723]


def test_1コメント内の複数言及を全部拾う():
    assert extract_timestamps("0:30 と 2:00 が神") == [30, 120]


def test_タイムスタンプが無ければ空():
    assert extract_timestamps("面白かった") == []


def test_同じ秒の言及を数える():
    marks = aggregate_marks(["12:34 好き", "12:34 神回", "0:10 冒頭"])
    assert marks[0] == {"seconds": 754, "count": 2,
                        "samples": ["12:34 好き", "12:34 神回"]}


def test_言及数の多い順に並ぶ():
    marks = aggregate_marks(["0:10 a", "12:34 b", "12:34 c"])
    assert [m["seconds"] for m in marks] == [754, 10]


def test_コメントが空なら空リスト():
    assert aggregate_marks([]) == []
