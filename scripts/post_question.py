#!/usr/bin/env python3
"""レシピの `question` を、その回のショートにコメントとして投稿する。

  python scripts/post_question.py recipes/<id>.json            # 出すだけ
  python scripts/post_question.py recipes/<id>.json --apply

**コメントは開設から32日で合計7件しか付いていない。** 問いかけが画面にも
概要欄にも1度も出ていないので、判定が割れる回だけ問いを1つ投げる
（docs/2026-09-10-analytics.md）。

**★ピン留めは YouTube Data API v3 に無い。** 2026-09-10 に discovery を
実測して確認した（`commentThreads` は insert/list のみ、`comments` に pin は
無く、`setModerationStatus` は保留コメントの承認用）。
**投稿したあと Studio で手でピン留めすること。**

投稿先はショート（長尺ではない）。再生の96%はショートフィードなので、
長尺に置いても誰も見ない。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.recipe import question_of, short_dirname, validate_question  # noqa: E402
from scripts.upload_youtube import PUBLISHED, current_channel, get_service  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def short_ids(recipe_id: str) -> list[str]:
    """台帳から、このレシピのショートの動画IDを集める。"""
    led = json.loads(PUBLISHED.read_text(encoding="utf-8-sig"))["videos"]
    out = []
    for i in range(4):
        entry = led.get(short_dirname(recipe_id, i))
        if entry:
            out.append(entry["youtube_video_id"])
    return out


def already_posted(service, video_id: str, channel_id: str) -> str | None:
    """自分が既に付けたトップレベルのコメントがあれば、その本文を返す。

    **二重投稿を防ぐ。** 同じ問いが2つ並ぶと、答える気が失せる。
    """
    res = service.commentThreads().list(
        part="snippet", videoId=video_id, maxResults=100,
        textFormat="plainText").execute()
    for th in res.get("items", []):
        sn = th["snippet"]["topLevelComment"]["snippet"]
        if (sn.get("authorChannelId") or {}).get("value") == channel_id:
            return sn["textOriginal"]
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("recipe", type=Path)
    ap.add_argument("--apply", action="store_true",
                    help="実際に投稿する（既定は表示のみ）")
    a = ap.parse_args()

    recipe = json.loads(a.recipe.read_text(encoding="utf-8"))
    q = question_of(recipe)
    if not q:
        raise SystemExit(
            f"! {a.recipe} に question が無い。"
            '判定が割れる回だけ "question": "あなたが虎なら出資しますか?" を足すこと')
    validate_question(q)

    ids = short_ids(recipe["id"])
    if not ids:
        raise SystemExit(f"! 台帳に {recipe['id']} のショートが無い")

    service = get_service()
    channel_id = current_channel(service)["id"]
    print(f"問い: {q}")

    # **予約公開中（private）の動画はコメント欄が無効として返る。**
    # 2026-09-10 に実測（commentsDisabled）。公開されてから投げること
    privacy = {it["id"]: it["status"]["privacyStatus"]
               for it in service.videos().list(
                   part="status", id=",".join(ids)).execute().get("items", [])}

    for vid in ids:
        url = f"https://www.youtube.com/watch?v={vid}"
        if privacy.get(vid) != "public":
            print(f"  {vid} は {privacy.get(vid)} なので飛ばす"
                  "（公開されてからもう一度実行すること）")
            continue
        prev = already_posted(service, vid, channel_id)
        if prev:
            print(f"  {vid} すでに投稿済み → {prev[:40]}")
            continue
        if not a.apply:
            print(f"  {vid} に投稿する（--apply を付けるまで何もしません）  {url}")
            continue
        service.commentThreads().insert(
            part="snippet",
            body={"snippet": {"videoId": vid,
                              "topLevelComment": {
                                  "snippet": {"textOriginal": q}}}}).execute()
        got = already_posted(service, vid, channel_id)
        if got != q:
            raise SystemExit(f"! {vid} に投稿したが読み直せない（{got!r}）")
        print(f"  ✓ {vid} に投稿した  {url}")
        print("    ★Studio で手でピン留めすること（API にピン留めは無い）")


if __name__ == "__main__":
    main()
