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

# 2026-09-07、web_safari が字幕トラックを一切返さなくなった。
# 取得済みの動画（xtJI21E2-xE）でも automatic_captions が 0 件になる。
# 媒体URLの取得には web_safari が要るので、字幕だけこのクライアントで引き直す。
# 実測で tv と web_embedded は 157 トラック（ja / ja-orig を含む）を返した。
CAPTION_CLIENT = {"player_client": ["tv"]}
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


# 自動生成の ja は「日本語ASR → 英語 → 日本語」の往復訳で、
# 2026-09-07 の実測で「150万円」が「150万ドル」、「虎」が「タイガース」になっていた。
# 金額と固有名詞が命なので、自動生成では原文の ja-orig を先に採る。
# 手動字幕は人が書いた日本語なので ja のままでよい。
AUTO_LANG_ORDER = ("ja-orig", "ja", "ja-JP")
MANUAL_LANG_ORDER = ("ja", "ja-orig", "ja-JP")


def pick_ja_vtt(info: dict) -> tuple[str | None, str | None, str | None]:
    """日本語字幕のVTT URLを返す。手動字幕を優先し、無ければ自動生成。

    自動生成は ja より ja-orig（原文のASR）を優先する。上の注記を参照。
    """
    for store, kind, order in (
            (info.get("subtitles") or {}, "manual", MANUAL_LANG_ORDER),
            (info.get("automatic_captions") or {}, "auto", AUTO_LANG_ORDER)):
        for lang in order:
            for track in store.get(lang) or []:
                if track.get("ext") == "vtt":
                    return track["url"], kind, lang
    return None, None, None


def resolve_ja_captions(info: dict, reextract):
    """日本語字幕を返す。一次抽出に無ければ reextract() の結果でもう一度探す。

    reextract は字幕の出るクライアントで抽出し直す呼び出し。
    引き直しに失敗しても「字幕が無い」と同じ扱いにする（呼び出し側が中断する）。
    """
    found = pick_ja_vtt(info)
    if found[0]:
        return found
    try:
        again = reextract()
    except Exception as e:  # noqa: BLE001  抽出の失敗は「字幕なし」と同じ扱い
        print(f"! 字幕の引き直しに失敗した: {type(e).__name__}: {e}")
        return None, None, None
    return pick_ja_vtt(again or {})


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


def fetch_one(url: str, force: bool = False, subs_only: bool = False) -> Path:
    from yt_dlp import YoutubeDL

    with YoutubeDL(ydl_opts(skip_download=True)) as ydl:
        info = ydl.extract_info(url, download=False)
        out = source_dir(info["id"])
        if (out / "source.mp4").exists() and not (force or subs_only):
            print(f"- {info['id']} は取得済み（--force で再取得）")
            return out
        out.mkdir(parents=True, exist_ok=True)

        def _captions_via_fallback() -> dict:
            print(f"- {info['id']}: 一次抽出に日本語字幕が無い。"
                  f"{CAPTION_CLIENT['player_client'][0]} で引き直す")
            o = ydl_opts(skip_download=True)
            o["extractor_args"]["youtube"]["player_client"] = list(
                CAPTION_CLIENT["player_client"])
            with YoutubeDL(o) as y2:
                return y2.extract_info(url, download=False)

        sub_url, kind, lang = resolve_ja_captions(info, _captions_via_fallback)
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

    if subs_only:
        print(f"✓ {info['id']}  字幕だけ取り直した（{len(cues)}行 / {lang}）")
        return out

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
    ap.add_argument("--subs-only", action="store_true",
                    help="source.mp4 はそのままで subs.json / meta.json だけ取り直す")
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
        fetch_one(u, a.force, subs_only=a.subs_only)


if __name__ == "__main__":
    main()
