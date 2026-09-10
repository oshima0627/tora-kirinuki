#!/usr/bin/env python3
"""ショートの区間候補を総当たりで出す。

  python scripts/find_short.py <video_id>
  python scripts/find_short.py <video_id> --from 15 --to 25
  python scripts/find_short.py <video_id> --min 50 --max 58 --letterbox

**HANDOFF.md に手書きのスニペットとして置かれていたものを実装に移した
（2026-09-10）。** スニペットは終端の窓が 65〜73秒の直書きで、9/7〜9/12 の
6本すべてが 69.5〜74.6秒になった直接の原因だった。

出すのは「文頭に着地して、巻き戻しが0秒」の開始点だけ。巻き戻しが要る＝
そこが文の途中で、前提が入っていない。

`--letterbox` を付けると、候補の前後のフレームを抜いて上下端の輝度を測る。
元動画そのものが黒帯を入れている区間（番組の煽り差し込み）を縦型に組むと、
黒帯がそのまま入る。**目視ではなく測る。**
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.fetch_source import source_dir  # noqa: E402
from scripts.moments import is_letterboxed, short_candidates  # noqa: E402
from scripts.recipe import SHORT_TARGET_MAX, SHORT_TARGET_MIN  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def frame_at(video: Path, sec: float, out: Path) -> Path | None:
    """指定秒の1コマを抜く。抜けなければ None。"""
    r = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{sec}", "-i", str(video),
         "-frames:v", "1", str(out)], capture_output=True)
    return out if r.returncode == 0 and out.exists() else None


def letterbox_at(video: Path, secs: list[float]) -> list[float]:
    """レターボックスだった秒を返す。"""
    from PIL import Image

    hit = []
    with tempfile.TemporaryDirectory() as td:
        for i, s in enumerate(secs):
            f = frame_at(video, s, Path(td) / f"{i}.jpg")
            if f and is_letterboxed(Image.open(f)):
                hit.append(s)
    return hit


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video_id")
    # **15〜25分帯。** 実測（n=19）で帯の中 n=8 の平均視聴率 中央値 68.2%、
    # 帯の外 n=11 は 57.5%。決着シーン（後半）は前提を知らないと意味が分からない
    ap.add_argument("--from", dest="lo", type=float, default=15.0,
                    help="探す帯の開始（分。既定 15）")
    ap.add_argument("--to", dest="hi", type=float, default=25.0,
                    help="探す帯の終了（分。既定 25）")
    ap.add_argument("--min", type=float, default=SHORT_TARGET_MIN,
                    help=f"尺の下限（秒。既定 {SHORT_TARGET_MIN:.0f}）")
    ap.add_argument("--max", type=float, default=SHORT_TARGET_MAX,
                    help=f"尺の上限（秒。既定 {SHORT_TARGET_MAX:.0f}）")
    ap.add_argument("--letterbox", action="store_true",
                    help="候補の前後のフレームを抜いて黒帯を測る（source.mp4 が要る）")
    a = ap.parse_args()

    d = source_dir(a.video_id)
    subs = d / "subs.json"
    if not subs.exists():
        raise SystemExit(f"! {subs} が無い。fetch_source.py を先に実行してください")
    cues = json.loads(subs.read_text(encoding="utf-8"))

    lo, hi = a.lo * 60, a.hi * 60
    cands = short_candidates(cues, lo, hi, a.min, a.max)
    print(f"{a.lo:.1f}〜{a.hi:.1f}分 / 尺 {a.min:.0f}〜{a.max:.0f}秒 → {len(cands)}件")
    if not cands:
        print("! 候補が0件。--from/--to を広げるか、--min/--max を見直してください")
        return

    video = d / "source.mp4"
    for c in cands:
        print(f"\n開始 {c['start']:9.3f}（{c['start'] / 60:5.2f}分）"
              f"  尺候補 {c['lengths']}")
        print(f"   {c['line'][:60]}")
        if a.letterbox:
            if not video.exists():
                print(f"   ! {video} が無いので黒帯を測れない")
                continue
            # 冒頭・中ほど・終端の3点で足りる。黒帯は差し込み単位で続く
            secs = [c["start"], c["start"] + max(c["lengths"]) / 2,
                    c["start"] + max(c["lengths"])]
            hit = letterbox_at(video, secs)
            if hit:
                print(f"   ! レターボックス {[round(s, 1) for s in hit]} "
                      "→ 縦型に組むと黒帯が入る。この区間は避けること")
            else:
                print("   黒帯なし")


if __name__ == "__main__":
    main()
