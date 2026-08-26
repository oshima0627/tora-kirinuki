#!/usr/bin/env python3
"""ショートから長尺への導線が、YouTube 側の実物でどうなっているかを出す。書き込みはしない。

  python scripts/audit_links.py

**導線は2本ある。この2本を混同しない。**

1. 概要欄のリンク（`upload_youtube.py` の `with_long_form_link()` が入れる）
   → API で読める。このスクリプトが見るのはこちら
2. Shorts の「関連動画」欄（Studio の動画詳細にある。ショートのプレイヤー本体に出る）
   → **Data API にフィールドが無い。ここには出ないし、設定もできない**

1 が全部入っていても 2 は空でありうる。実際そうなっている（2026-08-26 時点）。
2 の確認は Studio の画面でしかできない。

消費するクォータは playlistItems と videos の list だけで 5〜10 ユニット。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json  # noqa: E402

from scripts.audit_account import (  # noqa: E402
    LONG_FORM_SECONDS, all_video_ids, fetch_videos, iso8601_seconds,
    uploads_playlist,
)
from scripts.upload_youtube import PUBLISHED, get_service  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

VIDEO_URL = re.compile(r"(?:youtu\.be/|watch\?v=)([\w-]{11})")


def main() -> None:
    service = get_service()
    ch = service.channels().list(part="contentDetails", mine=True).execute()
    videos = fetch_videos(service, all_video_ids(service,
                                                 uploads_playlist(ch["items"][0])))

    ledger = json.loads(PUBLISHED.read_text(encoding="utf-8-sig"))["videos"]
    key_of = {v["youtube_video_id"]: k for k, v in ledger.items()}
    long_ids = {v["youtube_video_id"] for k, v in ledger.items()
                if not k.endswith("-short")}

    shorts = [v for v in videos
              if iso8601_seconds(v["contentDetails"]["duration"])
              < LONG_FORM_SECONDS]
    shorts.sort(key=lambda v: v["snippet"]["publishedAt"])

    print(f"== 概要欄の長尺リンク ==（動画 {len(videos)} 本 / "
          f"{LONG_FORM_SECONDS}秒未満 {len(shorts)} 本）")
    print(f"{'公開(UTC)':17} {'id':12} {'台帳キー':32} {'公開':8} 長尺リンク")

    missing = 0
    for v in shorts:
        vid, desc = v["id"], v["snippet"]["description"]
        key = key_of.get(vid)
        found = [m for m in VIDEO_URL.findall(desc) if m in long_ids]
        pair = None
        if key and key.endswith("-short"):
            entry = ledger.get(key[: -len("-short")])
            pair = entry["youtube_video_id"] if entry else None

        if pair and pair in found:
            mark = f"○ {pair}"
        elif found:
            mark = f"△ 別の長尺 {found[0]}"
        else:
            mark = "× 無し"
            missing += 1
        print(f"{v['snippet']['publishedAt'][:16]:17} {vid:12} "
              f"{(key or '(台帳に無い)'):32} {v['status']['privacyStatus']:8} {mark}")

    print(f"\n  概要欄にリンクが無いショート: {missing} 本")

    # ここを毎回読ませる。数字が全部○でも、届く導線はまだ空かもしれない
    print("\n== Shorts の「関連動画」欄 ==")
    print("  API では読めない。Studio の 動画 > 詳細 > 関連動画 を目で見ること。")
    print("  設定には『上級者向け機能』の認証が要る。")
    print("  設定 > チャンネル > 機能の利用資格 で状態を確認する。")


if __name__ == "__main__":
    main()
