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

# 2026-08-19、YouTube 側の変更で素の yt-dlp では本編が落とせなくなった（HTTP 403）。
# 次の3つが揃って初めて通る。ひとつでも欠けると症状が変わるだけで落ちる。
#
#   1. JSランタイム   署名チャレンジの解読に要る。無いと android_vr へ退避して 403
#   2. POトークン     bgutil のプロバイダが要る。未起動だと同じく 403
#   3. web_safari     既定クライアントの媒体URLは 403。Cookie も併せて要る
#                     （Cookie 無しだと "Only images are available" になる）
#
# 2 は常駐サーバが要る。起動していない場合は下の PO_TOKEN_SERVER_HINT を出す。
#   cd ~/bgutil-ytdlp-pot-provider/server && node build/main.js
#
# web_safari では DASH（映像と音声が別）が出ず、HLSの結合フォーマットだけになる。
# 1080p は itag 96。fetch は下の FORMAT で明示的に 1080p までに抑える。
COMPAT = {
    "js_runtimes": {"node": {}},
    "cookiesfrombrowser": ("firefox", None, None, None),
}
CLIENT = {"player_client": ["web_safari"]}
FORMAT = "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"

PO_TOKEN_SERVER = "http://127.0.0.1:4416"
PO_TOKEN_SERVER_HINT = (
    "! POトークンのプロバイダが起動していません。別のシェルで先にこれを実行してください:\n"
    "    cd ~/bgutil-ytdlp-pot-provider/server && node build/main.js")


def check_pot_server() -> None:
    """未起動のまま走ると 403 で落ちるだけで理由が出ないので、先に見る。"""
    import urllib.error
    import urllib.request
    try:
        urllib.request.urlopen(f"{PO_TOKEN_SERVER}/ping", timeout=5).read()
    except (urllib.error.URLError, OSError):
        raise SystemExit(PO_TOKEN_SERVER_HINT)


def ydl_opts(**extra: object) -> dict:
    """yt-dlp のオプションに、上の回避策をまとめて足す。"""
    opts: dict = {"quiet": True, "no_warnings": True, **COMPAT}
    ea = dict(extra.pop("extractor_args", None) or JA)
    ea["youtube"] = {**ea.get("youtube", {}), **CLIENT}
    opts["extractor_args"] = ea
    opts.update(extra)
    return opts


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

    opts = ydl_opts(skip_download=True, extract_flat="in_playlist",
                    playlistend=limit)
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(CHANNEL_URL, download=False)
    return [{"id": e.get("id"), "title": e.get("title") or "",
             "duration": e.get("duration"),
             "url": f"https://www.youtube.com/watch?v={e.get('id')}"}
            for e in (info.get("entries") or [])]


def fetch_one(url: str, force: bool = False) -> Path:
    from yt_dlp import YoutubeDL

    with YoutubeDL(ydl_opts(skip_download=True)) as ydl:
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

    with YoutubeDL(ydl_opts(format=FORMAT, merge_output_format="mp4",
                            outtmpl=str(out / "source.%(ext)s"))) as ydl:
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
    check_pot_server()
    for u in urls:
        fetch_one(u, a.force)


if __name__ == "__main__":
    main()
