#!/usr/bin/env python3
"""チャンネルトレーラーを、いちばん数字の良いショートに差し替える。

  python scripts/set_trailer.py                 # 現状と推奨を出すだけ
  python scripts/set_trailer.py --apply
  python scripts/set_trailer.py --video <id> --apply

トレーラーは**未登録者がチャンネルページを開いたときに自動再生される動画**。
2026-09-10 時点で `VwO47R4gGsE`（8/13公開・5分38秒の長尺・2再生）が入っていた。
チャンネル経由の再生は410あるので、**受け皿がいちばん数字の悪い動画**になっていた
（docs/2026-09-10-analytics.md）。

推奨は「公開済みショートのうち平均視聴率が最大のもの」。再生数では選ばない。
再生数はショートフィードの配信量に支配される（相関 +0.49 止まり）。

**`channels.update` の brandingSettings は部分更新ではない。** 読んだものを
まるごと送り返し、`unsubscribedTrailer` だけ差し替える。落とすと説明文や
既定言語が消える。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.report_stats import analytics, iso8601_seconds  # noqa: E402
from scripts.upload_youtube import PUBLISHED, get_service  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SHORT_MAX_SEC = 180


def _retry(request, tries: int = 4):
    """Analytics は 500 backendError を散発的に返す。数回だけ待って引き直す。"""
    import time

    from googleapiclient.errors import HttpError
    for i in range(tries):
        try:
            return request.execute()
        except HttpError as e:
            if e.resp.status < 500 or i == tries - 1:
                raise
            time.sleep(2 ** i)


def best_short(service) -> tuple[str, float, int, str] | None:
    """公開済みショートを平均視聴率で並べ、最大のものを返す。"""
    led = json.loads(PUBLISHED.read_text(encoding="utf-8-sig"))["videos"]
    ids = [v["youtube_video_id"] for v in led.values()]
    items = []
    for i in range(0, len(ids), 50):
        items += service.videos().list(
            part="snippet,status,contentDetails",
            id=",".join(ids[i:i + 50])).execute().get("items", [])

    ya, cid = analytics(service)
    today = date.today().isoformat()
    rows = []
    for it in items:
        if it["status"]["privacyStatus"] != "public":
            continue
        if iso8601_seconds(it["contentDetails"]["duration"]) > SHORT_MAX_SEC:
            continue
        r = (_retry(ya.reports().query(
            ids=cid, startDate="2026-08-01", endDate=today,
            metrics="views,averageViewPercentage",
            filters=f"video=={it['id']}")).get("rows") or [[0, 0]])[0]
        # **再生が少ない本の平均視聴率は当てにならない。** n=16 で64.3%が出た例がある
        if r[0] < 500:
            continue
        rows.append((r[1], r[0], it["id"], it["snippet"]["title"]))
    if not rows:
        return None
    avg, views, vid, title = max(rows)
    return vid, avg, views, title


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", help="トレーラーにする動画ID（省略時は自動で選ぶ）")
    ap.add_argument("--apply", action="store_true",
                    help="実際に設定する（既定は表示のみ）")
    a = ap.parse_args()

    service = get_service()
    ch = service.channels().list(
        part="snippet,brandingSettings", mine=True).execute()["items"][0]
    branding = ch["brandingSettings"]
    now = branding["channel"].get("unsubscribedTrailer")
    print(f"チャンネル: {ch['snippet']['title']}")
    print(f"いまのトレーラー: {now or '（未設定）'}")

    if a.video:
        target, why = a.video, "手で指定"
    else:
        pick = best_short(service)
        if not pick:
            raise SystemExit("! 推奨を選べなかった（再生500以上の公開ショートが無い）")
        target, avg, views, title = pick
        why = f"平均視聴率 {avg:.1f}% / 再生 {views:,} / {title[:36]}"
    print(f"推奨: {target}  {why}")

    if now == target:
        print("すでに設定済み。何もしない")
        return
    if not a.apply:
        print("\n--apply を付けると設定します（付けるまで何も変えません）")
        return

    branding["channel"]["unsubscribedTrailer"] = target
    service.channels().update(
        part="brandingSettings",
        body={"id": ch["id"], "brandingSettings": branding}).execute()

    # **直後に読み直すと古い値が返る。** 2026-09-10 に実測。update の応答も
    # 更新前の値を返してくるので、応答は検証に使えない。数秒おいて引き直す
    import time

    got = None
    for i in range(5):
        time.sleep(2)
        after = service.channels().list(
            part="brandingSettings", mine=True).execute()["items"][0]
        got = after["brandingSettings"]["channel"].get("unsubscribedTrailer")
        if got == target:
            print(f"✓ 設定した。{i * 2 + 2}秒後に読み直して確認: {got}")
            return
    raise SystemExit(
        f"! 10秒待っても反映されない（読み直した値 {got}）。"
        "Studio のカスタマイズ > レイアウト で確認すること")


if __name__ == "__main__":
    main()
