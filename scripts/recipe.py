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

# 「許諾を得て運営」とは書かない。権利者は「あくまでご本人は黙認」という扱いで、
# ガイドラインでも「公認」「公式」表記を禁じている（2026-08-09 の受付メールで確認）。
# 申請済みという事実だけを書く。
CREDIT = ("本チャンネルはガジェット通信クリエイターネットワークに"
          "申請済みの切り抜きチャンネルです。公式チャンネルではありません。")

# 出演者の名誉・信用を害する表記は禁止されている。タイトル生成時の下限ガード
BANNED_IN_TITLE = ("公式", "公認", "マネーの虎")


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

    # ガイドラインで「公認」「公式」表記と「マネーの虎」を想起させる表現が禁止
    title = recipe["title"]
    hit = next((w for w in BANNED_IN_TITLE if w in title), None)
    if hit:
        raise ValueError(
            f"タイトルに「{hit}」が入っている。ガイドラインで禁止されている表現")


SHORT_MAX_SEC = 180.0     # Shorts として扱われる上限（YouTube の仕様）

# 実際に伸びている競合の尺（2026-08-13 実測）。令和の虎塾のショートは67〜73秒で
# 公開1〜4日に3,925〜28,477再生、【忙しい人のための】は22〜37秒。
# こちらの103秒・132秒は0〜2再生だった。上限180秒に収まっていても長すぎる。
# 落とすほどではないので警告にとどめる（尺は素材で決まることもある）
SHORT_RECOMMENDED_SEC = 75.0


def validate_short(recipe: dict, cues: list[dict] | None = None) -> list[str]:
    """ショートの区間を検証する。長尺と同じレシピから作るので共通項目は validate に任せる。

    cues（元動画の字幕）を渡すと、**実際にビルドされる区間**で検証する。
    開始点は build_short が話題の頭まで巻き戻すので、レシピの start より
    手前から始まる。尺の判定はその巻き戻し後の長さで行う。

    落とすべきでない指摘は警告の一覧として返す。
    """
    short = recipe.get("short")
    if not short:
        raise ValueError("レシピに short がない。ショートを作るには short が要る")

    start, end = short.get("start"), short.get("end")
    if start is None or end is None or end <= start:
        raise ValueError(f"short.clip の範囲が不正: start={start} end={end}")

    if not (short.get("hook") or "").strip():
        raise ValueError(
            "short.hook が空。縦型は冒頭2秒で離脱が決まるので、"
            "フック無しで出す意味がない")

    warnings = []
    if cues is not None:
        from scripts.moments import rewind_to_topic_head

        landed = rewind_to_topic_head(start, cues)
        if landed["start"] < start:
            warnings.append(
                f"開始が発話の途中だったので {start:.1f} → {landed['start']:.1f} まで"
                f"巻き戻した [{landed['kind']}] {landed['line'][:36]}")
        start = landed["start"]

        # **字幕が焼けない区間は出さない。** 何を言っているか分からない切り抜きに
        # なる。「切り抜き方が下手でどういう意味なのか全くわからない」（2026-08-22）
        if not any(start <= c["t"] < end for c in cues):
            raise ValueError(
                f"short の区間（{start:.1f}-{end:.1f}）に字幕が1つも無い。"
                "字幕を焼けないショートは意味が伝わらない")

    if end - start > SHORT_MAX_SEC:
        raise ValueError(
            f"short が {end - start:.0f}秒。Shorts の上限 {SHORT_MAX_SEC:.0f}秒を超えている")
    if end - start > SHORT_RECOMMENDED_SEC:
        warnings.append(
            f"short が {end - start:.0f}秒。伸びている競合は22〜73秒で、"
            f"{SHORT_RECOMMENDED_SEC:.0f}秒を超えると完走されにくい")
    return warnings


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
