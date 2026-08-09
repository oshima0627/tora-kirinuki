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
    ap.add_argument("--length", type=float, default=420.0,
                    help="1本の目安の尺（秒）")
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

    cands = find_candidates(signals, cues, duration, a.count, a.length)
    (d / "candidates.json").write_text(
        json.dumps(cands, ensure_ascii=False, indent=1), encoding="utf-8")

    if not cands:
        print("! 候補が0件。signals.json に信号が入っているか確認してください")
        return

    for i, c in enumerate(cands, 1):
        head = "".join(c["subtitles"][:4])[:56]
        print(f"{i}. {hms(c['start'])}-{hms(c['end'])}  score={c['score']:.1f}  {head}")

    money = [m for m in (signals.get("lexical") or []) if m["kind"] == "金額"][:8]
    if money:
        print("\n案件カードの下書き（金額の言及。ASRなので映像で裏取りすること）:")
        for m in money:
            print(f"  {hms(m['seconds'])} {m['line'][:44]}")


if __name__ == "__main__":
    main()
