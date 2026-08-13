#!/usr/bin/env python3
"""切り抜き候補を candidates.json に出す。

  python scripts/find_moments.py <video_id>
  python scripts/find_moments.py <video_id> --count 5 --length 420

金額の語彙ヒットも一緒に出す。案件カード（希望金額・事業内容）を書くときの
下書きになる。ただし字幕はASRなので、**金額は必ず映像で裏取りすること**。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.fetch_source import source_dir  # noqa: E402
from scripts.moments import find_candidates  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def hms(sec: float) -> str:
    s = int(sec)
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video_id")
    ap.add_argument("--count", type=int, default=5)
    # 既定を900秒（15分）にしてある。「令和の虎 切り抜き」の検索上位25本は
    # すべて14〜70分で、日次で回している競合も13〜15分と20分だった（2026-08-13 実測）。
    # 当初の420秒はこの市場では明確に短すぎる。総再生時間（YPPの3,000時間）にも効く
    ap.add_argument("--length", type=float, default=900.0,
                    help="1本の目安の尺（秒）。この市場の相場は13〜20分")
    # 詰めどころを狙うときに使う。既定のままだと判定パートが上位に来やすく、
    # 実際に8本すべてが判定パートからの切り出しになっていた
    ap.add_argument("--prefer", choices=("詰め", "判定", "金額"),
                    help="この語彙の重みを上げて候補を選び直す")
    a = ap.parse_args()

    d = source_dir(a.video_id)
    for name in ("signals.json", "subs.json", "meta.json"):
        if not (d / name).exists():
            raise SystemExit(
                f"! {d / name} が無い。fetch_source.py と probe_signals.py を先に実行してください")

    signals = json.loads((d / "signals.json").read_text(encoding="utf-8"))
    cues = json.loads((d / "subs.json").read_text(encoding="utf-8"))
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    duration = int(meta.get("duration_sec") or 0)

    cands = find_candidates(signals, cues, duration, a.count, a.length, a.prefer)
    (d / "candidates.json").write_text(
        json.dumps(cands, ensure_ascii=False, indent=1), encoding="utf-8")

    if not cands:
        print("! 候補が0件。signals.json に信号が入っているか確認してください")
        return

    for i, c in enumerate(cands, 1):
        head = "".join(c["subtitles"][:4])[:46]
        s = c.get("signals") or {}
        # 位置（動画のどのあたりか）も出す。8本すべてが平均79%地点＝判定パート
        # からの切り出しになっていたのを、選ぶ前に気づけるようにする
        pos = c["start"] / duration * 100 if duration else 0
        breakdown = " ".join(f"{k}{s.get(k, 0)}" for k in ("詰め", "判定", "金額", "コメント"))
        print(f"{i}. {hms(c['start'])}-{hms(c['end'])}  {pos:.0f}%地点  "
              f"score={c['score']:.1f}  [{breakdown}]  {head}")

    money = [m for m in (signals.get("lexical") or []) if m["kind"] == "金額"][:8]
    if money:
        print("\n案件カードの下書き（金額の言及。ASRなので映像で裏取りすること）:")
        for m in money:
            print(f"  {hms(m['seconds'])} {m['line'][:44]}")


if __name__ == "__main__":
    main()
