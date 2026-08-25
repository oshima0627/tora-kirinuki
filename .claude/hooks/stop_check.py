#!/usr/bin/env python3
"""セッションを終えるときに、引き継ぎとpushの漏れを検出する。

**判定は「未pushのコミットがあるのに、そのどれも HANDOFF.md を触っていない」。**
2026-08-25 にこれが起きた（3コミット先行・HANDOFF.md は前日のまま・未push）。
push すれば自然に消えるので、放っておくと鳴り続けることはない。

止めるのは1セッションに1回だけ。それ以降は systemMessage で出す。
毎ターン止めると作業にならず、直せないときに無限ループになる。
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo import git_in, repo_root  # noqa: E402

# **Windowsの既定は cp932。** 日本語も ⚠ も出せずにUnicodeEncodeError で落ちる
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HANDOFF = "HANDOFF.md"


def verdict(ahead: int, handoff_touched: bool, dirty: int,
            already_blocked: bool) -> tuple[bool, str]:
    """(止めるか, 出す文) を返す。副作用を持たないのでテストできる。"""
    if ahead == 0 and dirty == 0:
        return False, ""
    lines = []
    if ahead and not handoff_touched:
        lines.append(f"未pushのコミットが{ahead}件あるのに、どれも {HANDOFF} を"
                     "触っていません。**直下の HANDOFF.md を今回の内容で上書きしてください**"
                     "（新しい日付のファイルを作らない）。書く項目は CLAUDE.md にあります。")
    elif ahead:
        lines.append(f"{HANDOFF} は更新済みですが、未pushのコミットが{ahead}件あります。"
                     "`git push` と既定ブランチへのマージまで済ませてください。")
    if dirty:
        lines.append(f"未コミットの変更が{dirty}件あります。"
                     "途中で終わるときも、そこまでをコミットして残してください。")
    msg = " ".join(lines)
    return (bool(ahead) and not handoff_touched and not already_blocked), msg


def _seen(session_id: str) -> bool:
    """このセッションで既に一度止めたか。止めていなければ印を付けて False。"""
    if not session_id:
        return True                        # 判別できないなら止めない
    mark = Path(tempfile.gettempdir()) / f"claude-handoff-{session_id}.mark"
    if mark.exists():
        return True
    mark.write_text("1", encoding="utf-8")
    return False


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    root = repo_root()
    if root is None:
        return

    upstream = git_in(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    base = upstream or "origin/main"
    rng = f"{base}..HEAD"
    commits = [c for c in git_in(root, "rev-list", rng).splitlines() if c]
    touched = HANDOFF in git_in(root, "diff", "--name-only", f"{base}...HEAD").splitlines()
    dirty = len([x for x in git_in(root, "status", "--porcelain").splitlines() if x])

    block, msg = verdict(len(commits), touched, dirty,
                         already_blocked=_seen(payload.get("session_id", "")))
    if not msg:
        return
    out: dict = {"systemMessage": f"⚠ {msg}"}
    if block:
        out |= {"decision": "block", "reason": msg}
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
