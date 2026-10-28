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
    validate_cta(recipe)
    validate_long_format(recipe)
    validate_experiment(recipe)


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

# ---------------------------------------------------------------------------
# 2026-10-29〜11-11 の形式実験（docs/experiments-ledger.md）。**既定は従来どおり**
# （format 無し＝standard。45〜180秒の検証・50〜58秒の窓・長尺の尺は検証しない）。
#
#   short.format = "kazuzure"  数字ズレ型。10〜15秒を狙い、**8〜20秒だけ通す**
#   recipe.format = "matome"   図解まとめ（長尺）。**6〜9分（360〜540秒）だけ通す**
#
# 数字ズレ型は区間が短いので、締めの帯（既定4秒）も短くする（SHORT_CTA_SEC_BY_FORMAT）。
# 台詞が解決する最後の数秒を上帯で隠さないため。下帯の字幕は元から覆わない。
# ---------------------------------------------------------------------------
SHORT_FORMATS = {
    # 名前: (下限, 上限, 狙う窓の下限, 狙う窓の上限)
    "standard": (SHORT_MIN_SEC, SHORT_MAX_SEC, SHORT_TARGET_MIN, SHORT_TARGET_MAX),
    "kazuzure": (8.0, 20.0, 10.0, 15.0),
}
SHORT_CTA_SEC_BY_FORMAT = {"standard": 4.0, "kazuzure": 3.0}
# 数字ズレ型の title は「【数字ズレ#N】…」。秒数は入れない
KAZUZURE_TITLE_RE = r"^【数字ズレ#(\d+)】"
KAZUZURE_SECONDS_RE = r"\d+\s*(?:秒|s\b)"

LONG_FORMATS = {
    # 名前: (下限, 上限)  None は検証しない（従来の長尺）
    "standard": None,
    "matome": (360.0, 540.0),
}
# 従来の長尺の狙い（13〜20分）。実験中に standard 側が外れたら警告するだけ
LONG_STANDARD_TARGET = (780.0, 1200.0)

# 実験の変種。D（締めの文言）は偶数 n で「判定は本編で」、奇数 n は従来の問い。
# C（長尺）は奇数 n が matome、偶数 n が standard
ENDING_HANTEI = "判定は本編で"
EXPERIMENT_SHORT_VARIANTS = ("kazuzure", "fallback")
EXPERIMENT_ENDINGS = ("question", "hantei")
EXPERIMENT_LONGS = ("matome", "standard")


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


def short_format(recipe: dict, index: int = 0) -> str:
    """そのショートの形式。`shorts[i].format` → `short_format`（レシピ直下）→ standard。"""
    shorts = shorts_of(recipe)
    short = shorts[index] if index < len(shorts) else {}
    fmt = (short.get("format") or recipe.get("short_format") or "standard")
    if fmt not in SHORT_FORMATS:
        raise ValueError(
            f"short.format が不明: {fmt}（{'/'.join(SHORT_FORMATS)} のどれか）")
    return fmt


def long_format(recipe: dict) -> str:
    """長尺の形式。`format`（レシピ直下）。無ければ standard（従来どおり）。"""
    fmt = recipe.get("format") or "standard"
    if fmt not in LONG_FORMATS:
        raise ValueError(
            f"format が不明: {fmt}（{'/'.join(LONG_FORMATS)} のどれか）")
    return fmt


def short_cta_sec(recipe: dict, index: int = 0) -> float:
    """ショート締めの帯の秒数。`shorts[i].cta_sec` → 形式の既定（standard 4秒 / kazuzure 3秒）。"""
    shorts = shorts_of(recipe)
    short = shorts[index] if index < len(shorts) else {}
    sec = short.get("cta_sec")
    if sec is None:
        return SHORT_CTA_SEC_BY_FORMAT[short_format(recipe, index)]
    sec = float(sec)
    if not (1.0 <= sec <= 6.0):
        raise ValueError(f"short.cta_sec が {sec}。1〜6秒の範囲にすること")
    return sec


ENDING_TEXT_MAX = 30


def ending_text_of(recipe: dict, index: int = 0) -> str | None:
    """問いの代わりに締めの帯へ出す一言（D: 偶数 n の「判定は本編で」）。無ければ None。

    `shorts[i].ending_text` → `ending_text`（レシピ直下）→ experiment.variant.ending
    が "hantei" のとき ENDING_HANTEI。**問いではないので「理由もコメントで」は足さない。**
    概要欄の1行目は別（comment_prompt）で、ここは影響しない。
    """
    shorts = shorts_of(recipe)
    short = shorts[index] if index < len(shorts) else {}
    t = (short.get("ending_text") or recipe.get("ending_text") or "").strip()
    if t:
        return t
    variant = ((recipe.get("experiment") or {}).get("variant") or {})
    return ENDING_HANTEI if variant.get("ending") == "hantei" else None


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

    fmt = short_format(recipe, index)
    min_sec, max_sec, tgt_min, tgt_max = SHORT_FORMATS[fmt]

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
    if fmt == "standard":
        if length < min_sec:
            raise ValueError(
                f"short が {length:.1f}秒。これでは問いと答えが1往復も入らないので "
                f"{min_sec:.0f}秒を下限にしている")
        if length > max_sec:
            raise ValueError(
                f"short が {length:.0f}秒。Shorts の上限 {max_sec:.0f}秒を超えている")
    elif not (min_sec <= length <= max_sec):
        raise ValueError(
            f"short（{fmt}）が {length:.1f}秒。この形式は {min_sec:.0f}〜{max_sec:.0f}秒"
            f"（狙いは {tgt_min:.0f}〜{tgt_max:.0f}秒）だけ通す。"
            "巻き戻し後の長さで測っている")
    _validate_short_title(recipe, short, fmt)
    if fmt != "standard":
        if length < tgt_min or length > tgt_max:
            warnings.append(
                f"short（{fmt}）が {length:.1f}秒。狙う窓は {tgt_min:.0f}〜{tgt_max:.0f}秒")
    elif length > SHORT_TARGET_MAX:
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

    warnings += _validate_points(points_of(recipe, index), length,
                                 check_window=(fmt == "standard"))
    return warnings


def _validate_short_title(recipe: dict, short: dict, fmt: str) -> None:
    """ショートのタイトルを検証する。

    **従来は recipe["title"]（長尺）しか禁止語を見ていなかった。** ショートは
    short.title（無ければ hook）が実際のタイトルになるので、同じ禁止語を見る。
    kazuzure は「【数字ズレ#N】…」で、N は experiment.series_no と一致させ、
    秒数は入れない。
    """
    title = (short.get("title") or short.get("hook") or "").strip()
    hit = next((w for w in BANNED_IN_TITLE if w in title), None)
    if hit:
        raise ValueError(
            f"ショートのタイトルに「{hit}」が入っている。ガイドラインで禁止されている表現")
    if fmt != "kazuzure":
        return
    import re

    if len(title) > 100:
        raise ValueError(f"ショートのタイトルが {len(title)}文字。100文字を超えると切れる")
    m = re.match(KAZUZURE_TITLE_RE, title)
    if not m:
        raise ValueError(
            "short.title が「【数字ズレ#N】<出演者名や題材＋何が起きたか>」の形でない: "
            f"{title!r}")
    if title[m.end():].strip() == "":
        raise ValueError("short.title に【数字ズレ#N】のあとの本文（題材と何が起きたか）が無い")
    if re.search(KAZUZURE_SECONDS_RE, title):
        raise ValueError(f"short.title に秒数を入れない: {title!r}")
    series = (recipe.get("experiment") or {}).get("series_no")
    if series is not None and int(m.group(1)) != int(series):
        raise ValueError(
            f"short.title の #{m.group(1)} が experiment.series_no={series} と合わない")


def _validate_points(points: list[dict], length: float,
                     check_window: bool = True) -> list[str]:
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
    if (check_window and points
            and not any(lo <= float(p.get("at", 0.0)) <= hi for p in points)):
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


# 視聴者参加の導線（docs/engagement.md、2026-10-15 承認の常設方針）。
#
# 問いは「自分ならどうするか」の型にする。**呼びかけ（見てね・登録してね）だけ
# ではコメントは増えない。** 答えられる問いを画面と概要欄の1行目に出す。
# レシピに cta_question が無い旧レシピでも動くよう、タイトル等から既定を作る。
CTA_END_DEFAULT = "あなたならどうする？コメントで／学びになったら高評価・チャンネル登録を"
CTA_COMMENT_TAIL = "理由もコメントで"
# 有償・見返り付きの依頼は方針で禁止。「公式」「公認」はガイドラインで禁止
CTA_BANNED = ("公式", "公認", "マネーの虎", "プレゼント", "抽選", "謝礼",
              "相互登録", "登録してくれた方", "高評価してくれた方")


def cta_enabled(recipe: dict) -> bool:
    """"cta": false で無効にできる。既定は有効。"""
    return recipe.get("cta", True) is not False


def cta_question(recipe: dict) -> str:
    """その回の問い（核）。cta_question → question → タイトル等から既定。"""
    q = (recipe.get("cta_question") or recipe.get("question") or "").strip()
    if q:
        return q
    cards = recipe.get("cards") or {}
    text = " ".join([
        recipe.get("title") or "",
        (cards.get("brief") or {}).get("amount") or "",
        (cards.get("verdict") or {}).get("result") or ""])
    # 社長ファイトクラブ版などは金額ではなく「支援」を判定する
    if "支援" in text or "ファイトクラブ" in text or "社長FC" in text:
        return "あなたが虎なら支援する？しない？"
    return "あなたが虎なら出資する？しない？"


def _first_clause(q: str) -> str:
    """「出資する？しない？」→「出資する？」。最初の疑問符まで。"""
    for i, ch in enumerate(q):
        if ch in QUESTION_MARKS:
            return q[:i + 1]
    return q


def comment_prompt(recipe: dict, question: str | None = None) -> str:
    """問い＋「理由もコメントで」。問い自体がコメントを求めていれば足さない。"""
    q = (question or cta_question(recipe)).strip()
    return q if "コメント" in q else q + CTA_COMMENT_TAIL


def cta_start_text(recipe: dict) -> str:
    """長尺の冒頭テロップ。例「あなたが虎なら出資する？最後に答えを聞きます」"""
    t = (recipe.get("cta_start") or "").strip()
    return t or _first_clause(cta_question(recipe)) + "最後に答えを聞きます"


def cta_end_text(recipe: dict) -> str:
    """長尺の終盤テロップ。「／」で2行に分ける。"""
    return (recipe.get("cta_end") or "").strip() or CTA_END_DEFAULT


def short_cta_text(recipe: dict, index: int = 0) -> str:
    """ショートの締めの1行。shorts[i].cta_question があればそれを使う。

    ending_text（D の「判定は本編で」）があれば問いの代わりにそれを出す。
    """
    ending = ending_text_of(recipe, index)
    if ending:
        return ending
    shorts = shorts_of(recipe)
    short = shorts[index] if index < len(shorts) else {}
    q = (short.get("cta_question") or "").strip()
    return comment_prompt(recipe, q or None)


def validate_cta(recipe: dict) -> None:
    """画面と概要欄に出す問いの禁止語を落とす。"""
    if not cta_enabled(recipe):
        return
    texts = [cta_question(recipe), cta_start_text(recipe), cta_end_text(recipe)]
    texts += [short_cta_text(recipe, i) for i in range(len(shorts_of(recipe)))]
    for i in range(len(shorts_of(recipe))):
        e = ending_text_of(recipe, i)
        if e and len(e) > ENDING_TEXT_MAX:
            raise ValueError(f"ending_text が {len(e)}文字。{ENDING_TEXT_MAX}文字以内にすること")
    for t in texts:
        hit = next((w for w in CTA_BANNED if w in t), None)
        if hit:
            raise ValueError(f"問いかけに「{hit}」が入っている（docs/engagement.md で禁止）: {t}")
        if "http://" in t or "https://" in t:
            raise ValueError(f"問いかけに URL を入れない: {t}")


def long_length_warnings(recipe: dict) -> list[str]:
    """長尺の尺の警告（落とさない）。standard は実験中だけ 13〜20分を外れたら知らせる。"""
    clip = recipe.get("clip") or {}
    length = float(clip.get("end", 0)) - float(clip.get("start", 0))
    if recipe.get("experiment") and long_format(recipe) == "standard":
        lo, hi = LONG_STANDARD_TARGET
        if not (lo <= length <= hi):
            return [f"長尺（standard）が {length / 60:.1f}分。従来の 13〜20分から外れている"
                    "（実験の偶数 n は従来の長尺で比べる）"]
    return []


def validate_long_format(recipe: dict) -> None:
    """format: "matome" の長尺は 6〜9分（clip の長さ。build_clip は巻き戻さないので確定値）。"""
    fmt = long_format(recipe)
    rng = LONG_FORMATS[fmt]
    if rng is None:
        return
    clip = recipe["clip"]
    length = float(clip["end"]) - float(clip["start"])
    if not (rng[0] <= length <= rng[1]):
        raise ValueError(
            f"長尺（{fmt}）が {length:.0f}秒（{length / 60:.1f}分）。"
            f"この形式は {rng[0] / 60:.0f}〜{rng[1] / 60:.0f}分だけ通す")


EXPERIMENT_START = "2026-10-29"


def validate_experiment(recipe: dict) -> None:
    """experiment ブロック（docs/experiments-ledger.md）の整合を見る。無ければ何もしない。

    experiment = {"id": ..., "n": 0〜13, "series_no": 1〜, "date": "YYYY-MM-DD"(任意),
                  "variant": {"short": kazuzure|fallback,
                              "ending": question|hantei, "long": matome|standard}}
    **偶数 n は ending=hantei・long=standard、奇数 n は ending=question・long=matome。**
    プラン E（同じ回から2本のショート）は却下済みなので、ショートは1本だけ。
    """
    exp = recipe.get("experiment")
    if not exp:
        return
    for key in ("id", "n", "series_no", "variant"):
        if exp.get(key) in (None, ""):
            raise ValueError(f"experiment.{key} が無い")
    n, series = exp["n"], exp["series_no"]
    if not isinstance(n, int) or isinstance(n, bool) or n < 0:
        raise ValueError(f"experiment.n が不正: {n!r}（0以上の整数）")
    if not isinstance(series, int) or isinstance(series, bool) or series < 1:
        raise ValueError(f"experiment.series_no が不正: {series!r}（1以上の整数）")
    if exp.get("date"):
        from datetime import date

        d0 = date.fromisoformat(EXPERIMENT_START)
        if (date.fromisoformat(exp["date"]) - d0).days != n:
            raise ValueError(
                f"experiment.n={n} が date={exp['date']} と合わない"
                f"（n = {EXPERIMENT_START} からの日数）")
    v = exp["variant"]
    if v.get("short") not in EXPERIMENT_SHORT_VARIANTS:
        raise ValueError(f"experiment.variant.short が不正: {v.get('short')!r}")
    if v.get("ending") not in EXPERIMENT_ENDINGS:
        raise ValueError(f"experiment.variant.ending が不正: {v.get('ending')!r}")
    if v.get("long") not in EXPERIMENT_LONGS:
        raise ValueError(f"experiment.variant.long が不正: {v.get('long')!r}")

    even = n % 2 == 0
    if (v["ending"] == "hantei") != even:
        raise ValueError(
            f"n={n}（{'偶' if even else '奇'}数）の締めは "
            f"{'hantei（判定は本編で）' if even else 'question（従来の問い）'} にすること")
    if (v["long"] == "matome") == even:
        raise ValueError(
            f"n={n}（{'偶' if even else '奇'}数）の長尺は "
            f"{'standard（13〜20分）' if even else 'matome（6〜9分）'} にすること")

    shorts = shorts_of(recipe)
    if len(shorts) != 1:
        raise ValueError(
            f"experiment 中のショートは1本だけ（いま {len(shorts)}本）。"
            "プラン E（同じ回から2本）は却下済み")
    want = "kazuzure" if v["short"] == "kazuzure" else "standard"
    if short_format(recipe, 0) != want:
        raise ValueError(
            f"variant.short={v['short']} なのに short.format が {short_format(recipe, 0)}")
    if long_format(recipe) != ("matome" if v["long"] == "matome" else "standard"):
        raise ValueError(
            f"variant.long={v['long']} なのに format が {long_format(recipe)}")
    if not cta_enabled(recipe):
        raise ValueError("experiment 中は cta:false にしない（概要欄1行目の問いが要る）")
    ending = ending_text_of(recipe, 0)
    if v["ending"] == "hantei" and ending != ENDING_HANTEI:
        raise ValueError(f"締めは「{ENDING_HANTEI}」にすること（ending_text={ending!r}）")
    if v["ending"] == "question" and ending:
        raise ValueError("奇数 n は従来の問い。ending_text を入れない")
    validate_short(recipe, None, 0)


def _source_lines(recipe: dict) -> list[str]:
    """元動画のタイトルとURL。**概要欄にもキャプションにも必ず入れる。**

    権利者ガイドラインの必須条件なので、書き手に任せず1箇所で作る。
    """
    return [f"【元動画】{recipe['source_title']}", recipe["source_url"]]


def build_description(recipe: dict) -> str:
    """概要欄。冒頭の元動画URL・タイトルは手書きさせず、ここで必ず付ける。"""
    body = (recipe.get("description") or "").strip()
    tags = " ".join(f"#{t}" for t in (recipe.get("tags") or []))
    # **1行目は問い**（docs/engagement.md）。元動画のタイトル・URL はその直下
    # （2〜3行目）に置き、折りたたまずに見える範囲に残す
    head = [comment_prompt(recipe)] if cta_enabled(recipe) else []
    parts = [*head, *_source_lines(recipe), "", body, "", CREDIT]
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
