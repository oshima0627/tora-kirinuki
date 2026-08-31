#!/usr/bin/env python3
"""同じレシピから縦型ショートをビルドする。

  python scripts/build_short.py recipes/<id>.json --dry-run
  python scripts/build_short.py recipes/<id>.json

長尺（build_clip.py）とレシピを共有する。素材・候補・カードの文言をそのまま
使えるので、ショートを足しても調べ直しが要らない。

**2026-08-24 に作り直した。** 視聴者コメント「切り抜き方が下手でどういう意味なのか
全くわからない」（唯一付いたコメント）を受けて実物を測った結果、3つ直した。

  1. 開始点を話題の頭まで巻き戻す（19本中18本が発話の途中から始まっていた）
  2. 字幕を時間同期で焼く（それまでは1枚のPNGを全区間に重ねていた）
  3. 横のトリミングをやめる（元動画の要約テロップが左右に切れて読めなかった）
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
                           render_short_caption, render_short_frame)
from scripts.fetch_source import source_dir  # noqa: E402
from scripts.moments import rewind_to_topic_head  # noqa: E402
from scripts.recipe import (build_caption, build_description,  # noqa: E402
                            validate, validate_short)
from scripts.subtitles import (burn_plan, risky_lines,  # noqa: E402
                               unused_fixes)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"

DUR_TOLERANCE = 1.0
FPS = 30


def load_cues(src_dir: Path) -> list[dict]:
    path = src_dir / "subs.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def plan_span(recipe: dict, cues: list[dict]) -> tuple[float, float, dict]:
    """実際にビルドする区間と、巻き戻しの着地点を返す。"""
    short = recipe["short"]
    landed = rewind_to_topic_head(short["start"], cues)
    return landed["start"], short["end"], landed


def preflight(recipe: dict, src_dir: Path, cues: list[dict]) -> list[str]:
    validate(recipe)
    for w in validate_short(recipe, cues or None):
        print(f"! {w}")

    missing = []
    if not (src_dir / "source.mp4").exists():
        missing.append(f"{src_dir / 'source.mp4'} が無い")
    # **字幕が無ければ焼けない。** 字幕の無いショートを出したのが今回の原因
    if not cues:
        missing.append(f"{src_dir / 'subs.json'} が無い。fetch_source.py を先に実行すること")

    meta_path = src_dir / "meta.json"
    if meta_path.exists():
        dur = json.loads(meta_path.read_text(encoding="utf-8")).get("duration_sec")
        if dur and recipe["short"]["end"] > dur:
            missing.append(
                f"short.end={recipe['short']['end']} が元動画の尺 {dur} を超えている")
    return missing


def _report(recipe: dict, start: float, end: float, landed: dict,
            plan: list[dict], cues: list[dict]) -> None:
    """--dry-run と本ビルドの両方で出す。**自動の行き過ぎを目で止めるため。**"""
    print(f"  切り出し {start:.1f}s - {end:.1f}s（{end - start:.1f}s）")
    if landed["start"] < recipe["short"]["start"]:
        print(f"  巻き戻し {recipe['short']['start']:.1f} → {start:.1f}"
              f"（-{recipe['short']['start'] - start:.1f}s）"
              f"[{landed['kind']}] {landed['line'][:44]}")
    print(f"  字幕 {len(plan)}枚")
    for p in plan:
        print(f"    {p['start']:6.2f}-{p['end']:6.2f}  {p['text']}")

    stale = unused_fixes(cues, start, end, recipe.get("fixes"))
    if stale:
        print(f"  ! recipe.fixes のうち当たらなかったもの: {'/ '.join(stale)}")

    risky = risky_lines(plan)
    if risky:
        # ASRは実測で「土橋さん→その悪さん」「焼き鳥3級→焼き鳥産」と崩れる。
        # 令和の虎は金額が命なので、焼く前に必ず人の目に掛ける
        print(f"  ! 数字を含む字幕が {len(risky)}行ある。ASRは金額と固有名詞を崩すので、"
              "映像で裏取りすること")
        for p in risky:
            print(f"    {p['start']:6.2f}  {p['text']}")


def video_filter(n_captions: int) -> str:
    """映像を16:9のまま置き、下地と字幕を順に重ねるフィルタを組む。

    **横にトリミングしない。** 元動画は制作側が画面下いっぱいに要約テロップを
    焼き込んでいる。中央61%に詰めていたので「マイナスな発言が多い」が
    「ナスな発言が多」に化けて画面中央に残っていた（実測）。
    """
    w, h = SHORT_SIZE
    vy = int(h * SHORT_TOP)
    vh = h - vy - int(h * SHORT_BOTTOM)
    parts = [f"[0:v]scale={w}:{vh}:force_original_aspect_ratio=decrease,"
             f"pad={w}:{vh}:(ow-iw)/2:(oh-ih)/2:color=black,fps={FPS},"
             f"pad={w}:{h}:0:{vy}:color=black[v0]"]
    parts.append("[v0][1:v]overlay=0:0[v1]")          # 黒帯とフック
    return ";".join(parts), vh


def build(recipe_path: Path, dry_run: bool = False) -> Path:
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    src = source_dir(recipe["source_video_id"])
    cues = load_cues(src)

    missing = preflight(recipe, src, cues)
    if missing:
        for m in missing:
            print(f"! {m}")
        raise SystemExit("素材が足りないので中断する")

    start, end, landed = plan_span(recipe, cues)
    plan = burn_plan(cues, start, end, fixes=recipe.get("fixes"))
    length = end - start
    out = WORK / f"{recipe['id']}-short"

    print(f"[{'dry-run' if dry_run else 'build'}] {recipe['id']}-short")
    _report(recipe, start, end, landed, plan, cues)
    print(f"  フック: {recipe['short']['hook'][:44]}")
    if dry_run:
        return out

    out.mkdir(parents=True, exist_ok=True)
    caps = out / "captions"
    caps.mkdir(exist_ok=True)
    for f in caps.glob("*.png"):
        f.unlink()

    frame = out / "frame.png"
    # **下帯は字幕に譲る。** レシピの quote（固定引用）は焼かない。
    # 上帯の head が同じことを言っているうえ、固定の台詞は話者を取り違えさせる
    render_short_frame(recipe["short"].get("head")).save(frame)

    inputs = ["-i", str(src / "source.mp4"), "-i", str(frame)]
    chain, _ = video_filter(len(plan))
    for i, p in enumerate(plan):
        png = caps / f"{i:03d}.png"
        render_short_caption(p["text"]).save(png)
        inputs += ["-i", str(png)]
        chain += (f";[v{i + 1}][{i + 2}:v]overlay=0:0:"
                  f"enable='between(t,{p['start']:.3f},{p['end']:.3f})'[v{i + 2}]")
    last = f"[v{len(plan) + 1}]"

    video = out / "video.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start}", *inputs,
         "-t", f"{length}", "-filter_complex", chain,
         "-map", last, "-map", "0:a",
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
    # TikTok へは手で投稿する。貼り付けるテキストをここで出しておく
    (out / "caption.txt").write_text(build_caption(recipe), encoding="utf-8")
    short = recipe["short"]
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

    w, h = SHORT_SIZE
    print(f"✓ {video}  {actual:.1f}s  {w}x{h}  字幕{len(plan)}枚")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("recipe", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    build(a.recipe, a.dry_run)


if __name__ == "__main__":
    main()
