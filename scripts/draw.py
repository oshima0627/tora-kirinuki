#!/usr/bin/env python3
"""描画の共通部品。チャンネルアート（build_brand）と図解カード（cards）で共有する。

配色はチャンネルのブランドに揃える。白地に赤、差し色に金。
令和の虎の意匠（赤いリング・筆文字ロゴ・人物シルエット・イナズマ）は使わない。
"""

from __future__ import annotations

import re
from pathlib import Path

from PIL import ImageDraw, ImageFont

FONT_SANS = [
    r"C:\Windows\Fonts\YuGothB.ttc",
    r"C:\Windows\Fonts\meiryob.ttc",
    r"C:\Windows\Fonts\msgothic.ttc",
]

RED = (214, 34, 42)
GOLD = (226, 158, 34)
BG_TOP = (255, 255, 255)
BG_BOTTOM = (243, 243, 246)
INK = (24, 24, 28)
MUTED = (122, 122, 132)


def pick_font(size: int) -> ImageFont.FreeTypeFont:
    for p in FONT_SANS:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def fit_font(draw: ImageDraw.ImageDraw, text: str, max_w: int,
             start: int) -> ImageFont.FreeTypeFont:
    """幅に収まる最大サイズのフォントを返す。"""
    size = start
    while size > 14:
        f = pick_font(size)
        b = draw.textbbox((0, 0), text, font=f)
        if b[2] - b[0] <= max_w:
            return f
        size -= 2
    return pick_font(14)


# 英数字の連なりと、数値＋単位は途中で折り返さない。1文字ずつ送っていた頃は
# 「231万5000円」が「231万5」／「000円」に、「1兆747億円」が「…2兆」／「円」に
# 割れており、行をまたいだ数字が別の額に読めていた。
_NUM = r"[0-9A-Za-z][0-9A-Za-z.,]*"
_UNIT = (r"パーセント|ポイント|項目|時間|キロ|メートル|トン|ドル|"
         r"[%％万億兆円年月日人名件回倍割歳個台本社校票席分秒]")
_ATOM_RE = re.compile(rf"(?:{_NUM}(?:{_UNIT})*)+|.", re.S)

# 改行してよい場所の優先度。日本語は単語境界が無いので、幅だけで切ると
# 「立候補して」／「いる」のように語の途中で割れる。幅の許す範囲で
# いちばん後ろの「自然な切れ目」まで戻してから改行する。
_BREAK_AFTER = "、。，．！？」』）］｝〉》"      # この文字の直後で切る
_BREAK_BEFORE = "「『（［｛〈《"                # この文字の直前で切る
_PARTICLES = "はがをにへとでもやのかねよ"       # 助詞の直後も自然
_HIRAGANA = re.compile(r"[ぁ-ゟ]")

# **括弧の中では折らない。** 引用は1つのまとまりで、途中で切ると読み手が
# 繋ぎ直すことになる（「場所を変えるか、／順序を変えるか」のように割れる）。
_OPEN_BRACKETS = "（［｛「『〈《〔"
_CLOSE_BRACKETS = "）］｝」』〉》〕"

# 切れ目を探して戻れる範囲。これ以上戻ると行が短くなりすぎて、
# かえって読みにくい（1行だけ極端に短い段差ができる）。
_BACKTRACK_RATIO = 0.6


def _atom_depths(atoms: list[str]) -> list[int]:
    """各 atom の開始時点の括弧の深さ。depths[j] は j の直前で折るときの深さ。"""
    depths, depth = [], 0
    for a in atoms:
        depths.append(depth)
        for ch in a:
            if ch in _OPEN_BRACKETS:
                depth += 1
            elif ch in _CLOSE_BRACKETS:
                depth = max(0, depth - 1)
    return depths


def _break_score(atoms: list[str], j: int, depths: list[int]) -> int:
    """atoms[:j] で改行したときの自然さ。大きいほど良い、0 なら語の途中。"""
    if depths[j] > 0:                 # 括弧の中。ここは切れ目として選ばない
        return 0
    prev, nxt = atoms[j - 1], atoms[j]
    if prev[-1] in _BREAK_AFTER:
        return 4
    if nxt[0] in _BREAK_BEFORE:
        return 3
    if len(prev) == 1 and prev in _PARTICLES:
        return 2
    # ひらがな → 漢字・カタカナ の変わり目は語の切れ目であることが多い。
    # 逆にひらがなが続く所や、漢字のあとのひらがな（送りがな）は語の途中。
    if _HIRAGANA.match(prev[-1]) and not _HIRAGANA.match(nxt[0]):
        return 1
    return 0


def _choose_break(atoms: list[str], start: int, n: int,
                  depths: list[int]) -> int:
    """幅で決まった位置 n から、自然な切れ目まで戻した位置を返す。"""
    floor = start + max(1, int((n - start) * _BACKTRACK_RATIO))
    best, best_score = n, 0
    for j in range(n, floor - 1, -1):
        if j >= len(atoms) or j <= start:
            continue
        score = _break_score(atoms, j, depths)
        if score > best_score:            # 同点なら後ろ（行が長いほう）を採る
            best, best_score = j, score
    return best


def wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont,
         max_w: int) -> list[str]:
    """日本語は単語境界が無いので、幅と切れ目の自然さを見て折り返す。

    英数字と数値＋単位は1かたまりとして扱い、途中では切らない。
    幅で決まった位置が語の途中なら、句読点・かっこ・助詞・ひらがなから漢字への
    変わり目まで戻してから改行する（戻しすぎて行が短くなるのは
    `_BACKTRACK_RATIO` で防ぐ）。
    """
    atoms = _ATOM_RE.findall(text)
    depths = _atom_depths(atoms)
    lines, start = [], 0
    while start < len(atoms):
        n = start
        while n < len(atoms):
            cand = "".join(atoms[start:n + 1])
            b = draw.textbbox((0, 0), cand, font=font)
            if b[2] - b[0] > max_w and n > start:
                break
            n += 1
        if n >= len(atoms):
            lines.append("".join(atoms[start:]))
            break
        cut = _choose_break(atoms, start, n, depths) if n - start > 1 else n
        cut = max(cut, start + 1)          # 1行に最低1 atom は入れる
        lines.append("".join(atoms[start:cut]))
        start = cut
    return lines
