#!/usr/bin/env python3
"""レシピの検証と概要欄の生成。

**規約担保の中核。** 権利者ガイドラインの必須条件（概要欄の冒頭に元動画URL・
タイトル）と、過去の事故（別チャンネルへの誤投稿）への対策をここで強制する。
運用の注意書きではなく、通らなければ落ちる形にしてある。

字幕はASRなので金額が崩れる。令和の虎は金額が命なので、裏取りしていない
数字を公開させないよう cards.brief.amount が空ならビルドを止める。
"""

from __future__ import annotations

REQUIRED = ("id", "source_video_id", "source_url", "source_title",
            "title", "expected_channel_id")

CREDIT = ("本チャンネルはガジェット通信クリエイターネットワークを通じて"
          "切り抜き動画の許諾を得て運営しています。")


def validate(recipe: dict) -> None:
    """不備があれば ValueError。ビルドとアップロードの前に必ず通す。"""
    for key in REQUIRED:
        if not recipe.get(key):
            raise ValueError(f"レシピに {key} が無い（必須）")

    clip = recipe.get("clip") or {}
    start, end = clip.get("start"), clip.get("end")
    if start is None or end is None or end <= start:
        raise ValueError(f"clip の範囲が不正: start={start} end={end}")

    amount = ((recipe.get("cards") or {}).get("brief") or {}).get("amount")
    if not amount:
        raise ValueError(
            "cards.brief.amount が空。字幕はASRで金額が崩れるため、"
            "映像で裏取りした金額を入れること")


def build_description(recipe: dict) -> str:
    """概要欄。冒頭の元動画URL・タイトルは手書きさせず、ここで必ず付ける。"""
    body = (recipe.get("description") or "").strip()
    tags = " ".join(f"#{t}" for t in (recipe.get("tags") or []))
    parts = [
        f"【元動画】{recipe['source_title']}",
        recipe["source_url"],
        "",
        body,
        "",
        CREDIT,
    ]
    if tags:
        parts += ["", tags]
    return "\n".join(parts).strip() + "\n"
