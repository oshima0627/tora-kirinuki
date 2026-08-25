#!/usr/bin/env python3
"""公開済みの動画の数字を並べる。

  python scripts/report_stats.py
  python scripts/report_stats.py --traffic     # トラフィックソースの内訳も出す
  python scripts/report_stats.py --retention   # ショートの平均視聴率と残存を出す

**再生数は `videos.list` の statistics で見ること。** YouTube Analytics は
2〜3日遅れるので、直近の日付が空でも「ゼロ確定」ではない。
インプレッション数とCTRは Analytics API に無く、Studio の画面でしか見られない。

**08-20公開分でショートの配信が始まった。** それ以前は6〜15再生、以降は
数千再生で、こちらの変更では説明できない断絶がある（`docs/2026-08-25-baseline.md`）。
作りの差を見るならこの境目より後どうしで比べること。再生数はフィードの配信量に
支配されるので、見るのは平均視聴率。

**Analytics の `day` は太平洋時間。** JST の公開日より1日前にずれて出る。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.upload_youtube import PUBLISHED, current_channel, get_service  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ショートの配信が始まった境目（公開日・JST）
SHORTS_PICKUP = "2026-08-20"


def iso8601_seconds(dur: str) -> int:
    """PT15M2S → 902。時間は使わないので分・秒だけ見る。"""
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", dur)
    if not m:
        return 0
    h, mi, se = (int(x or 0) for x in m.groups())
    return h * 3600 + mi * 60 + se


def analytics(service):
    """Analytics API のクライアントと channel== の ids を返す。"""
    from googleapiclient.discovery import build

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from scripts.upload_youtube import SCOPES, TOKEN

    creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return (build("youtubeAnalytics", "v2", credentials=creds),
            f"channel=={current_channel(service)['id']}")


def iso_day(video: dict) -> str:
    st, sn = video["status"], video["snippet"]
    return (st.get("publishAt") or sn.get("publishedAt") or "")[:10]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--traffic", action="store_true",
                    help="トラフィックソースの内訳も出す")
    ap.add_argument("--retention", action="store_true",
                    help="ショートの平均視聴率と残存を出す")
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
                     it["snippet"]["title"][:38], it["id"],
                     iso8601_seconds(it["contentDetails"]["duration"])))

    before = [r for r in rows if r[0] < SHORTS_PICKUP and r[1] == "public"]
    print(f"{'公開日':11} {'状態':8} {'尺':8} {'再生':>6} {'高評価':>5}  タイトル")
    for r in sorted(rows):
        mark = "  ← 配信後" if r[0] >= SHORTS_PICKUP else ""
        print(f"{r[0]:11} {r[1]:8} {r[2]:8} {r[3]:>6,} {r[4]:>5}  {r[5]}{mark}")

    if before:
        total = sum(r[3] for r in before)
        print(f"\n配信が始まる前の公開分 {len(before)}本 / 合計再生 {total:,}"
              f"（1本あたり {total / len(before):.1f}）")

    if a.retention:
        ya, ids_ = analytics(service)
        days = sorted({r[0] for r in rows if r[0]})
        today = date.today().isoformat()
        start, end = days[0], min(days[-1], today)
        # **平均視聴率で比べること。** 再生数はショートフィードの配信量で決まる
        print(f"\nショートの視聴（Analytics {start}〜{end}・2〜3日遅れる）")
        print(f"{'公開日':11} {'再生':>6} {'平均%':>6} {'25%':>6} {'50%':>6} "
              f"{'75%':>6} {'高評価率':>7}  タイトル")
        for r in sorted(rows):
            if r[7] > 180 or r[1] != "public" or r[0] < SHORTS_PICKUP:
                continue
            res = ya.reports().query(
                ids=ids_, startDate=start, endDate=end,
                metrics="views,averageViewPercentage",
                filters=f"video=={r[6]}").execute().get("rows") or [[0, 0]]
            views, avg = res[0]
            keep = ya.reports().query(
                ids=ids_, startDate=start, endDate=end,
                metrics="audienceWatchRatio",
                dimensions="elapsedVideoTimeRatio",
                filters=f"video=={r[6]};audienceType==ORGANIC").execute().get("rows") or []
            at = {int(round(x[0] * 100)): x[1] for x in keep}
            cell = lambda p: f"{at[p] * 100:>5.1f}%" if p in at else "     -"  # noqa: E731
            like = f"{100 * r[4] / r[3]:>6.2f}%" if r[3] else "     -"
            print(f"{r[0]:11} {views:>6,} {avg:>5.1f}% {cell(25)} {cell(50)} "
                  f"{cell(75)} {like}  {r[5][:30]}")

    if a.traffic:
        ya, ids_ = analytics(service)
        days = sorted({r[0] for r in rows if r[0]})
        # **未来の日付を渡すと400になる。** 予約ぶんが混ざるので今日で止める。
        # subscribersGained は insightTrafficSourceType と併用できない
        today = date.today().isoformat()
        res = ya.reports().query(
            ids=ids_,
            startDate=days[0], endDate=min(days[-1], today),
            metrics="views,estimatedMinutesWatched",
            dimensions="insightTrafficSourceType", sort="-views").execute()
        print("\nトラフィックソース（Analytics は2〜3日遅れる）")
        for row in res.get("rows") or []:
            print(f"  {row[0]:24} 再生{row[1]:>6}  視聴分{row[2]:>6}")


if __name__ == "__main__":
    main()
