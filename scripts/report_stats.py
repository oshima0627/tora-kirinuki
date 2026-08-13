#!/usr/bin/env python3
"""公開済みの動画の数字を並べる。

  python scripts/report_stats.py
  python scripts/report_stats.py --traffic     # トラフィックソースの内訳も出す

**再生数は `videos.list` の statistics で見ること。** YouTube Analytics は
2〜3日遅れるので、直近の日付が空でも「ゼロ確定」ではない。
インプレッション数とCTRは Analytics API に無く、Studio の画面でしか見られない。

2026-08-13 に4点（タイトルの型・冒頭の無音・ショートの尺・長尺の尺）を変えた。
その前後で差が出るかをここで見る。境目は08-14公開分から。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.upload_youtube import PUBLISHED, current_channel, get_service  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 4点の変更を入れたビルドが出るのはここから
CHANGED_FROM = "2026-08-14"


def iso_day(video: dict) -> str:
    st, sn = video["status"], video["snippet"]
    return (st.get("publishAt") or sn.get("publishedAt") or "")[:10]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--traffic", action="store_true",
                    help="トラフィックソースの内訳も出す")
    a = ap.parse_args()

    service = get_service()
    data = json.loads(PUBLISHED.read_text(encoding="utf-8-sig"))
    ids = [v["youtube_video_id"] for v in data["videos"].values()]
    if not ids:
        raise SystemExit("published.json に記録がありません")

    items = []
    for i in range(0, len(ids), 50):
        items += service.videos().list(
            part="snippet,statistics,status,contentDetails",
            id=",".join(ids[i:i + 50])).execute().get("items", [])

    rows = []
    for it in items:
        rows.append((iso_day(it), it["status"]["privacyStatus"],
                     it["contentDetails"]["duration"].replace("PT", ""),
                     int(it["statistics"].get("viewCount", 0)),
                     int(it["statistics"].get("likeCount", 0)),
                     it["snippet"]["title"][:38]))

    before = [r for r in rows if r[0] < CHANGED_FROM and r[1] == "public"]
    print(f"{'公開日':11} {'状態':8} {'尺':8} {'再生':>6} {'高評価':>5}  タイトル")
    for r in sorted(rows):
        mark = "  ← 変更後" if r[0] >= CHANGED_FROM else ""
        print(f"{r[0]:11} {r[1]:8} {r[2]:8} {r[3]:>6,} {r[4]:>5}  {r[5]}{mark}")

    if before:
        total = sum(r[3] for r in before)
        print(f"\n変更前の公開分 {len(before)}本 / 合計再生 {total:,}"
              f"（1本あたり {total / len(before):.1f}）")

    if a.traffic:
        from googleapiclient.discovery import build

        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from scripts.upload_youtube import SCOPES, TOKEN

        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        ya = build("youtubeAnalytics", "v2", credentials=creds)
        days = sorted({r[0] for r in rows if r[0]})
        # **未来の日付を渡すと400になる。** 予約ぶんが混ざるので今日で止める。
        # subscribersGained は insightTrafficSourceType と併用できない
        today = date.today().isoformat()
        res = ya.reports().query(
            ids=f"channel=={current_channel(service)['id']}",
            startDate=days[0], endDate=min(days[-1], today),
            metrics="views,estimatedMinutesWatched",
            dimensions="insightTrafficSourceType", sort="-views").execute()
        print("\nトラフィックソース（Analytics は2〜3日遅れる）")
        for row in res.get("rows") or []:
            print(f"  {row[0]:24} 再生{row[1]:>6}  視聴分{row[2]:>6}")


if __name__ == "__main__":
    main()
