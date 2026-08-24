#!/usr/bin/env python3
"""4信号を合成して切り抜き候補を出す。

実データで見ると信号の性質がまるで違う。

  音量      量は多いがノイズも多い。最大スパイクが笑いの場面だったりする
  詰め語彙  虎が詰めている箇所を直接指す
  コメント  件数は少ないが精度が高い（「31:50 その態度なんなん？」など）
  金額語彙  盛り上がりではなく**構造**を示す。案件カードの材料になる

なので単純加算にしない。**音量と詰め語彙が同時に立つ箇所**を持ち上げる。
どちらか片方だけなら、笑い声か単なる言い回しの可能性が残る。
"""

from __future__ import annotations

W_LOUD = 0.35
W_COMMENT = 0.30          # 1件でも効くようにする。精度が高いので
W_HEATMAP = 0.40
W_LEX = {"詰め": 0.30, "判定": 0.25, "金額": 0.08}

COMBO_WINDOW = 10.0       # 音量と詰め語彙が何秒以内なら同時とみなすか
COMBO_BONUS = 0.35
COMBO_LOUD_MIN = 0.45     # これ未満の音量は「張られた声」とみなさない

SPREAD = 8                # 各信号を前後何秒までなだらかに効かせるか


def _add(grid: dict[int, float], t: int, v: float, duration: int) -> None:
    """点ではなく前後に広げて足す。字幕とコメントの秒がずれても拾えるように。"""
    for d in range(-SPREAD, SPREAD + 1):
        k = t + d
        if 0 <= k <= duration:
            grid[k] = grid.get(k, 0.0) + v * (1 - abs(d) / (SPREAD + 1))


# **切り出す場所は判定だけではない。** 8本を実測したところ全部が動画の
# 平均79%地点＝判定パートからの切り出しで、うち6本が完全ALLの成功譚だった。
# 一方この市場で伸びているのは「虎がブチギレた回」「激詰め」——中盤の対立。
# 詰めどころを狙いたいときに語彙の重みを持ち上げられるようにしておく
PREFER_BOOST = 3.0


def score_grid(signals: dict, duration: int, prefer: str | None = None) -> dict[int, float]:
    """秒ごとのスコアを返す。値が無い秒はキーごと持たない。

    prefer に語彙の種類（詰め／判定／金額）を渡すと、その語彙の重みを上げる。
    """
    w_lex = dict(W_LEX)
    if prefer in w_lex:
        w_lex[prefer] *= PREFER_BOOST

    grid: dict[int, float] = {}

    loud_at: dict[int, float] = {}
    for e in signals.get("loudness") or []:
        t = int(e["t"])
        loud_at[t] = max(loud_at.get(t, 0.0), float(e["score"]))
        if e["score"] > 0:
            _add(grid, t, float(e["score"]) * W_LOUD, duration)

    hard_at: set[int] = set()
    for m in signals.get("lexical") or []:
        w = w_lex.get(m["kind"], 0.0)
        if w:
            _add(grid, int(m["seconds"]), w, duration)
        if m["kind"] in ("詰め", "判定"):
            hard_at.add(int(m["seconds"]))

    for m in signals.get("comment_marks") or []:
        _add(grid, int(m["seconds"]), W_COMMENT * min(m.get("count", 1), 3), duration)

    for h in signals.get("heatmap") or []:
        mid = int((h["start"] + h["end"]) / 2)
        _add(grid, mid, float(h["score"]) * W_HEATMAP, duration)

    # 音量と詰め語彙が近接したところを持ち上げる
    for t, lv in loud_at.items():
        if lv < COMBO_LOUD_MIN:
            continue
        if any(abs(t - h) <= COMBO_WINDOW for h in hard_at):
            _add(grid, t, COMBO_BONUS * lv, duration)

    return grid


def snap_to_cues(start: float, end: float, cues: list[dict]) -> tuple[float, float]:
    """区間の端を最寄りの字幕キュー境界に寄せる。文の途中で切らないため。"""
    if not cues:
        return start, end
    times = [c["t"] for c in cues]
    nearest = lambda x: min(times, key=lambda t: abs(t - x))  # noqa: E731
    return nearest(start), nearest(end)


def signal_counts(signals: dict, start: float, end: float) -> dict[str, int]:
    """区間に入っている信号の内訳。**判定パートか詰めパートかを見分けるため。**

    スコアだけでは、虎が詰めている区間なのか出資判定の区間なのかが分からない。
    どちらを切るかで動画の性格が変わるので、選ぶ前に内訳を見せる。
    """
    counts = {k: 0 for k in W_LEX}
    for m in signals.get("lexical") or []:
        if start <= m["seconds"] <= end and m["kind"] in counts:
            counts[m["kind"]] += 1
    counts["コメント"] = sum(
        m.get("count", 1) for m in (signals.get("comment_marks") or [])
        if start <= m["seconds"] <= end)
    return counts


def find_candidates(signals: dict, cues: list[dict], duration: int,
                    count: int = 5, length: float = 420.0,
                    prefer: str | None = None,
                    exclude: list[tuple[float, float]] | None = None) -> list[dict]:
    """スコアの積分が大きい区間を、重ならないように上から取る。

    ヒートマップが無くても動く。令和の虎Second では30本中23本で
    ヒートマップが存在しないため、ここが動かないと大半の動画で候補ゼロになる。

    exclude に区間を渡すと、そこに1秒でもかかる候補を落とす。**同じ配信から
    2本目を切るときに使う。** 初期の8本は既定420秒で切っていたので、1本あたり
    3〜7分しか使っておらず、同じ回に25〜60分の未使用が残っている。
    """
    grid = score_grid(signals, duration, prefer)
    if not grid:
        return []

    half = int(length / 2)
    windows = []
    for center in range(half, max(half + 1, duration - half), 5):
        total = sum(grid.get(t, 0.0) for t in range(center - half, center + half))
        windows.append((total, center))
    windows.sort(key=lambda x: -x[0])

    picked: list[dict] = []
    for total, center in windows:
        if total <= 0:
            break
        start, end = snap_to_cues(max(0.0, center - length / 2),
                                  min(float(duration), center + length / 2), cues)
        if end <= start:
            continue
        if any(start < p["end"] and p["start"] < end for p in picked):
            continue
        if any(start < ex_end and ex_start < end for ex_start, ex_end in (exclude or [])):
            continue
        picked.append({
            "start": start, "end": end, "score": round(total, 3),
            "signals": signal_counts(signals, start, end),
            "subtitles": [c["line"] for c in cues if start <= c["t"] <= end],
        })
        if len(picked) >= count:
            break
    return picked


# 巻き戻し。**信号のピークで切ると「山の頂上」に着地する。** 頂上には
# そこへ至る登り（前提）が入っていない。実測で、投稿済み19本のうち18本が
# 発話の途中から始まっていた（最大 +18.4秒）。
#
# 例（2026-08-19-akutsu-gyutan / short.start=2275.0）:
#   2264.44 ちょっとある推理していいですか?僕   ← 前提の頭。カットの外
#   2267.52 その悪さんが今日全然元気なくプラス   ← 根拠。カットの外
#   2272.96 結構マイナスになることばっか…       ← 根拠。カットの外
#   2275.00 ← ここから切っていた
#   2275.96 で、なんでかって言うと               ← 結論の接続詞から始まる
REWIND_MAX_BACK = 15.0
SENTENCE_END = ("。", "．", ".", "？", "?", "！", "!")

# ASRは相槌と1文字を独立したキューとして吐く。ここで止めても前提は入らない
FILLERS = {"はい", "うん", "ええ", "えっ", "あー", "なるほど", "そうですね",
           "そうそう", "確かに", "はいはい", "オッケー", "ありがとうございます"}
NOTE_CHARS = "[]［］"

# **接続詞で始まるキューは文の頭ではない。** 直前が「。」で終わっていても、
# 中身は前の話の続きになる。「で、なんでかって言うと」から始めたのが
# 今回のコメント（「どういう意味なのか全くわからない」）の直接の原因だった
CONTINUATIONS = ("で、", "でも", "ですから", "だから", "だけど", "ただ", "それで",
                 "そして", "そこで", "なので", "つまり", "けど", "が、", "あと",
                 "ま、", "まあ", "っていうか", "ていうか", "というか", "で,")


def _core(line: str) -> str:
    """音の注記・先頭の相槌・句読点を落とした中身を返す。

    ASRは「はい。で、子供にもそうです。」のように相槌と本文を1キューに混ぜる。
    先頭の相槌を落とさないと、続きの接続詞を見逃す。
    """
    s = (line or "").strip()
    while s and s[0] in NOTE_CHARS:                      # [笑い] のようなキュー
        close = max(s.find("]"), s.find("］"))
        if close < 0:
            break
        s = s[close + 1:].strip()
    for _ in range(3):                                   # 相槌が連なることがある
        for f in FILLERS:
            if s.startswith(f) and s[len(f):len(f) + 1] in ("。", "、", "．"):
                s = s[len(f) + 1:].strip()
                break
        else:
            break
    return s.strip("".join(SENTENCE_END) + "、 　")


def is_fragment(line: str) -> bool:
    """相槌・音の注記・1文字キューなら True。ここでは切り出しを始めない。"""
    core = _core(line)
    return len(core) < 3 or core in FILLERS


def continues_previous(line: str) -> bool:
    """接続詞で始まる＝前の話の続きなら True。ここで切ると前提が入らない。"""
    return _core(line).startswith(CONTINUATIONS)


def rewind_to_topic_head(start: float, cues: list[dict],
                         max_back: float = REWIND_MAX_BACK) -> dict:
    """開始点を巻き戻して {"start", "kind", "line"} を返す。

    着地の質は3段階ある。**どれで着地したかを返すのは --dry-run で
    目で止められるようにするため。**

      文頭      直前のキューが文末（。？!）で終わっている＝文の頭。狙いはここ
      境界      文頭が見つからず、キューの頭に寄せただけ。前提が入っていない
                可能性が高いので、人が区間を選び直す判断材料になる
      そのまま  max_back 秒の内に何も無かった。行き過ぎるくらいなら動かさない
    """
    if not cues:
        return {"start": start, "kind": "そのまま", "line": ""}
    i = max((k for k, c in enumerate(cues) if c["t"] <= start + 1e-9), default=None)
    if i is None:
        return {"start": start, "kind": "そのまま", "line": ""}

    limit = start - max_back
    boundary = None
    for j in range(i, -1, -1):
        if cues[j]["t"] < limit:
            break
        line = cues[j]["line"]
        if is_fragment(line):
            continue
        if boundary is None:
            boundary = j
        if continues_previous(line):
            continue
        # 先頭キューを無条件に文頭とはみなさない。「リストが全文である」という
        # 前提が要るうえ、証明できないものは「境界」で人の目に掛けたほうがよい
        prev = cues[j - 1]["line"].rstrip() if j > 0 else ""
        if prev.endswith(SENTENCE_END):
            return {"start": cues[j]["t"], "kind": "文頭", "line": line}

    if boundary is not None and cues[boundary]["t"] < start:
        return {"start": cues[boundary]["t"], "kind": "境界",
                "line": cues[boundary]["line"]}
    return {"start": start, "kind": "そのまま", "line": ""}
