#!/usr/bin/env python3
"""再生リストの中身を、レシピの判定カードに合わせて揃える。

  python scripts/sync_playlists.py            # 何をするかだけ出す（既定・書き込みなし）
  python scripts/sync_playlists.py --apply    # 実際に足す・外す

**なぜ要るか**: 2026-08-27 時点で「完全ALL成立回」12本のうち6本が
台帳に無い非公開動画だった。視聴者には「非公開の動画」としか出ない。
逆に 08-13 以降の公開動画はどの再生リストにも入っていない。

**分類はレシピの `cards.verdict.result` から決める。** 推測しない。
「完全ALL / ALL / エクシード」→ 成立、「ナッシング」→ 不成立、
「協力確約」→ SNS版（お金ではなく協力の確約で終わる回）。
どれにも当たらなければ触らない（「触らない」として出す）。

**非公開の動画は入れない。** 予約公開の分は、公開された日に流し直す。

クォータ: playlistItems の insert / delete が 1回 50 ユニット。
playlists.insert も 50。--apply の前に必ずドライランで本数を数えること。
"""

from __future__ import annotations

import argparse
import glob
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.upload_youtube import PUBLISHED, get_service  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 分類名 -> (再生リストのタイトル, 説明)
BUCKETS = {
    "成立": (
        "完全ALL成立回｜令和の虎Second 切り抜き",
        "虎が全員そろって出資した「完全ALL」の回だけを集めました。"
        "希望額・詰めどころ・出資の内訳を図解で整理しています。",
    ),
    "不成立": (
        "不成立・虎が詰めた回｜令和の虎Second 切り抜き",
        "出資に至らなかった回を集めました。虎が何を問題視したのか、"
        "決裂の理由を図解で整理しています。",
    ),
    "協力確約": (
        "協力確約で終わった回｜令和の虎Second 切り抜き",
        "お金ではなく「どっぷり手伝う」で決着したSNS版の回を集めました。"
        "虎が何を評価したのかを図解で整理しています。",
    ),
}


def classify(result: str):
    """判定カードの result 文字列から分類を決める。当たらなければ None。"""
    if not result or "要裏取り" in result:
        return None
    if "協力確約" in result:
        return "協力確約"
    if "ナッシング" in result:
        return "不成立"
    if "ALL" in result or "エクシード" in result:
        return "成立"
    return None


def recipe_verdicts():
    """レシピID -> 判定カードの result。"""
    out = {}
    for path in glob.glob(str(ROOT / "recipes" / "*.json")):
        if Path(path).name.startswith("_"):
            continue
        data = json.load(io.open(path, encoding="utf-8"))
        result = (data.get("cards") or {}).get("verdict", {}).get("result", "")
        out[data["id"]] = result
    return out


def ledger_pairs():
    """(レシピID, videoId) を台帳のキー順で返す。"""
    videos = json.load(io.open(PUBLISHED, encoding="utf-8"))["videos"]
    pairs = []
    for key in sorted(videos):
        base = key[: -len("-short")] if key.endswith("-short") else key
        pairs.append((base, videos[key]["youtube_video_id"]))
    return pairs


def live_privacy(service, video_ids):
    """videos.list で今の公開状態を引く。台帳の privacy_status は投稿時の値で古い。"""
    out = {}
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i : i + 50]
        res = service.videos().list(part="status", id=",".join(chunk)).execute()
        for item in res["items"]:
            out[item["id"]] = item["status"]["privacyStatus"]
    return out


def existing_playlists(service):
    """タイトル -> {id, items: {videoId: playlistItemId}}"""
    out = {}
    res = service.playlists().list(part="snippet", mine=True, maxResults=50).execute()
    for p in res["items"]:
        pid = p["id"]
        items = {}
        token = None
        while True:
            r = (
                service.playlistItems()
                .list(
                    part="contentDetails",
                    playlistId=pid,
                    maxResults=50,
                    pageToken=token,
                )
                .execute()
            )
            for it in r["items"]:
                items[it["contentDetails"]["videoId"]] = it["id"]
            token = r.get("nextPageToken")
            if not token:
                break
        out[p["snippet"]["title"]] = {"id": pid, "items": items}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="実際に書き込む")
    args = ap.parse_args()

    service = get_service()
    verdicts = recipe_verdicts()
    pairs = ledger_pairs()
    privacy = live_privacy(service, [vid for _, vid in pairs])
    playlists = existing_playlists(service)

    # 分類 -> 入れるべき videoId の並び
    want = {name: [] for name in BUCKETS}
    skipped = []
    for base, vid in pairs:
        bucket = classify(verdicts.get(base, ""))
        status = privacy.get(vid, "?")
        if bucket is None:
            got = verdicts.get(base, "")
            skipped.append((base, vid, "判定が分類に当たらない: " + repr(got)))
            continue
        if status != "public":
            skipped.append((base, vid, "公開されていない（%s）" % status))
            continue
        want[bucket].append(vid)

    adds, removes, creates = [], [], []
    for bucket, vids in want.items():
        title = BUCKETS[bucket][0]
        pl = playlists.get(title)
        if pl is None:
            creates.append(bucket)
            adds.extend((bucket, v) for v in vids)
            continue
        for v in vids:
            if v not in pl["items"]:
                adds.append((bucket, v))
        for v, item_id in pl["items"].items():
            if v not in vids:
                removes.append((bucket, v, item_id, privacy.get(v, "台帳外")))

    print("== 作る再生リスト ==")
    for b in creates:
        print("  + " + BUCKETS[b][0])
    print("\n== 外す %d 本 ==" % len(removes))
    for b, v, _i, st in removes:
        print("  - [%s] %s  (%s)" % (b, v, st))
    print("\n== 足す %d 本 ==" % len(adds))
    for b, v in adds:
        print("  + [%s] %s" % (b, v))
    print("\n== 触らない %d 本 ==" % len(skipped))
    for base, v, why in skipped:
        print("  . %s %s: %s" % (v, base, why))

    units = (len(creates) + len(removes) + len(adds)) * 50
    print("\n消費するクォータの見込み: %d ユニット" % units)

    if not args.apply:
        print("\n（ドライラン。書き込むには --apply）")
        return 0

    for bucket in creates:
        title, desc = BUCKETS[bucket]
        res = (
            service.playlists()
            .insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": title,
                        "description": desc,
                        "defaultLanguage": "ja",
                    },
                    "status": {"privacyStatus": "public"},
                },
            )
            .execute()
        )
        playlists[title] = {"id": res["id"], "items": {}}
        print("作った: %s %s" % (title, res["id"]))

    for bucket, vid, item_id, _st in removes:
        service.playlistItems().delete(id=item_id).execute()
        print("外した: [%s] %s" % (bucket, vid))

    for bucket, vid in adds:
        pid = playlists[BUCKETS[bucket][0]]["id"]
        service.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": pid,
                    "resourceId": {"kind": "youtube#video", "videoId": vid},
                }
            },
        ).execute()
        print("足した: [%s] %s" % (bucket, vid))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
