#!/usr/bin/env python3
"""区間の字幕を時刻付きで出す。レシピを書くときに中身を読むため。

  python scripts/show_subs.py <video_id> 1909 2809
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.fetch_source import source_dir  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def hms(sec: float) -> str:
    s = int(sec)
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video_id")
    ap.add_argument("start", type=float)
    ap.add_argument("end", type=float)
    ap.add_argument("--every", type=float, default=0.0,
                    help="この秒数ごとに1行にまとめる（流し読み用）")
    a = ap.parse_args()

    cues = json.loads((source_dir(a.video_id) / "subs.json").read_text(encoding="utf-8"))
    sel = [c for c in cues if a.start <= c["t"] <= a.end]
    if not a.every:
        for c in sel:
            print(f"{hms(c['t'])} {c['line']}")
        return
    buf, bucket = [], None
    for c in sel:
        b = int(c["t"] // a.every)
        if bucket is None:
            bucket = b
        if b != bucket:
            print(f"{hms(bucket * a.every)} {''.join(buf)}")
            buf, bucket = [], b
        buf.append(c["line"])
    if buf:
        print(f"{hms(bucket * a.every)} {''.join(buf)}")


if __name__ == "__main__":
    main()
