#!/usr/bin/env python3
"""アカウントとチャンネルの状態を、そのまま画面に出す。書き込みはしない。

  python scripts/audit_account.py

**これは「published.json に何があるか」ではなく「YouTube に何があるか」を見る。**
両者はずれる。実際、published.json に載っていない private 動画が8本あった
（`docs/2026-08-26-account-audit.md`）。ずれたまま放置すると、旧動画の行方が
分からなくなる。

**API に無いものはここには出ない。** インプレッション数・CTR・著作権の申し立て・
収益化の資格状況は Studio の画面でしか見られない。出ないものを「無い」と
読み違えないこと。確認先は docs/2026-08-26-account-audit.md に URL を書いた。

消費するクォータは 5〜10 ユニット（channels/playlistItems/videos/playlists/
channelSections の list はどれも1ユニット）。1日10,000の枠に対して無視できる。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json  # noqa: E402

from scripts.upload_youtube import PUBLISHED, get_service  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# これより長いものを長尺として数える。ショートは60〜70秒で作っている
LONG_FORM_SECONDS = 180


def iso8601_seconds(dur: str) -> int:
    """PT15M2S → 902。"""
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", dur or "")
    if not m:
        return 0
    h, mi, se = (int(x or 0) for x in m.groups())
    return h * 3600 + mi * 60 + se


def uploads_playlist(channel: dict) -> str:
    return channel["contentDetails"]["relatedPlaylists"]["uploads"]


def all_video_ids(service, playlist_id: str) -> list[str]:
    ids: list[str] = []
    token = None
    while True:
        r = service.playlistItems().list(
            part="contentDetails", playlistId=playlist_id,
            maxResults=50, pageToken=token).execute()
        ids += [i["contentDetails"]["videoId"] for i in r["items"]]
        token = r.get("nextPageToken")
        if not token:
            return ids


def fetch_videos(service, ids: list[str]) -> list[dict]:
    out: list[dict] = []
    for i in range(0, len(ids), 50):
        out += service.videos().list(
            part="snippet,status,statistics,contentDetails",
            id=",".join(ids[i:i + 50])).execute()["items"]
    return out


def main() -> None:
    service = get_service()

    ch = service.channels().list(
        part="snippet,statistics,status,brandingSettings,contentDetails",
        mine=True).execute()["items"][0]
    sn, st, stat = ch["snippet"], ch["status"], ch["statistics"]
    print("== チャンネル ==")
    print(f"  {sn['title']}")
    print(f"  id       : {ch['id']}")
    print(f"  ハンドル : {sn.get('customUrl')}")
    print(f"  開設     : {sn['publishedAt'][:10]}  国 {sn.get('country')}  "
          f"言語 {sn.get('defaultLanguage')}")
    print(f"  公開設定 : {st.get('privacyStatus')}  "
          f"リンク {st.get('isLinked')}  "
          f"長時間アップロード {st.get('longUploadsStatus')}  "
          f"収益化 {st.get('isChannelMonetizationEnabled')}")
    print(f"  登録者   : {stat['subscriberCount']}"
          f"（非表示 {stat['hiddenSubscriberCount']}）  "
          f"総再生 {stat['viewCount']}  公開動画 {stat['videoCount']}")
    trailer = ch["brandingSettings"]["channel"].get("unsubscribedTrailer")
    print(f"  トレーラー: {trailer or '（未設定）'}")

    ids = all_video_ids(service, uploads_playlist(ch))
    videos = fetch_videos(service, ids)
    known = {v["youtube_video_id"]
             for v in json.loads(
                 PUBLISHED.read_text(encoding="utf-8-sig"))["videos"].values()}

    print(f"\n== 動画 {len(videos)} 本（published.json は {len(known)} 件）==")
    print(f"{'公開日時(UTC)':16} {'id':12} {'秒':>4} {'公開':8} {'状態':10} "
          f"{'再生':>6} {'高評価':>5} {'台帳':4} タイトル")
    orphans, long_views, short_views = [], 0, 0
    for v in sorted(videos, key=lambda v: (v["status"].get("publishAt")
                                           or v["snippet"]["publishedAt"])):
        s, n, c = v["status"], v["snippet"], v["contentDetails"]
        sec = iso8601_seconds(c.get("duration"))
        views = int(v.get("statistics", {}).get("viewCount", 0))
        on_ledger = v["id"] in known
        if not on_ledger:
            orphans.append(v)
        if sec >= LONG_FORM_SECONDS:
            long_views += views
        else:
            short_views += views
        day = (s.get("publishAt") or n["publishedAt"])[:16]
        print(f"{day:16} {v['id']:12} {sec:>4} {s['privacyStatus']:8} "
              f"{s['uploadStatus']:10} {views:>6} "
              f"{int(v.get('statistics', {}).get('likeCount', 0)):>5} "
              f"{'○' if on_ledger else '× 未登録':4} {n['title'][:26]}")

    print(f"\n  長尺（{LONG_FORM_SECONDS}秒以上）の再生合計: {long_views}")
    print(f"  ショートの再生合計            : {short_views}")

    # 台帳に無い動画は、消すことも差し替えることもできなくなる。名指しで出す
    if orphans:
        print(f"\n! published.json に無い動画が {len(orphans)} 本")
        for v in orphans:
            print(f"    {v['id']}  {v['status']['privacyStatus']:8} "
                  f"{v['snippet']['publishedAt'][:10]}  "
                  f"{v['snippet']['title'][:40]}")

    # 静かに配信を殺しうる設定。ここに出たら Studio で直す
    flagged = [v for v in videos
               if v["status"].get("madeForKids")
               or not v["status"].get("embeddable", True)
               or v["contentDetails"].get("regionRestriction")
               or v["status"].get("rejectionReason")]
    print(f"\n== 配信を妨げる設定 ==")
    if flagged:
        for v in flagged:
            print(f"  ! {v['id']} {json.dumps(v['status'], ensure_ascii=False)}")
    else:
        print("  子ども向け・埋め込み禁止・地域制限・拒否 いずれも無し")

    pls = service.playlists().list(
        part="snippet,status,contentDetails", channelId=ch["id"],
        maxResults=50).execute().get("items", [])
    print(f"\n== 再生リスト {len(pls)} 本 ==")
    for p in pls:
        print(f"  {p['id']} {p['status']['privacyStatus']:8} "
              f"{p['contentDetails']['itemCount']:>3}本 {p['snippet']['title']}")

    print("\n-- ここに出ないもの（Studio でしか見られない）--")
    print("  インプレッション数 / CTR  : アナリティクス > コンテンツ")
    print("  著作権の申し立て          : コンテンツ > フィルタ > 申し立て")
    print("  収益化の資格状況          : 収益化")


if __name__ == "__main__":
    main()
