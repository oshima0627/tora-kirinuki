#!/usr/bin/env python3
"""切り抜き動画をビルドする。

  python scripts/build_clip.py recipes/<id>.json --dry-run
  python scripts/build_clip.py recipes/<id>.json

出力は work/<id>/ に video.mp4 / thumb.png / description.txt / meta.json。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.cards import render_brief, render_point, render_verdict  # noqa: E402
from scripts.fetch_source import source_dir  # noqa: E402
from scripts.recipe import build_description, validate  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"

CARD_SEC = 4.0          # 案件カード・判定カードの表示秒数
POINT_SEC = 3.5         # 論点カードの表示秒数
DUR_TOLERANCE = 1.0     # ビルド後の尺の許容差（秒）
FPS = 30


def preflight(recipe: dict, src_dir: Path) -> list[str]:
    """素材の実在をまとめて確認する。

    ffmpeg が途中で落ちるより、何が足りないかを先に全部出したほうが直しやすい。
    レシピ自体の不備は ValueError で即座に落とす（規約違反の予防なので妥協しない）。
    """
    validate(recipe)

    missing = []
    for name in ("source.mp4", "subs.json"):
        if not (src_dir / name).exists():
            missing.append(f"{src_dir / name} が無い")

    start, end = recipe["clip"]["start"], recipe["clip"]["end"]

    meta_path = src_dir / "meta.json"
    if meta_path.exists():
        dur = json.loads(meta_path.read_text(encoding="utf-8")).get("duration_sec")
        if dur and end > dur:
            missing.append(f"clip.end={end} が元動画の尺 {dur} を超えている")

    for i, p in enumerate(recipe["cards"].get("points") or []):
        if not (start <= p.get("at", -1) <= end):
            missing.append(
                f"論点カード[{i}] の at={p.get('at')} が clip({start}-{end}) の外にある")
    return missing


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def _still(png: Path, out: Path, seconds: float) -> None:
    """静止画から尺つきの動画セグメントを作る。無音トラックを必ず付ける。"""
    _run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(png),
          "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
          "-t", f"{seconds}", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
          "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-r", str(FPS),
          "-vf", "scale=1920:1080", str(out)])


def _thumbnail(recipe: dict, src: Path, out: Path) -> None:
    """サムネイルを作る。

    recipe に thumb があれば競合の型で組む（黒帯＋左右の写真＋吹き出し＋極太行）。
    無ければ案件カードをそのまま使う。
    """
    thumb = recipe.get("thumb")
    if not thumb:
        render_brief(recipe["cards"]["brief"], size=(1280, 720)).save(out / "thumb.png")
        return

    from PIL import Image

    from scripts.thumbnail import compose_photos, render_thumbnail

    def grab(at: float, name: str) -> Image.Image:
        p = out / name
        _run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{at}",
              "-i", str(src / "source.mp4"), "-frames:v", "1", str(p)])
        return Image.open(p)

    faces = thumb.get("faces") or []
    frames = [grab(f["at"], f"_face{i}.png") for i, f in enumerate(faces)]
    photo = compose_photos(
        frames,
        [f.get("x", 0.5) for f in faces],
        biases=[f.get("bias") for f in faces],
        # 立位の人物は頭がフレーム上部に近く、既定の PHOTO_TOP だと頭が切れることがある。
        # その face だけ crop_top を小さくして頭上に余白を作る
        tops=[f.get("crop_top") for f in faces],
        # 会話テロップが画面下いっぱいに出るカットは crop_bottom でテロップ帯を落とす
        bottoms=[f.get("crop_bottom") for f in faces],
    )

    render_thumbnail(photo, thumb.get("top"), thumb.get("bubbles"),
                     thumb.get("bottom")).save(out / "thumb.png")


def build(recipe_path: Path, dry_run: bool = False) -> Path:
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    src = source_dir(recipe["source_video_id"])

    missing = preflight(recipe, src)
    if missing:
        for m in missing:
            print(f"! {m}")
        raise SystemExit("素材が足りないので中断する")

    start, end = recipe["clip"]["start"], recipe["clip"]["end"]
    length = end - start
    points = recipe["cards"].get("points") or []
    out = WORK / recipe["id"]

    if dry_run:
        print(f"[dry-run] {recipe['id']}")
        print(f"  切り出し {start:.1f}s - {end:.1f}s（{length:.1f}s）")
        print(f"  論点カード {len(points)} 枚")
        print(f"  合計尺の見込み {length + CARD_SEC * 2:.1f}s")
        return out

    out.mkdir(parents=True, exist_ok=True)
    cards = out / "cards"
    cards.mkdir(exist_ok=True)

    brief_png, verdict_png = cards / "brief.png", cards / "verdict.png"
    render_brief(recipe["cards"]["brief"]).save(brief_png)
    render_verdict(recipe["cards"].get("verdict") or {}).save(verdict_png)

    # 本体を切り出す。尺は -t で明示する（-ss だけだと入力側の丸めで伸びる）
    body = out / "body.mp4"
    _run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start}",
          "-i", str(src / "source.mp4"), "-t", f"{length}",
          "-vf", f"scale=1920:1080,fps={FPS}",
          "-c:v", "libx264", "-preset", "medium", "-crf", "20",
          "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", str(body)])

    # 論点カードを1枚ずつ重ねる
    overlaid = body
    for i, p in enumerate(points):
        at = p["at"] - start
        png = cards / f"point_{i}.png"
        render_point(p["text"]).save(png)
        nxt = out / f"_ov{i}.mp4"
        _run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(overlaid),
              "-i", str(png), "-filter_complex",
              f"[0:v][1:v]overlay=0:0:enable='between(t,{at},{at + POINT_SEC})'",
              "-c:a", "copy", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
              str(nxt)])
        overlaid = nxt

    _still(brief_png, out / "_brief.mp4", CARD_SEC)
    _still(verdict_png, out / "_verdict.mp4", CARD_SEC)

    concat = out / "concat.txt"
    concat.write_text("".join(
        f"file '{p.as_posix()}'\n"
        for p in (out / "_brief.mp4", overlaid, out / "_verdict.mp4")),
        encoding="utf-8")
    video = out / "video.mp4"
    _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
          "-i", str(concat), "-c", "copy", str(video)])

    expected = length + CARD_SEC * 2
    actual = probe_duration(video)
    if abs(actual - expected) > DUR_TOLERANCE:
        raise SystemExit(f"! 尺が合わない: 期待 {expected:.1f}s / 実測 {actual:.1f}s")

    (out / "description.txt").write_text(build_description(recipe), encoding="utf-8")
    _thumbnail(recipe, src, out)
    (out / "meta.json").write_text(json.dumps({
        "id": recipe["id"],
        "title": recipe["title"],
        "tags": recipe.get("tags") or [],
        "category_id": recipe.get("category_id", "22"),
        "privacy_status": recipe.get("privacy_status", "private"),
        "expected_channel_id": recipe["expected_channel_id"],
        "source_url": recipe["source_url"],
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"✓ {video}  {actual:.1f}s")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("recipe", type=Path)
    ap.add_argument("--dry-run", action="store_true",
                    help="素材の確認と尺の試算だけ行う")
    a = ap.parse_args()
    build(a.recipe, a.dry_run)


if __name__ == "__main__":
    main()
