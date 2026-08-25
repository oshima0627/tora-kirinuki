"""フックが見る「本体のリポジトリ」を決める。

**ワークツリーから起動されても本体の HANDOFF.md を見る。** 2026-08-25 に、
ワークツリーのブランチが初期コミットのままで CLAUDE.md も HANDOFF.md も
無く、引き継ぎを読まないまま作業を始めた。git-common-dir は
ワークツリーでも本体の .git を指すので、その親を根とする。
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def _git(*args: str) -> str:
    return subprocess.run(("git", *args), capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout.strip()


def repo_root() -> Path | None:
    common = _git("rev-parse", "--git-common-dir")
    if not common:
        return None
    top = _git("rev-parse", "--show-toplevel")
    # 本体では ".git"（相対）、ワークツリーでは本体の絶対パスが返る
    p = Path(common)
    if not p.is_absolute():
        p = Path(top or ".") / p
    return p.resolve().parent


def git_in(root: Path, *args: str) -> str:
    return subprocess.run(("git", "-C", str(root), *args), capture_output=True,
                          text=True, encoding="utf-8", errors="replace").stdout.strip()
