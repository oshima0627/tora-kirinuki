#!/usr/bin/env python3
"""同じレシピから縦型ショートをビルドする。

  python scripts/build_short.py recipes/<id>.json --dry-run
  python scripts/build_short.py recipes/<id>.json

長尺（build_clip.py）とレシピを共有する。素材・候補・カードの文言をそのまま
使えるので、ショートを足しても調べ直しが要らない。

元映像は16:9。縦型では中央を1:1で抜き、上にフック・下に図解を置く。
全画面クロップより情報量が入り、図解という差別化軸を縦でも保てる。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_clip import probe_duration  # noqa: E402
from scripts.cards import (SHORT_BOTTOM, SHORT_SIZE, SHORT_TOP,  # noqa: E402
                           render_short_frame)
from scripts.fetch_source import source_dir  # noqa: E402
from scripts.recipe import build_description, validate, validate_short  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"

DUR_TOLERANCE = 1.0
FPS = 30


def preflight(recipe: dict, src_dir: Path) -> list[str]:
    validate(recipe)
    validate_short(recipe)

    missing = []
    if not (src_dir / "source.mp4").exists():
        missing.append(f"{src_dir / 'source.mp4'} が無い")

    meta_path = src_dir / "meta.json"
    if meta_path.exists():
        dur = json.loads(meta_path.read_text(encoding="utf-8")).get("duration_sec")
        if dur and recipe["short"]["end"] > dur:
            missing.append(
                f"short.end={recipe['short']['end']} が元動画の尺 {dur} を超えている")
    return missing


def build(recipe_path: Path, dry_run: bool = False) -> Path:
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    src = source_dir(recipe["source_video_id"])

    missing = preflight(recipe, src)
    if missing:
        for m in missing:
            print(f"! {m}")
        raise SystemExit("素材が足りないので中断する")

    short = recipe["short"]
    start, end = short["start"], short["end"]
    length = end - start
    out = WORK / f"{recipe['id']}-short"

    if dry_run:
        print(f"[dry-run] {recipe['id']}-short")
        print(f"  切り出し {start:.1f}s - {end:.1f}s（{length:.1f}s）")
        print(f"  フック: {short['hook'][:40]}")
        return out

    out.mkdir(parents=True, exist_ok=True)
    frame = out / "frame.png"
    render_short_frame(short.get("head"), short.get("quote")).save(frame)

    w, h = SHORT_SIZE
    vy = int(h * SHORT_TOP)
    vh = h - vy - int(h * SHORT_BOTTOM)
    video = out / "video.mp4"
    # **縦にトリミングして顔を大きくする。** 16:9をそのまま幅に合わせると
    # 映像が小さくなり、縦型として弱い（競合の上位はどれも大きく寄せている）。
    # 上下の黒帯が元動画の告知と字幕を覆うので、二重にもならない
    ar = w / vh
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start}",
         "-i", str(src / "source.mp4"), "-i", str(frame), "-t", f"{length}",
         "-filter_complex",
         # 元動画のテロップが映像領域に写り込むのは許容する。
         # 先に落とすと寄りすぎて顔が切れるため（実ビルドで確認）
         f"[0:v]crop='min(iw,ih*{ar:.4f})':'min(ih,iw/{ar:.4f})',"
         f"scale={w}:{vh},fps={FPS},pad={w}:{h}:0:{vy}:color=black[bg];"
         f"[bg][1:v]overlay=0:0[out]",
         "-map", "[out]", "-map", "0:a",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
         str(video)], check=True, capture_output=True)

    actual = probe_duration(video)
    if abs(actual - length) > DUR_TOLERANCE:
        raise SystemExit(f"! 尺が合わない: 期待 {length:.1f}s / 実測 {actual:.1f}s")

    # サムネイルは完成映像の1コマを使う。下地と映像が合成された実際の見た目になる
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-ss", "1", "-i", str(video),
         "-frames:v", "1", str(out / "thumb.png")], check=True, capture_output=True)

    (out / "description.txt").write_text(build_description(recipe), encoding="utf-8")
    (out / "meta.json").write_text(json.dumps({
        "id": f"{recipe['id']}-short",
        "title": (short.get("title") or short["hook"])[:100],
        # #Shorts が無いと縦型でもショート棚に乗らないことがある
        "tags": (recipe.get("tags") or []) + ["Shorts"],
        "category_id": recipe.get("category_id", "22"),
        "privacy_status": recipe.get("privacy_status", "private"),
        "expected_channel_id": recipe["expected_channel_id"],
        "source_url": recipe["source_url"],
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"✓ {video}  {actual:.1f}s  {w}x{h}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("recipe", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    build(a.recipe, a.dry_run)


if __name__ == "__main__":
    main()
