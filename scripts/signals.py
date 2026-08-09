#!/usr/bin/env python3
"""Most replayed ヒートマップと、コメントのタイムスタンプ言及を扱う純粋関数。

ヒートマップは YouTube Data API では取得できない。動画ページの ytInitialData
（frameworkUpdates 内の macroMarkersListEntity）にしか入っていないため、
ブラウザで取った JSON を parse_heatmap に渡す形にしてある。
"""

from __future__ import annotations

import re

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
