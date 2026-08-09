#!/usr/bin/env python3
"""切り抜き地点を探すための4信号を扱う純粋関数。

ヒートマップは YouTube Data API では取得できない。動画ページの ytInitialData
（frameworkUpdates 内の macroMarkersListEntity）にしか入っていないため、
ブラウザで取った JSON を parse_heatmap に渡す形にしてある。

**ヒートマップは主軸にできない。** 令和の虎Second の直近30本を実測したところ、
存在するのは7本（23%）だけだった。生成条件は「5万回以上」かつ「3週間以上経過」の
両方らしく、再生数が足りていても日が浅いと出ない（12日前・6.2万回で無し）。
切り抜きは新着を早く出すのが勝ち筋なので、一番使いたい場面で使えない。

そこで常に使える2つを主軸に据える。

  1. 音量スパイク  虎が激怒すれば必ず音量に出る。新着でも即座に取れる
  2. 字幕の語彙    構造が定型なので、詰め・金額・判定の語彙で山を拾える
  3. コメント言及  新着でもある程度つく
  4. ヒートマップ  あれば加点。過去回を掘るときに効く
"""

from __future__ import annotations

import re
import statistics

# 前後が数字やコロンでない mm:ss / h:mm:ss だけを拾う
TS_RE = re.compile(r"(?<![\d:])(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?![\d:])")
SAMPLE_LIMIT = 3


def parse_heatmap(data: dict) -> list[dict]:
    """ytInitialData から Most replayed を [{"start","end","score"}, ...] にする。"""
    out: list[dict] = []

    def walk(o):
        if isinstance(o, list):
            for x in o:
                walk(x)
            return
        if not isinstance(o, dict):
            return
        ml = (o.get("macroMarkersListEntity") or {}).get("markersList")
        if ml and ml.get("markerType") == "MARKER_TYPE_HEATMAP":
            for m in ml.get("markers") or []:
                start = int(m.get("startMillis", 0)) / 1000
                dur = int(m.get("durationMillis", 0)) / 1000
                out.append({
                    "start": start,
                    "end": start + dur,
                    "score": float(m.get("intensityScoreNormalized", 0.0)),
                })
        for v in o.values():
            walk(v)

    walk(data)
    return out


def extract_timestamps(text: str) -> list[int]:
    """コメント本文の mm:ss / h:mm:ss を秒に変換して返す。"""
    return [(int(h) if h else 0) * 3600 + int(m) * 60 + int(s)
            for h, m, s in TS_RE.findall(text or "")]


def aggregate_marks(comments: list[str]) -> list[dict]:
    """秒ごとに言及を集計する。言及数の多い順、同数なら秒の小さい順。"""
    bucket: dict[int, list[str]] = {}
    for c in comments:
        for sec in extract_timestamps(c):
            bucket.setdefault(sec, []).append(c)
    marks = [{"seconds": sec, "count": len(v), "samples": v[:SAMPLE_LIMIT]}
             for sec, v in bucket.items()]
    marks.sort(key=lambda m: (-m["count"], m["seconds"]))
    return marks


# ── 音量 ────────────────────────────────────────────────────────────

ASTATS_T_RE = re.compile(r"pts_time:([\d.]+)")
ASTATS_DB_RE = re.compile(r"lavfi\.astats\.Overall\.RMS_level=(-?[\d.]+|-inf)")


def parse_astats(text: str, bin_sec: float = 1.0) -> list[dict]:
    """ffmpeg の astats 出力を、秒ごとの平均dBにまとめる。

    ffmpeg は音声フレームごと（8kHzで毎秒50件ほど）に吐くので、
    そのままでは細かすぎる。無音区間は -inf になるので捨てる。
    """
    bins: dict[float, list[float]] = {}
    cur_t: float | None = None
    for line in text.splitlines():
        m = ASTATS_T_RE.search(line)
        if m:
            cur_t = float(m.group(1))
            continue
        m = ASTATS_DB_RE.search(line)
        if m and cur_t is not None:
            if m.group(1) == "-inf":
                continue
            bins.setdefault((cur_t // bin_sec) * bin_sec, []).append(float(m.group(1)))
    return [{"t": t, "db": statistics.fmean(v)} for t, v in sorted(bins.items())]


def loudness_scores(env: list[dict], baseline_sec: float = 120.0) -> list[dict]:
    """局所的な基準からどれだけ跳ねたかを 0..1 で返す。

    絶対的な音量ではなく**周囲との差**を見る。全体が大きい動画でも、
    静かな動画でも、同じ尺度で「ここで声が張られた」を拾えるようにする。
    """
    if not env:
        return []
    half = max(1, int(baseline_sec / 2))
    out = []
    for i, e in enumerate(env):
        lo, hi = max(0, i - half), min(len(env), i + half + 1)
        base = statistics.median(x["db"] for x in env[lo:hi])
        out.append({"t": e["t"], "db": e["db"], "over": e["db"] - base})

    peak = max((o["over"] for o in out), default=0.0)
    if peak <= 0:
        return [{"t": o["t"], "score": 0.0} for o in out]
    return [{"t": o["t"], "score": max(0.0, o["over"]) / peak} for o in out]


# ── 字幕の語彙 ──────────────────────────────────────────────────────

# 令和の虎は「事業計画を持ち込む→虎が詰める→出資判定」の定型構造を持つ。
# その3局面に出る語を拾えば、ヒートマップが無くても山が取れる。
LEXICON: dict[str, tuple[str, ...]] = {
    "詰め": ("お前", "ふざけ", "話にならない", "甘い", "無理", "やめた方がいい",
             "任せられない", "だめ", "ダメ", "厳しい", "おかしい", "違う",
             "何言って", "舐め", "本気で"),
    "金額": ("万円", "億円", "いくら", "資金", "融資", "出資額", "希望金額",
             "売上", "利益", "原価"),
    "判定": ("出資します", "出資しません", "降ります", "抜けます", "成立",
             "ALL", "オールなし", "全員", "ゼロ", "やりましょう"),
}


def lexical_marks(cues: list[dict]) -> list[dict]:
    """字幕から定型語彙を拾う。[{"seconds","kind","word","line"}, ...]"""
    out = []
    for c in cues:
        line = c.get("line") or ""
        for kind, words in LEXICON.items():
            hit = next((w for w in words if w in line), None)
            if hit:
                out.append({"seconds": int(c.get("t") or 0), "kind": kind,
                            "word": hit, "line": line})
    return out
