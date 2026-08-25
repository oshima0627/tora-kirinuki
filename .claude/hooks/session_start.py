#!/usr/bin/env python3
"""セッション開始時に HANDOFF.md を context へ入れる。

**指示書に書いたから読む、とは考えない。** CLAUDE.md に「必ず読む」と
書いてあっても 2026-08-25 に読み落とした。決定論的に流し込む。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo import repo_root  # noqa: E402

# **Windowsの既定は cp932。** 日本語も ⚠ も出せずにUnicodeEncodeError で落ちる
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

MAX_CHARS = 20000


def main() -> None:
    root = repo_root()
    f = root / "HANDOFF.md" if root else None
    if f is None or not f.exists():
        body = ("HANDOFF.md がリポジトリ直下にありません。"
                "**このセッションの終わりに必ず新規作成してください。**"
                "書く項目は CLAUDE.md にあります。")
    else:
        text = f.read_text(encoding="utf-8", errors="replace")
        if len(text) > MAX_CHARS:
            text = text[:MAX_CHARS] + "\n\n（長いのでここで切りました。全文は HANDOFF.md）"
        body = (f"=== {f} ===\n{text}\n=== ここまで ===\n"
                "**このセッションの終わりに、このファイルを今回の内容で上書きしてください。**"
                "新しい日付のファイルを作らない。直下の HANDOFF.md を書き直す。")
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart", "additionalContext": body}},
        ensure_ascii=False))


if __name__ == "__main__":
    main()
