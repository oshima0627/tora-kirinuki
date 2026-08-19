#!/usr/bin/env python3
"""切り抜き地点を探すための信号を集めて signals.json にまとめる。

  python scripts/probe_signals.py <video_id>
  python scripts/probe_signals.py <video_id> --no-comments
  python scripts/probe_signals.py <video_id> --ytdata dump.json

音量と語彙は work/<video_id>/ の素材だけで完結する。コメントは yt-dlp で取る。
ヒートマップは YouTube Data API でも yt-dlp でも取れないが、**動画ページの
HTML を直接引けば入っている。** ブラウザ経由は要らなかった（当初は必要だと
思って --ytdata で渡す作りにしていた）。
そもそも令和の虎Second では30本中7本にしか存在しないので、無くても動く。
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.fetch_source import check_pot_server, source_dir, ydl_opts  # noqa: E402
from scripts.signals import (aggregate_marks, lexical_marks,  # noqa: E402
                             loudness_scores, parse_astats, parse_heatmap)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 8kHz モノラルに落としてから測る。音量の山を見るだけなので情報量は足りる
ASTATS_FILTER = ("astats=metadata=1:reset=8000,"
                 "ametadata=print:key=lavfi.astats.Overall.RMS_level:file=-")


def measure_loudness(source: Path) -> list[dict]:
    out = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-loglevel", "error",
         "-i", str(source), "-vn", "-ac", "1", "-ar", "8000",
         "-af", ASTATS_FILTER, "-f", "null", "-"],
        capture_output=True, text=True, check=True)
    return loudness_scores(parse_astats(out.stdout))


# 素の urllib だと YouTube が簡易版を返すことがあるので UA を名乗る
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")
HEAT_RE = re.compile(r'"markerType":"MARKER_TYPE_HEATMAP","markers":(\[.*?\])', re.S)


def fetch_heatmap(video_id: str) -> list[dict]:
    """Most replayed を動画ページのHTMLから取る。無ければ空。"""
    req = urllib.request.Request(
        f"https://www.youtube.com/watch?v={video_id}",
        headers={"User-Agent": UA, "Accept-Language": "ja,en;q=0.9"})
    try:
        html = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
    except Exception as e:                                   # noqa: BLE001
        print(f"! ヒートマップを取得できませんでした（続行）: {str(e)[:70]}")
        return []
    m = HEAT_RE.search(html)
    if not m:
        return []
    return [{"start": int(x["startMillis"]) / 1000,
             "end": (int(x["startMillis"]) + int(x["durationMillis"])) / 1000,
             "score": float(x["intensityScoreNormalized"])}
            for x in json.loads(m.group(1))]


def fetch_comments(video_id: str, limit: int = 400) -> list[str]:
    from yt_dlp import YoutubeDL

    opts = ydl_opts(skip_download=True, getcomments=True,
                    extractor_args={"youtube": {
                        "lang": ["ja"],
                        "max_comments": [str(limit), "all", "0"]}})
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}",
                                download=False)
    return [c.get("text") or "" for c in (info.get("comments") or [])]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video_id")
    ap.add_argument("--ytdata", type=Path,
                    help="ytInitialData の JSON を手で渡す場合（通常は自動取得）")
    ap.add_argument("--no-comments", action="store_true")
    a = ap.parse_args()

    d = source_dir(a.video_id)
    source, subs = d / "source.mp4", d / "subs.json"
    missing = [str(p) for p in (source, subs) if not p.exists()]
    if missing:
        for m in missing:
            print(f"! {m} が無い")
        raise SystemExit("先に fetch_source.py を実行してください")

    print("音量を測っています（尺の1割ほど時間がかかります）...")
    loud = measure_loudness(source)

    cues = json.loads(subs.read_text(encoding="utf-8"))
    lex = lexical_marks(cues)

    comments: list[str] = []
    if not a.no_comments:
        try:
            comments = fetch_comments(a.video_id)
        except Exception as e:                       # noqa: BLE001
            print(f"! コメントを取得できませんでした（続行）: {str(e)[:80]}")
    marks = aggregate_marks(comments)

    heatmap = (parse_heatmap(json.loads(a.ytdata.read_text(encoding="utf-8")))
               if a.ytdata else fetch_heatmap(a.video_id))
    if not heatmap:
        print("- ヒートマップなし（新しい動画では生成されていない。他の3信号で進む）")

    (d / "signals.json").write_text(json.dumps({
        "video_id": a.video_id,
        "loudness": loud,
        "lexical": lex,
        "comment_marks": marks,
        "heatmap": heatmap,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"✓ {d / 'signals.json'}")
    print(f"  音量 {len(loud)}秒分 / 語彙 {len(lex)}件 / "
          f"コメント言及 {len(marks)}箇所（{len(comments)}件から） / "
          f"ヒートマップ {len(heatmap)}区間")


if __name__ == "__main__":
    main()
