#!/usr/bin/env python3
"""YouTube自動字幕（VTT）のパーサ。

自動字幕は2行ローリング表示のため、同じ文字列が何度も出る。
直前行の前方一致／包含で潰して、確定した行だけを残す。
libecity-library/scripts/fetch-youtube.py の実装を移植した。

自動字幕はASRなので固有名詞と数値が崩れる。令和の虎は金額が命なので、
ここから取った数字をそのままカードに載せてはいけない（→ scripts/recipe.py）。
"""

from __future__ import annotations

import re

TAG_RE = re.compile(r"<[^>]+>")
CUE_RE = re.compile(r"^(\d{2}:\d{2}:\d{2}\.\d{3})\s+-->")
SKIP_PREFIX = ("WEBVTT", "Kind:", "Language:", "NOTE")


def parse_vtt(text: str) -> list[tuple[float, str]]:
    """VTT全文を [(開始秒, 行), ...] に変換する。"""
    cues: list[tuple[float, str]] = []
    cur_t: float | None = None
    for raw in text.splitlines():
        m = CUE_RE.match(raw.strip())
        if m:
            h, mnt, s = m.group(1).split(":")
            cur_t = int(h) * 3600 + int(mnt) * 60 + float(s)
            continue
        line = TAG_RE.sub("", raw).strip()
        if not line or line.startswith(SKIP_PREFIX):
            continue
        cues.append((cur_t or 0.0, line))

    merged: list[tuple[float, str]] = []
    for t, line in cues:
        if merged:
            prev = merged[-1][1]
            if line == prev or line in prev:
                continue
            if prev in line:                      # 前の行が伸びただけ → 差し替え
                merged[-1] = (merged[-1][0], line)
                continue
        merged.append((t, line))
    return merged


# 焼き込み。**ショートは1枚のPNGを全区間に重ねていた。** 会話は進むのに
# 文字は動かないので、画面の人物が固定の台詞を言っているように見える
# （2026-08-19-akutsu-gyutan では、映っているのは志願者で台詞は虎のもの）。
BURN_MAX_CHARS = 24         # 1枚に載せる目安。縦型の下帯で2行に収まる長さ
BREAK_AFTER = "。．？?！!、，"
MIN_TAIL = 4                # これ未満の余りは前の断片にくっつける
# 断片の先頭に置くと読めなくなる文字。「…思っち」「ゃった。」のような割れ方を防ぐ
NEVER_LEAD = "ゃゅょぁぃぅぇぉっーゎ、。，．)）」』"
MIN_SHOW = 0.7              # これ未満しか出ない字幕は隣と繋げる（実測0.28秒があった）
MAX_SHOW = 8.0              # これを超えて1枚を出し続けない（VTRや音楽で字幕が切れる）
NOTE_RE = re.compile(r"[\[［][^\]］]*[\]］]")     # [笑い] [拍手] [鼻息] [音楽]

# ASRは固有名詞と数字を崩す。実測で「土橋さん→その悪さん」「焼き鳥3級→焼き鳥産」。
# 令和の虎は金額が命なので、これを含む行は焼く前に必ず人の目に掛ける
RISKY = "0123456789０１２３４５６７８９万億円%％割"


def _split(text: str, max_chars: int) -> list[str]:
    """読める長さに割る。句読点で切れるならそこで切る。"""
    out: list[str] = []
    rest = text
    while len(rest) > max_chars:
        head = rest[:max_chars]
        cut = max(head.rfind(ch) for ch in BREAK_AFTER)
        cut = cut + 1 if cut >= max_chars // 3 else max_chars
        while cut < len(rest) and rest[cut] in NEVER_LEAD:
            cut += 1
        out.append(rest[:cut])
        rest = rest[cut:]
    if rest:
        # 「か。」だけの1枚が0.2秒出るのを防ぐ。少しはみ出しても読めるほうがよい
        if out and len(rest) < MIN_TAIL:
            out[-1] += rest
        else:
            out.append(rest)
    return out


def burn_plan(cues: list[dict], start: float, end: float,
              max_chars: int = BURN_MAX_CHARS) -> list[dict]:
    """区間の字幕を [{"start", "end", "text"}] にする。時刻は start からの相対秒。

    キューの表示は次のキューが始まるまで。最後のキューは区間の終わりまで。
    音の注記（[笑い] など）は焼かない。字幕として意味を運ばないため。
    """
    from scripts.moments import _core

    # **音の注記を落としてから区間を決める。** ASRは長い発話の直後に「[鼻息]」の
    # ようなキューを差し込む。そこで打ち切ると、実測で107文字が0.29秒に詰め込まれ、
    # その後の12秒が無字幕になった
    kept = [(c["t"], NOTE_RE.sub("", c["line"] or "").strip()) for c in cues]
    # 1文字だけのキュー（ASRは「ほ」「お」を独立して吐く）は焼かない。
    # 0.5秒だけ1文字が出ても読めず、直前の字幕を途中で消してしまう
    kept = [(t, text) for t, text in kept if len(_core(text)) >= 2]

    plan: list[dict] = []
    for i, (t, text) in enumerate(kept):
        c_start, c_end = t, (kept[i + 1][0] if i + 1 < len(kept) else end)
        c_start, c_end = max(c_start, start), min(c_end, end)
        if c_end <= c_start:
            continue

        chunks = _split(text, max_chars)
        total = sum(len(x) for x in chunks) or 1
        at = c_start
        for k, chunk in enumerate(chunks):
            # 最後の断片はキューの終わりに合わせる。按分の丸めで隙間を空けない
            nxt = c_end if k == len(chunks) - 1 else at + (c_end - c_start) * len(chunk) / total
            nxt = min(nxt, at + MAX_SHOW)          # 1枚を出しっぱなしにしない
            plan.append({"start": round(at - start, 3),
                         "end": round(nxt - start, 3), "text": chunk})
            at = nxt
    return _merge_flashes(plan)


def _merge_flashes(plan: list[dict], min_show: float = MIN_SHOW) -> list[dict]:
    """一瞬しか出ない字幕を隣と繋げる。

    ASRは「FC」「版も出ておい」のように語を割って別キューにする。実測0.28秒。
    読めないうえに点滅するので、次の字幕と1枚にまとめる（音に合わせて
    短いほうの頭から出す）。最後の1枚なら前と繋げる。
    """
    out: list[dict] = []
    for cur in plan:
        if out and out[-1]["end"] - out[-1]["start"] < min_show:
            prev = out.pop()
            cur = {"start": prev["start"], "end": cur["end"],
                   "text": prev["text"] + cur["text"]}
        out.append(cur)
    if len(out) > 1 and out[-1]["end"] - out[-1]["start"] < min_show:
        last = out.pop()
        out[-1] = {"start": out[-1]["start"], "end": last["end"],
                   "text": out[-1]["text"] + last["text"]}
    return out


def risky_lines(plan: list[dict]) -> list[dict]:
    """数字・金額・割合を含む行を返す。ASRが崩している可能性が高い。"""
    return [p for p in plan if any(ch in RISKY for ch in p["text"])]
