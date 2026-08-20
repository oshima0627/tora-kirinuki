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

from scripts.cards import (overflowing, render_brief, render_point,  # noqa: E402
                           render_verdict)
from scripts.fetch_source import source_dir  # noqa: E402
from scripts.recipe import build_description, validate  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"

# 案件カードと判定カードは、かつて静止画の動画セグメントを作って本編の前後に
# 連結していた。**やめた。** 冒頭4秒が無音（実測-91dB）の止め絵になり、
# 新規チャンネルの初回配信で最も効く「最初の数秒」を捨てていた。
# いまは本編に重ねるので、音は0秒から鳴る。
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

    brief = recipe["cards"].get("brief") or {}
    missing += overflowing(
        brief.get("amount", ""), brief.get("business", ""), brief.get("profile", ""),
        [p.get("text", "") for p in (recipe["cards"].get("points") or [])])

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


def overlay_plan(recipe: dict, cards: Path, length: float) -> list[tuple[Path, float, float]]:
    """(PNG, 表示開始, 表示終了) を本編の時間軸で返す。

    案件カードは冒頭、論点カードは指定秒、判定カードは末尾。すべて重ねるので
    尺は本編と一致する（連結していた頃は前後に4秒ずつ足されていた）。
    """
    start = recipe["clip"]["start"]
    plan = [(cards / "brief.png", 0.0, CARD_SEC)]
    for i, p in enumerate(recipe["cards"].get("points") or []):
        at = p["at"] - start
        plan.append((cards / f"point_{i}.png", at, at + POINT_SEC))
    plan.append((cards / "verdict.png", max(0.0, length - CARD_SEC), length))
    return plan


def overlay_filter(plan: list[tuple[Path, float, float]]) -> str:
    """入力0の映像に、入力1.. のPNGを時間指定で順に重ねるフィルタを組む。

    **1回のエンコードで全部重ねる。** 以前はカード1枚ごとに ffmpeg を回していて、
    9枚なら9世代ぶんの再エンコード劣化とビルド時間がかかっていた。
    """
    parts = [f"[0:v]scale=1920:1080,fps={FPS}[v0]"]
    for i, (_, s, e) in enumerate(plan):
        parts.append(f"[v{i}][{i + 1}:v]overlay=0:0:"
                     f"enable='between(t,{s:.3f},{e:.3f})'[v{i + 1}]")
    return ";".join(parts)


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


def build(recipe_path: Path, dry_run: bool = False,
          thumb_only: bool = False) -> Path:
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

    # **サムネは1回では決まらない。** 顔の切り取りも吹き出しの高さも、
    # 実物を見て直すことになる。そのたびに15分の再エンコードを挟むと
    # 確認そのものが雑になるので、絵だけ作り直せるようにしてある
    if thumb_only:
        out.mkdir(parents=True, exist_ok=True)
        _thumbnail(recipe, src, out)
        print(f"✓ {out / 'thumb.png'}")
        return out

    if dry_run:
        print(f"[dry-run] {recipe['id']}")
        print(f"  切り出し {start:.1f}s - {end:.1f}s（{length:.1f}s）")
        print(f"  論点カード {len(points)} 枚")
        print(f"  合計尺の見込み {length:.1f}s（カードは重ねるので尺は増えない）")
        return out

    out.mkdir(parents=True, exist_ok=True)
    cards = out / "cards"
    cards.mkdir(exist_ok=True)

    render_brief(recipe["cards"]["brief"]).save(cards / "brief.png")
    render_verdict(recipe["cards"].get("verdict") or {}).save(cards / "verdict.png")
    for i, p in enumerate(points):
        render_point(p["text"]).save(cards / f"point_{i}.png")

    plan = overlay_plan(recipe, cards, length)
    video = out / "video.mp4"
    # 尺は -t で明示する（-ss だけだと入力側の丸めで伸びる）
    # **-t は出力側に置く。** 入力の -i と次の -i のあいだに書くと、
    # 後続のPNG入力に対する指定として解釈され、切り出しの終端が効かない
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-ss", f"{start}", "-i", str(src / "source.mp4")]
    for png, _, _ in plan:
        cmd += ["-i", str(png)]
    cmd += ["-t", f"{length}",
            "-filter_complex", overlay_filter(plan),
            "-map", f"[v{len(plan)}]", "-map", "0:a",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", str(video)]
    _run(cmd)

    expected = length
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
    ap.add_argument("--thumb-only", action="store_true",
                    help="thumb.png だけ作り直す（本編は再エンコードしない）")
    a = ap.parse_args()
    build(a.recipe, a.dry_run, a.thumb_only)


if __name__ == "__main__":
    main()
