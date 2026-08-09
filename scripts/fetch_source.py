#!/usr/bin/env python3
"""令和の虎Second の本編を取得する。

  python scripts/fetch_source.py --latest 5
  python scripts/fetch_source.py --latest 3 --list    # 取得せず一覧だけ
  python scripts/fetch_source.py <URL> [<URL>...]
  python scripts/fetch_source.py --latest 5 --force   # 取得済みも再取得

出力は work/<video_id>/ に source.mp4 / subs.json / meta.json。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.subtitles import parse_vtt  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"

CHANNEL_URL = "https://www.youtube.com/@reiwanotora_second/videos"
CHANNEL_ID = "UC9cD37sXfBNCQpz3vINa3TA"

# lang=ja を付けないと、タイトル・チャプター名が自動翻訳で英語になる
JA = {"youtube": {"lang": ["ja"]}}


def source_dir(video_id: str) -> Path:
    return WORK / video_id


def pick_ja_vtt(info: dict) -> tuple[str | None, str | None, str | None]:
    """日本語字幕のVTT URLを返す。手動字幕を優先し、無ければ自動生成。"""
    for store, kind in ((info.get("subtitles") or {}, "manual"),
                        (info.get("automatic_captions") or {}, "auto")):
        for lang in ("ja", "ja-orig", "ja-JP"):
            for track in store.get(lang) or []:
                if track.get("ext") == "vtt":
                    return track["url"], kind, lang
    return None, None, None


def list_channel(limit: int) -> list[dict]:
    """新着一覧（メタのみ）。

    RSS（feeds/videos.xml）は500/404を返すことがあるので yt-dlp の抽出を使う。
    """
    from yt_dlp import YoutubeDL

    opts = {"quiet": True, "no_warnings": True, "skip_download": True,
            "extract_flat": "in_playlist", "playlistend": limit,
            "extractor_args": JA}
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(CHANNEL_URL, download=False)
    return [{"id": e.get("id"), "title": e.get("title") or "",
             "duration": e.get("duration"),
             "url": f"https://www.youtube.com/watch?v={e.get('id')}"}
            for e in (info.get("entries") or [])]


def fetch_one(url: str, force: bool = False) -> Path:
    from yt_dlp import YoutubeDL

    with YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True,
                    "extractor_args": JA}) as ydl:
        info = ydl.extract_info(url, download=False)
        out = source_dir(info["id"])
        if (out / "source.mp4").exists() and not force:
            print(f"- {info['id']} は取得済み（--force で再取得）")
            return out
        out.mkdir(parents=True, exist_ok=True)

        sub_url, kind, lang = pick_ja_vtt(info)
        if not sub_url:
            raise SystemExit(
                f"! {info['id']}: 日本語字幕が無い。切り抜き地点を出せないので中断する")
        with ydl.urlopen(sub_url) as r:
            cues = parse_vtt(r.read().decode("utf-8", "replace"))

    (out / "subs.json").write_text(
        json.dumps([{"t": t, "line": l} for t, l in cues],
                   ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "meta.json").write_text(json.dumps({
        "video_id": info["id"],
        "url": info.get("webpage_url"),
        "title": info.get("title"),
        "duration_sec": info.get("duration"),
        "upload_date": info.get("upload_date"),
        "chapters": info.get("chapters") or [],
        "subtitle_kind": kind,
        "subtitle_lang": lang,
        "fetched_at": datetime.now(timezone.utc).astimezone().isoformat(
            timespec="seconds"),
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    with YoutubeDL({"quiet": True, "no_warnings": True, "extractor_args": JA,
                    "format": "bestvideo[height<=1080]+bestaudio/best",
                    "merge_output_format": "mp4",
                    "outtmpl": str(out / "source.%(ext)s")}) as ydl:
        ydl.download([url])

    print(f"✓ {info['id']}  {info.get('title')}  字幕{len(cues)}行")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("urls", nargs="*")
    ap.add_argument("--latest", type=int)
    ap.add_argument("--list", action="store_true", help="取得せず一覧だけ表示")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    urls = list(a.urls)
    if a.latest:
        items = list_channel(a.latest)
        if a.list:
            for it in items:
                print(f"{it['id']}  {it['title']}")
            return
        urls += [it["url"] for it in items]
    if not urls:
        raise SystemExit("URL か --latest を指定してください")
    for u in urls:
        fetch_one(u, a.force)


if __name__ == "__main__":
    main()
