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

# **狙う窓。2026-09-10 に 65〜73秒から下げた。**
# 公開済み19本を Analytics で測ったところ（docs/2026-09-10-analytics.md）:
#
#   実視聴秒   中央値 39.5秒（31.9〜54.0）。**尺との相関 -0.02＝完全に無関係**
#   尺 × 平均視聴率   -0.53
#   65秒以下 n=7 の平均視聴率 中央値 66.7% / 68秒以上 n=6 は 54.3%
#
# **尺を伸ばしても見られる秒数は増えず、分母だけが増える。**
# 70秒で作ると40秒しか見られず57%、55秒で作れば同じ40秒で73%になる。
# 平均視聴率はショートフィードの配信量に効く（再生数との相関 +0.49）ので、
# 同じ素材・同じ手間で結果が変わる。
SHORT_TARGET_MIN = 50.0
SHORT_TARGET_MAX = 58.0

# ここを割ると、令和の虎の「問い→答え」が1往復も入らない。
#
# **2026-09-10 に 65.0 から 45.0 に下げた。** 65秒は TikTok Creator Rewards の
# 「1分以上」に合わせた値（2026-08-30）だったが、TikTok のアカウントはまだ
# 作られておらず（state/tiktok.json は空）、**存在しないアカウントの将来の
# 収益化のために、実測で効いている YouTube の平均視聴率を捨てていた。**
# TikTok を始めるときは、同じ区間の end を伸ばした別ビルドにすること。
SHORT_MIN_SEC = 45.0

SHORT_RECOMMENDED_SEC = SHORT_TARGET_MAX


def shorts_of(recipe: dict) -> list[dict]:
    """このレシピのショートの一覧。

    **1本の長尺につきショートは2本要る**（docs/daily-workflow.md）。
    ショート2本目は親の長尺が公開済みのものから出すので、同じレシピに
    2区間を書いておく。`shorts`（複数）があればそれを、無ければ従来どおり
    `short`（単数）を1本だけ返す。既存レシピはそのまま動く。
    """
    shorts = recipe.get("shorts")
    if shorts:
        return list(shorts)
    short = recipe.get("short")
    return [short] if short else []


# 論点カード（図解）を出す狙いの秒。実測（n=19）で3秒地点の残存は全19本が
# 113%以上あり、差がつくのは7〜10秒地点（上位88〜98% / 下位74〜76%）。
# **落ち始めるところに2つ目の情報を出す**（docs/2026-09-10-analytics.md）
SHORT_POINT_WINDOW = (7.0, 10.0)


def points_of(short_or_recipe: dict, index: int = 0) -> list[dict]:
    """ショートに焼く論点カードの一覧。無ければ空。

    **既定では入らない（opt-in）。** 尺を50〜58秒にする施策と同時に入れると、
    どちらが効いたのか分からなくなる。**尺の答え合わせが済むまで使わないこと。**
    """
    shorts = shorts_of(short_or_recipe)
    short = shorts[index] if index < len(shorts) else short_or_recipe
    return list(short.get("points") or [])


def short_dirname(recipe_id: str, index: int) -> str:
    """work/ の出力先。1本目は従来どおり -short（既存の台帳と揃える）。"""
    return f"{recipe_id}-short" if index == 0 else f"{recipe_id}-short{index + 1}"


def validate_short(recipe: dict, cues: list[dict] | None = None,
                   index: int = 0) -> list[str]:
    """ショートの区間を検証する。長尺と同じレシピから作るので共通項目は validate に任せる。

    cues（元動画の字幕）を渡すと、**実際にビルドされる区間**で検証する。
    開始点は build_short が話題の頭まで巻き戻すので、レシピの start より
    手前から始まる。尺の判定はその巻き戻し後の長さで行う。

    落とすべきでない指摘は警告の一覧として返す。
    """
    shorts = shorts_of(recipe)
    if not shorts:
        raise ValueError("レシピに short がない。ショートを作るには short が要る")
    if index >= len(shorts):
        raise ValueError(
            f"short の {index + 1} 本目が無い（このレシピには {len(shorts)} 本）")
    short = shorts[index]

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

    length = end - start
    if length < SHORT_MIN_SEC:
        raise ValueError(
            f"short が {length:.1f}秒。これでは問いと答えが1往復も入らないので "
            f"{SHORT_MIN_SEC:.0f}秒を下限にしている")
    if length > SHORT_MAX_SEC:
        raise ValueError(
            f"short が {length:.0f}秒。Shorts の上限 {SHORT_MAX_SEC:.0f}秒を超えている")
    if length > SHORT_TARGET_MAX:
        # **落とさない。** 尺は素材で決まることもあるし、既存レシピを
        # ビルドし直せなくなる。ただし黙って通すと、実視聴秒が増えないまま
        # 平均視聴率だけが下がる本がまた出る
        warnings.append(
            f"short が {length:.0f}秒。狙う窓は "
            f"{SHORT_TARGET_MIN:.0f}〜{SHORT_TARGET_MAX:.0f}秒。実視聴秒は "
            f"尺に関係なく中央値39.5秒なので、超えたぶんは完走されにくい")
    elif length < SHORT_TARGET_MIN:
        warnings.append(
            f"short が {length:.0f}秒。狙う窓は "
            f"{SHORT_TARGET_MIN:.0f}〜{SHORT_TARGET_MAX:.0f}秒より短い")

    warnings += _validate_points(points_of(recipe, index), length)
    return warnings


def _validate_points(points: list[dict], length: float) -> list[str]:
    """論点カードの位置を検証する。at はショートの先頭からの秒。"""
    warnings = []
    spans = []
    for i, p in enumerate(points, 1):
        if not (p.get("text") or "").strip():
            raise ValueError(f"short.points の {i} 枚目の text が空")
        at = float(p.get("at", 0.0))
        sec = float(p.get("sec", 0.0))
        if sec <= 0:
            raise ValueError(f"short.points の {i} 枚目の sec が {sec}")
        if at < 0 or at + sec > length:
            raise ValueError(
                f"short.points の {i} 枚目（{at:.1f}〜{at + sec:.1f}秒）が "
                f"{length:.1f}秒の区間からはみ出している")
        spans.append((at, at + sec, i))

    for a in range(len(spans)):
        for b in range(a + 1, len(spans)):
            if spans[a][0] < spans[b][1] and spans[b][0] < spans[a][1]:
                raise ValueError(
                    f"short.points の {spans[a][2]} 枚目と {spans[b][2]} 枚目が"
                    "重なっている")

    lo, hi = SHORT_POINT_WINDOW
    if points and not any(lo <= float(p.get("at", 0.0)) <= hi for p in points):
        warnings.append(
            f"short.points が1枚も {lo:.0f}〜{hi:.0f}秒に無い。"
            "実測で残存が落ち始めるのはこの帯なので、1枚目はここに置くこと")
    return warnings


# 固定コメントの問い。
#
# **コメントは開設から32日で合計7件。** 問いかけが画面にも概要欄にも
# 1度も出ていない（docs/2026-09-10-analytics.md）。
#
# **ピン留めは YouTube Data API v3 に無い**（2026-09-10 に discovery を実測。
# commentThreads は insert/list のみ、comments に pin は無い）。
# 投稿までを自動化し、ピン留めは Studio で手でやる。
QUESTION_MAX = 200
QUESTION_MARKS = ("?", "？")


def question_of(recipe: dict) -> str | None:
    """固定コメントに投げる問い。無ければ None。"""
    q = (recipe.get("question") or "").strip()
    return q or None


def validate_question(question: str) -> None:
    """問いとして成立しているかを見る。**呼びかけではコメントは増えない。**"""
    q = (question or "").strip()
    if not q:
        raise ValueError("question が空")
    if len(q) > QUESTION_MAX:
        raise ValueError(
            f"question が {len(q)}文字。{QUESTION_MAX}文字を超えると長すぎる")
    if "http://" in q or "https://" in q:
        raise ValueError(
            "question に URL が入っている。自分のコメントにリンクを貼ると"
            "スパム判定される")
    if not any(m in q for m in QUESTION_MARKS):
        raise ValueError(
            "question に疑問符が無い。「今日も見てね」のような呼びかけでは"
            "問いにならないので、答えられる形にすること")


def _source_lines(recipe: dict) -> list[str]:
    """元動画のタイトルとURL。**概要欄にもキャプションにも必ず入れる。**

    権利者ガイドラインの必須条件なので、書き手に任せず1箇所で作る。
    """
    return [f"【元動画】{recipe['source_title']}", recipe["source_url"]]


def build_description(recipe: dict) -> str:
    """概要欄。冒頭の元動画URL・タイトルは手書きさせず、ここで必ず付ける。"""
    body = (recipe.get("description") or "").strip()
    tags = " ".join(f"#{t}" for t in (recipe.get("tags") or []))
    parts = [*_source_lines(recipe), "", body, "", CREDIT]
    if tags:
        parts += ["", tags]
    return "\n".join(parts).strip() + "\n"


def build_caption(recipe: dict, index: int = 0) -> str:
    """TikTok へ手で投稿するときに貼り付けるテキスト。

    **概要欄（build_description）は YouTube 用の長文なので使わない。**
    TikTok の URL はリンクにならないが、元動画へのリンクは権利者ガイドラインの
    必須条件なので、意図として必ず書く。
    """
    shorts = shorts_of(recipe)
    short = shorts[index] if index < len(shorts) else {}
    head = (short.get("title") or short.get("hook") or recipe["title"]).strip()
    tags = " ".join(f"#{t}" for t in (recipe.get("tags") or []))
    parts = [head, "", *_source_lines(recipe), "", CREDIT]
    if tags:
        parts += ["", tags]
    return "\n".join(parts).strip() + "\n"
