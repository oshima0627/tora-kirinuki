#!/usr/bin/env python3
"""YouTube自動字幕（VTT）のパーサ。

自動字幕は2行ローリング表示のため、同じ文字列が何度も出る。
直前行の前方一致／包含で潰して、確定した行だけを残す。
libecity-library/scripts/fetch-youtube.py の実装を移植した。

自動字幕はASRなので固有名詞と数値が崩れる。令和の虎は金額が命なので、
ここから取った数字をそのままカードに載せてはいけない（→ scripts/recipe.py）。
"""

from __future__ import annotations

import re

TAG_RE = re.compile(r"<[^>]+>")
CUE_RE = re.compile(r"^(\d{2}:\d{2}:\d{2}\.\d{3})\s+-->")
SKIP_PREFIX = ("WEBVTT", "Kind:", "Language:", "NOTE")


def parse_vtt(text: str) -> list[tuple[float, str]]:
    """VTT全文を [(開始秒, 行), ...] に変換する。"""
    cues: list[tuple[float, str]] = []
    cur_t: float | None = None
    for raw in text.splitlines():
        m = CUE_RE.match(raw.strip())
        if m:
            h, mnt, s = m.group(1).split(":")
            cur_t = int(h) * 3600 + int(mnt) * 60 + float(s)
            continue
        line = TAG_RE.sub("", raw).strip()
        if not line or line.startswith(SKIP_PREFIX):
            continue
        cues.append((cur_t or 0.0, line))

    merged: list[tuple[float, str]] = []
    for t, line in cues:
        if merged:
            prev = merged[-1][1]
            if line == prev or line in prev:
                continue
            if prev in line:                      # 前の行が伸びただけ → 差し替え
                merged[-1] = (merged[-1][0], line)
                continue
        merged.append((t, line))
    return merged
