"""Stop フックの判定。

**未pushのコミットがあるのに HANDOFF.md を触っていない**を捕まえる。
2026-08-25 にこれが起きた（3コミット先行・HANDOFF.md は前日のまま・未push）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".claude" / "hooks"))

from stop_check import verdict  # noqa: E402


def test_きれいなら何も言わない():
    assert verdict(ahead=0, handoff_touched=False, dirty=0,
                   already_blocked=False) == (False, "")


def test_未pushでHANDOFFを触っていなければ止める():
    block, msg = verdict(ahead=3, handoff_touched=False, dirty=0,
                         already_blocked=False)
    assert block and "HANDOFF.md" in msg


def test_同じセッションで二度目は止めずに言うだけ():
    block, msg = verdict(ahead=3, handoff_touched=False, dirty=0,
                         already_blocked=True)
    assert not block and "HANDOFF.md" in msg


def test_HANDOFFを触っていればpushだけ促す():
    block, msg = verdict(ahead=3, handoff_touched=True, dirty=0,
                         already_blocked=False)
    assert not block and "push" in msg


def test_未コミットだけなら止めない():
    block, msg = verdict(ahead=0, handoff_touched=False, dirty=2,
                         already_blocked=False)
    assert not block and "未コミット" in msg


def test_pushしてしまえば消える():
    # 鳴り続けないこと。push すれば ahead=0 になる
    assert verdict(ahead=0, handoff_touched=True, dirty=0,
                   already_blocked=False) == (False, "")
