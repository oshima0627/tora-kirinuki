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
                    prefer: str | None = None) -> list[dict]:
    """スコアの積分が大きい区間を、重ならないように上から取る。

    ヒートマップが無くても動く。令和の虎Second では30本中23本で
    ヒートマップが存在しないため、ここが動かないと大半の動画で候補ゼロになる。
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
        picked.append({
            "start": start, "end": end, "score": round(total, 3),
            "signals": signal_counts(signals, start, end),
            "subtitles": [c["line"] for c in cues if start <= c["t"] <= end],
        })
        if len(picked) >= count:
            break
    return picked
