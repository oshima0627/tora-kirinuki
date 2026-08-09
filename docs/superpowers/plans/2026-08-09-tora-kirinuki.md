# tora-kirinuki 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 令和の虎Second の本編から、図解カード付きの切り抜き動画を作って YouTube に投稿するパイプラインを作る。

**Architecture:** `bgm-youtube` と同じ「レシピJSON → ビルド → `work/<id>/` → アップロード」の型。
素材取得（yt-dlp）→ シグナル取得（Most replayed / コメント）→ 候補抽出（3点合成）→ レシピ作成 → ビルド（ffmpeg + Pillow）→ 投稿の6段。
純粋関数（パーサ・スコアリング・文字列生成）とI/O（yt-dlp・ffmpeg・API）を分離し、前者をテストで固める。

**Tech Stack:** Python 3.13 / pytest / yt-dlp / Pillow / ffmpeg / google-api-python-client

設計: [`../specs/2026-08-09-tora-kirinuki-design.md`](../specs/2026-08-09-tora-kirinuki-design.md)

## Global Constraints

すべてのタスクの要件に、以下が暗黙的に含まれる。

- **概要欄の冒頭には元動画のURLとタイトルを自動挿入する。** 手書きさせない（権利者ガイドラインの必須条件）
- **`expected_channel_id` が `meta.json` に無い、または実チャンネルと不一致ならアップロードしない**
- **`cards.brief.amount` が空ならビルドを失敗させる。** 字幕はASRで金額が崩れるため、未確認のまま公開させない
- **ffmpeg の尺は `-t` で明示し、ビルド後に実尺との差が1秒を超えたら失敗させる**
- **yt-dlp には `extractor_args={"youtube": {"lang": ["ja"]}}` を必ず渡す。** 付けないとタイトル・チャプター名が英語に自動翻訳される
- **素材の実在確認は処理開始前にまとめて行う。** 途中で ffmpeg が落ちるより、何が無いかを先に出す
- 音声ナレーションは入れない。付加価値はテロップと図解のみ
- Windows のため、標準出力は `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` する
- 対象は令和の虎Second（`@reiwanotora_second` / `UC9cD37sXfBNCQpz3vINa3TA`）のみ

---

### Task 1: プロジェクト基盤と字幕パーサ

**Files:**
- Create: `requirements.txt`
- Create: `pytest.ini`
- Create: `scripts/subtitles.py`
- Create: `tests/test_subtitles.py`

**Interfaces:**
- Consumes: なし
- Produces: `parse_vtt(text: str) -> list[tuple[float, str]]` — VTT全文を [(開始秒, 行), ...] に変換

`libecity-library/scripts/fetch-youtube.py:77-106` に動作実績のある実装がある。ロジックはそこから移植する。

- [ ] **Step 1: 依存とpytest設定を置く**

`requirements.txt`:

```
yt-dlp
pillow
google-api-python-client
google-auth-oauthlib
pytest
```

`pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
```

- [ ] **Step 2: 失敗するテストを書く**

`tests/test_subtitles.py`:

```python
from scripts.subtitles import parse_vtt

VTT = """WEBVTT
Kind: captions
Language: ja

00:00:01.000 --> 00:00:03.000
<c>希望</c>金額は

00:00:03.000 --> 00:00:05.000
希望金額は500万円

00:00:05.000 --> 00:00:07.000
希望金額は500万円

00:00:07.000 --> 00:00:09.000
事業内容を説明します
"""


def test_タグを除去して秒と行に変換する():
    assert parse_vtt(VTT)[0] == (1.0, "希望金額は")


def test_ローリング表示の重複を潰して伸びた行に差し替える():
    lines = [line for _, line in parse_vtt(VTT)]
    assert lines == ["希望金額は500万円", "事業内容を説明します"]


def test_ヘッダ行は無視する():
    assert all(l not in ("WEBVTT", "Kind: captions") for _, l in parse_vtt(VTT))


def test_空文字なら空リストを返す():
    assert parse_vtt("") == []
```

- [ ] **Step 3: 実行して失敗を確認する**

Run: `python -m pytest tests/test_subtitles.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.subtitles'`

- [ ] **Step 4: 実装する**

`scripts/subtitles.py`:

```python
#!/usr/bin/env python3
"""YouTube自動字幕（VTT）のパーサ。

自動字幕は2行ローリング表示のため、同じ文字列が何度も出る。
直前行の前方一致／包含で潰して、確定した行だけを残す。
libecity-library/scripts/fetch-youtube.py の実装を移植した。
"""

from __future__ import annotations

import re

TAG_RE = re.compile(r"<[^>]+>")
CUE_RE = re.compile(r"^(\d{2}:\d{2}:\d{2}\.\d{3})\s+-->")
SKIP_PREFIX = ("WEBVTT", "Kind:", "Language:", "NOTE")


def parse_vtt(text: str) -> list[tuple[float, str]]:
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
```

`scripts/__init__.py` と `tests/__init__.py` を空ファイルで作る（`from scripts.x import` を通すため）。

- [ ] **Step 5: 実行して成功を確認する**

Run: `python -m pytest tests/test_subtitles.py -v`
Expected: PASS（4件）

- [ ] **Step 6: コミット**

```bash
git add requirements.txt pytest.ini scripts/ tests/
git commit -m "字幕VTTパーサを libecity-library から移植"
```

---

### Task 2: 本編の取得（fetch_source.py）

**Files:**
- Create: `scripts/fetch_source.py`
- Create: `tests/test_fetch_source.py`

**Interfaces:**
- Consumes: `scripts.subtitles.parse_vtt`
- Produces:
  - `pick_ja_vtt(info: dict) -> tuple[str | None, str | None, str | None]` — (URL, "manual"|"auto", 言語コード)
  - `source_dir(video_id: str) -> Path` — `work/<video_id>/`
  - CLI: `python scripts/fetch_source.py --latest 5` / `--since 2026-08-01` / `<URL>...` / `--force`

出力は `work/<video_id>/` に `source.mp4`・`subs.json`・`meta.json`。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_fetch_source.py`:

```python
from scripts.fetch_source import pick_ja_vtt


def test_手動字幕を自動生成より優先する():
    info = {
        "subtitles": {"ja": [{"ext": "vtt", "url": "manual-url"}]},
        "automatic_captions": {"ja": [{"ext": "vtt", "url": "auto-url"}]},
    }
    assert pick_ja_vtt(info) == ("manual-url", "manual", "ja")


def test_手動が無ければ自動生成にフォールバックする():
    info = {"automatic_captions": {"ja": [{"ext": "vtt", "url": "auto-url"}]}}
    assert pick_ja_vtt(info) == ("auto-url", "auto", "ja")


def test_ja_origも見る():
    info = {"automatic_captions": {"ja-orig": [{"ext": "vtt", "url": "u"}]}}
    assert pick_ja_vtt(info) == ("u", "auto", "ja-orig")


def test_vtt以外は選ばない():
    info = {"subtitles": {"ja": [{"ext": "srv3", "url": "x"}]}}
    assert pick_ja_vtt(info) == (None, None, None)


def test_日本語字幕が無ければNoneを返す():
    assert pick_ja_vtt({"subtitles": {"en": [{"ext": "vtt", "url": "x"}]}}) == (None, None, None)
```

- [ ] **Step 2: 実行して失敗を確認する**

Run: `python -m pytest tests/test_fetch_source.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.fetch_source'`

- [ ] **Step 3: 実装する**

`scripts/fetch_source.py`:

```python
#!/usr/bin/env python3
"""令和の虎Second の本編を取得する。

  python scripts/fetch_source.py --latest 5
  python scripts/fetch_source.py --since 2026-08-01
  python scripts/fetch_source.py <URL> [<URL>...]
  python scripts/fetch_source.py --latest 5 --list    # 取得せず一覧だけ
  python scripts/fetch_source.py --latest 5 --force   # 取得済みも再取得
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.subtitles import parse_vtt  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"

CHANNEL_URL = "https://www.youtube.com/@reiwanotora_second/videos"
CHANNEL_ID = "UC9cD37sXfBNCQpz3vINa3TA"

# lang=ja を付けないと、タイトル・チャプター名が自動翻訳で英語になる
JA = {"youtube": {"lang": ["ja"]}}


def source_dir(video_id: str) -> Path:
    return WORK / video_id


def pick_ja_vtt(info: dict) -> tuple[str | None, str | None, str | None]:
    """日本語字幕のVTT URLを返す。手動字幕を優先し、無ければ自動生成。"""
    for store, kind in ((info.get("subtitles") or {}, "manual"),
                        (info.get("automatic_captions") or {}, "auto")):
        for lang in ("ja", "ja-orig", "ja-JP"):
            for track in store.get(lang) or []:
                if track.get("ext") == "vtt":
                    return track["url"], kind, lang
    return None, None, None


def list_channel(limit: int) -> list[dict]:
    """新着一覧（メタのみ）。RSSは500/404を返すことがあるので yt-dlp を使う。"""
    from yt_dlp import YoutubeDL
    opts = {"quiet": True, "no_warnings": True, "skip_download": True,
            "extract_flat": "in_playlist", "playlistend": limit, "extractor_args": JA}
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(CHANNEL_URL, download=False)
    return [{"id": e.get("id"), "title": e.get("title") or "",
             "duration": e.get("duration"),
             "url": f"https://www.youtube.com/watch?v={e.get('id')}"}
            for e in (info.get("entries") or [])]


def fetch_one(url: str, force: bool = False) -> Path:
    from yt_dlp import YoutubeDL

    with YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True,
                    "extractor_args": JA}) as ydl:
        info = ydl.extract_info(url, download=False)
        out = source_dir(info["id"])
        if out.exists() and not force:
            print(f"- {info['id']} は取得済み（--force で再取得）")
            return out
        out.mkdir(parents=True, exist_ok=True)

        sub_url, kind, lang = pick_ja_vtt(info)
        if not sub_url:
            raise SystemExit(f"! {info['id']}: 日本語字幕が無い。切り抜き地点を出せないので中断する")
        with ydl.urlopen(sub_url) as r:
            cues = parse_vtt(r.read().decode("utf-8", "replace"))

    (out / "subs.json").write_text(
        json.dumps([{"t": t, "line": l} for t, l in cues], ensure_ascii=False, indent=1),
        encoding="utf-8")
    (out / "meta.json").write_text(json.dumps({
        "video_id": info["id"],
        "url": info.get("webpage_url"),
        "title": info.get("title"),
        "duration_sec": info.get("duration"),
        "upload_date": info.get("upload_date"),
        "chapters": info.get("chapters") or [],
        "subtitle_kind": kind,
        "subtitle_lang": lang,
        "fetched_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    with YoutubeDL({"quiet": True, "no_warnings": True, "extractor_args": JA,
                    "format": "bestvideo[height<=1080]+bestaudio/best",
                    "merge_output_format": "mp4",
                    "outtmpl": str(out / "source.%(ext)s")}) as ydl:
        ydl.download([url])

    print(f"✓ {info['id']}  {info.get('title')}  字幕{len(cues)}行")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("urls", nargs="*")
    ap.add_argument("--latest", type=int)
    ap.add_argument("--since")
    ap.add_argument("--list", action="store_true", help="取得せず一覧だけ表示")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    urls = list(a.urls)
    if a.latest or a.since:
        items = list_channel(a.latest or 50)
        if a.list:
            for it in items:
                print(f"{it['id']}  {it['title']}")
            return
        urls += [it["url"] for it in items]
    if not urls:
        raise SystemExit("URL か --latest / --since を指定してください")
    for u in urls:
        fetch_one(u, a.force)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 実行して成功を確認する**

Run: `python -m pytest tests/test_fetch_source.py -v`
Expected: PASS（5件）

- [ ] **Step 5: 実データで1本取得する**

```bash
python -m pip install --user yt-dlp
python scripts/fetch_source.py --latest 3 --list
python scripts/fetch_source.py --latest 1
```

`work/<video_id>/` に `subs.json`・`meta.json`・`source.mp4` が出ること。
`meta.json` の `title` が**日本語**であること（英語なら `JA` が効いていない）。

- [ ] **Step 6: コミット**

```bash
git add scripts/fetch_source.py tests/test_fetch_source.py
git commit -m "本編と日本語字幕の取得を追加"
```

---

### Task 3: シグナル取得（probe_signals.py）

**Files:**
- Create: `scripts/signals.py`
- Create: `tests/test_signals.py`
- Create: `scripts/probe_signals.py`

**Interfaces:**
- Consumes: `scripts.fetch_source.source_dir`
- Produces:
  - `parse_heatmap(data: dict) -> list[dict]` — `ytInitialData` から `[{"start": float, "end": float, "score": float}, ...]`
  - `extract_timestamps(text: str) -> list[int]` — コメント本文から `mm:ss` / `h:mm:ss` を秒に
  - `aggregate_marks(comments: list[str]) -> list[dict]` — `[{"seconds": int, "count": int, "samples": [str]}, ...]`

Most replayed は YouTube Data API では取得できない。ブラウザで `ytInitialData` を読む。
`probe_signals.py` は `signals.json` の**受け口**とし、ヒートマップのJSONは引数で受け取る。
こうするとブラウザ操作と純粋処理が分離でき、テストできる。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_signals.py`:

```python
from scripts.signals import aggregate_marks, extract_timestamps, parse_heatmap

YT = {
    "frameworkUpdates": {"entityBatchUpdate": {"mutations": [
        {"payload": {"macroMarkersListEntity": {"markersList": {
            "markerType": "MARKER_TYPE_HEATMAP",
            "markers": [
                {"startMillis": "0", "durationMillis": "30000",
                 "intensityScoreNormalized": 0.10},
                {"startMillis": "30000", "durationMillis": "30000",
                 "intensityScoreNormalized": 0.95},
            ]}}}},
    ]}}
}


def test_ヒートマップを秒とスコアに変換する():
    assert parse_heatmap(YT) == [
        {"start": 0.0, "end": 30.0, "score": 0.10},
        {"start": 30.0, "end": 60.0, "score": 0.95},
    ]


def test_ヒートマップが無ければ空リスト():
    assert parse_heatmap({}) == []


def test_mmss形式を秒にする():
    assert extract_timestamps("12:34 ここが好き") == [754]


def test_hmmss形式を秒にする():
    assert extract_timestamps("1:02:03 の場面") == [3723]


def test_1コメント内の複数言及を全部拾う():
    assert extract_timestamps("0:30 と 2:00 が神") == [30, 120]


def test_タイムスタンプが無ければ空():
    assert extract_timestamps("面白かった") == []


def test_同じ秒の言及を数える():
    marks = aggregate_marks(["12:34 好き", "12:34 神回", "0:10 冒頭"])
    assert marks[0] == {"seconds": 754, "count": 2, "samples": ["12:34 好き", "12:34 神回"]}


def test_言及数の多い順に並ぶ():
    marks = aggregate_marks(["0:10 a", "12:34 b", "12:34 c"])
    assert [m["seconds"] for m in marks] == [754, 10]
```

- [ ] **Step 2: 実行して失敗を確認する**

Run: `python -m pytest tests/test_signals.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.signals'`

- [ ] **Step 3: 実装する**

`scripts/signals.py`:

```python
#!/usr/bin/env python3
"""Most replayed ヒートマップとコメントのタイムスタンプ言及を扱う純粋関数。"""

from __future__ import annotations

import re

TS_RE = re.compile(r"(?<![\d:])(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?![\d:])")
SAMPLE_LIMIT = 3


def parse_heatmap(data: dict) -> list[dict]:
    """ytInitialData から Most replayed を [{"start","end","score"}, ...] にする。"""
    out: list[dict] = []

    def walk(o):
        if isinstance(o, list):
            for x in o:
                walk(x)
            return
        if not isinstance(o, dict):
            return
        ml = o.get("macroMarkersListEntity", {}).get("markersList")
        if ml and ml.get("markerType") == "MARKER_TYPE_HEATMAP":
            for m in ml.get("markers") or []:
                start = int(m.get("startMillis", 0)) / 1000
                dur = int(m.get("durationMillis", 0)) / 1000
                out.append({"start": start, "end": start + dur,
                            "score": float(m.get("intensityScoreNormalized", 0.0))})
        for v in o.values():
            walk(v)

    walk(data)
    return out


def extract_timestamps(text: str) -> list[int]:
    """コメント本文の mm:ss / h:mm:ss を秒に変換して返す。"""
    out = []
    for h, m, s in TS_RE.findall(text or ""):
        out.append((int(h) if h else 0) * 3600 + int(m) * 60 + int(s))
    return out


def aggregate_marks(comments: list[str]) -> list[dict]:
    """秒ごとに言及を集計する。言及数の多い順、同数なら秒の小さい順。"""
    bucket: dict[int, list[str]] = {}
    for c in comments:
        for sec in extract_timestamps(c):
            bucket.setdefault(sec, []).append(c)
    marks = [{"seconds": sec, "count": len(v), "samples": v[:SAMPLE_LIMIT]}
             for sec, v in bucket.items()]
    marks.sort(key=lambda m: (-m["count"], m["seconds"]))
    return marks
```

- [ ] **Step 4: 実行して成功を確認する**

Run: `python -m pytest tests/test_signals.py -v`
Expected: PASS（8件）

- [ ] **Step 5: 受け口のCLIを作る**

`scripts/probe_signals.py`:

```python
#!/usr/bin/env python3
"""ヒートマップとコメントを signals.json にまとめる。

ヒートマップはブラウザで取得した ytInitialData の JSON ファイルを渡す。
（Most replayed は YouTube Data API では取得できない）

  python scripts/probe_signals.py <video_id> --ytdata dump.json --comments comments.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.fetch_source import source_dir  # noqa: E402
from scripts.signals import aggregate_marks, parse_heatmap  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video_id")
    ap.add_argument("--ytdata", type=Path, required=True,
                    help="ブラウザで取得した ytInitialData の JSON")
    ap.add_argument("--comments", type=Path,
                    help="コメント本文の配列（JSON）。省略時はコメント信号なし")
    a = ap.parse_args()

    out = source_dir(a.video_id)
    if not out.exists():
        raise SystemExit(f"! {out} が無い。先に fetch_source.py を実行してください")

    heatmap = parse_heatmap(json.loads(a.ytdata.read_text(encoding="utf-8")))
    if not heatmap:
        print("! ヒートマップが取れていない。動画が新しすぎる可能性がある")

    comments = json.loads(a.comments.read_text(encoding="utf-8")) if a.comments else []
    marks = aggregate_marks(comments)

    (out / "signals.json").write_text(json.dumps(
        {"video_id": a.video_id, "heatmap": heatmap, "comment_marks": marks},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✓ {out / 'signals.json'}  ヒートマップ{len(heatmap)}区間 / コメント言及{len(marks)}箇所")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: コミット**

```bash
git add scripts/signals.py scripts/probe_signals.py tests/test_signals.py
git commit -m "Most replayedとコメント言及の取得を追加"
```

---

### Task 4: 候補区間の抽出（find_moments.py）

**Files:**
- Create: `scripts/moments.py`
- Create: `tests/test_moments.py`
- Create: `scripts/find_moments.py`

**Interfaces:**
- Consumes: `scripts.signals`（`signals.json` の形）、`scripts.fetch_source.source_dir`
- Produces:
  - `score_at(seconds: float, heatmap: list[dict], marks: list[dict], window: float = 30.0) -> dict`
    → `{"heat": float, "comment": float, "total": float}`
  - `snap_to_cues(start: float, end: float, cues: list[dict]) -> tuple[float, float]`
  - `find_candidates(signals: dict, cues: list[dict], count: int = 5, length: float = 420.0) -> list[dict]`

**3信号の合成**: ヒートマップの山（視聴者が戻る場所）＋コメント言及（語られる場所）＋字幕（何が起きているか）。
重なる区間ほど高スコア。スコアは `heat * 0.6 + comment * 0.4` の加重和とする
（ヒートマップは全視聴者の行動、コメントは一部の声なので重みを分ける）。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_moments.py`:

```python
from scripts.moments import find_candidates, score_at, snap_to_cues

HEAT = [
    {"start": 0.0, "end": 30.0, "score": 0.1},
    {"start": 30.0, "end": 60.0, "score": 0.9},
]
MARKS = [{"seconds": 40, "count": 4, "samples": ["0:40 神"]}]
CUES = [{"t": 0.0, "line": "冒頭"}, {"t": 28.0, "line": "本題"},
        {"t": 58.0, "line": "詰め"}, {"t": 95.0, "line": "判定"}]


def test_ヒートマップの該当区間のスコアを返す():
    assert score_at(45.0, HEAT, [])["heat"] == 0.9


def test_ヒートマップの範囲外は0():
    assert score_at(500.0, HEAT, [])["heat"] == 0.0


def test_窓内のコメント言及を数える():
    assert score_at(45.0, HEAT, MARKS, window=30.0)["comment"] == 4.0


def test_窓外のコメント言及は数えない():
    assert score_at(200.0, HEAT, MARKS, window=30.0)["comment"] == 0.0


def test_合成スコアは加重和():
    s = score_at(45.0, HEAT, [])
    assert s["total"] == 0.9 * 0.6


def test_区間の端を字幕の切れ目に寄せる():
    assert snap_to_cues(30.0, 60.0, CUES) == (28.0, 58.0)


def test_字幕が無ければ元の区間を返す():
    assert snap_to_cues(30.0, 60.0, []) == (30.0, 60.0)


def test_候補はスコアの高い順に返る():
    sig = {"heatmap": HEAT, "comment_marks": MARKS}
    got = find_candidates(sig, CUES, count=1, length=30.0)
    assert len(got) == 1
    assert got[0]["start"] == 28.0


def test_ヒートマップが空なら候補も空():
    assert find_candidates({"heatmap": [], "comment_marks": []}, CUES) == []
```

- [ ] **Step 2: 実行して失敗を確認する**

Run: `python -m pytest tests/test_moments.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.moments'`

- [ ] **Step 3: 実装する**

`scripts/moments.py`:

```python
#!/usr/bin/env python3
"""3信号（ヒートマップ・コメント言及・字幕）の合成で切り抜き候補を出す。"""

from __future__ import annotations

W_HEAT = 0.6
W_COMMENT = 0.4
COMMENT_CAP = 10.0     # 言及数の正規化上限。1箇所に集中しても支配させない


def score_at(seconds: float, heatmap: list[dict], marks: list[dict],
             window: float = 30.0) -> dict:
    heat = 0.0
    for h in heatmap:
        if h["start"] <= seconds < h["end"]:
            heat = h["score"]
            break
    comment = float(sum(m["count"] for m in marks
                        if abs(m["seconds"] - seconds) <= window))
    total = heat * W_HEAT + min(comment / COMMENT_CAP, 1.0) * W_COMMENT
    return {"heat": heat, "comment": comment, "total": total}


def snap_to_cues(start: float, end: float, cues: list[dict]) -> tuple[float, float]:
    """区間の端を最寄りの字幕キュー境界に寄せる。文の途中で切らないため。"""
    if not cues:
        return start, end
    times = [c["t"] for c in cues]
    nearest = lambda x: min(times, key=lambda t: abs(t - x))  # noqa: E731
    return nearest(start), nearest(end)


def find_candidates(signals: dict, cues: list[dict], count: int = 5,
                    length: float = 420.0) -> list[dict]:
    """ヒートマップの区間ごとにスコアを出し、上位を長さ length の候補にする。"""
    heatmap = signals.get("heatmap") or []
    marks = signals.get("comment_marks") or []
    if not heatmap:
        return []

    scored = []
    for h in heatmap:
        mid = (h["start"] + h["end"]) / 2
        s = score_at(mid, heatmap, marks)
        start, end = snap_to_cues(max(0.0, mid - length / 2), mid + length / 2, cues)
        if end <= start:
            continue
        scored.append({"start": start, "end": end, "score": s["total"],
                       "breakdown": s,
                       "subtitles": [c["line"] for c in cues
                                     if start <= c["t"] <= end]})

    scored.sort(key=lambda c: -c["score"])

    picked: list[dict] = []
    for c in scored:
        if any(c["start"] < p["end"] and p["start"] < c["end"] for p in picked):
            continue                      # 既に採った区間と重なるものは捨てる
        picked.append(c)
        if len(picked) >= count:
            break
    return picked
```

- [ ] **Step 4: 実行して成功を確認する**

Run: `python -m pytest tests/test_moments.py -v`
Expected: PASS（9件）

- [ ] **Step 5: CLIを作る**

`scripts/find_moments.py`:

```python
#!/usr/bin/env python3
"""候補区間を candidates.json に出す。

  python scripts/find_moments.py <video_id> --count 5 --length 420
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.fetch_source import source_dir  # noqa: E402
from scripts.moments import find_candidates  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def hms(sec: float) -> str:
    s = int(sec)
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video_id")
    ap.add_argument("--count", type=int, default=5)
    ap.add_argument("--length", type=float, default=420.0, help="1本の目安の尺（秒）")
    a = ap.parse_args()

    d = source_dir(a.video_id)
    for name in ("signals.json", "subs.json"):
        if not (d / name).exists():
            raise SystemExit(f"! {d / name} が無い。先に fetch_source.py と probe_signals.py を実行してください")

    signals = json.loads((d / "signals.json").read_text(encoding="utf-8"))
    cues = json.loads((d / "subs.json").read_text(encoding="utf-8"))

    cands = find_candidates(signals, cues, a.count, a.length)
    (d / "candidates.json").write_text(
        json.dumps(cands, ensure_ascii=False, indent=1), encoding="utf-8")

    if not cands:
        print("! 候補が0件。ヒートマップが取れていない可能性がある")
    for i, c in enumerate(cands, 1):
        head = "".join(c["subtitles"][:3])[:60]
        print(f"{i}. {hms(c['start'])}-{hms(c['end'])}  score={c['score']:.3f}  {head}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: コミット**

```bash
git add scripts/moments.py scripts/find_moments.py tests/test_moments.py
git commit -m "3信号合成による切り抜き候補の抽出を追加"
```

---

### Task 5: レシピ検証と概要欄生成（recipe.py）

**Files:**
- Create: `scripts/recipe.py`
- Create: `tests/test_recipe.py`
- Create: `recipes/_example.json`

**Interfaces:**
- Consumes: なし
- Produces:
  - `validate(recipe: dict) -> None` — 不備があれば `ValueError`
  - `build_description(recipe: dict) -> str` — 冒頭に元動画URL・タイトルを入れた概要欄本文

**このタスクが規約担保の中核。** 概要欄の元動画URL挿入と `expected_channel_id` の必須化、
`cards.brief.amount` の空チェックをここで強制する。以降のビルドは必ずこれを通す。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_recipe.py`:

```python
import pytest

from scripts.recipe import build_description, validate


def base() -> dict:
    return {
        "id": "2026-08-10-example",
        "source_video_id": "abcdefghijk",
        "source_url": "https://www.youtube.com/watch?v=abcdefghijk",
        "source_title": "【FULL】元動画のタイトル",
        "clip": {"start": 100.0, "end": 500.0},
        "cards": {
            "brief": {"amount": "希望金額 500万円", "business": "事業内容", "profile": "経歴"},
            "points": [{"at": 200.0, "text": "指摘"}],
            "verdict": {"result": "成立", "detail": "2名から計300万円"},
        },
        "title": "動画タイトル",
        "description": "本文",
        "tags": ["令和の虎", "切り抜き"],
        "expected_channel_id": "UCxxxxxxxxxxxxxxxxxxxxxx",
        "privacy_status": "private",
    }


def test_正しいレシピは通る():
    validate(base())


def test_expected_channel_idが無ければ落ちる():
    r = base()
    del r["expected_channel_id"]
    with pytest.raises(ValueError, match="expected_channel_id"):
        validate(r)


def test_金額が空ならビルドさせない():
    r = base()
    r["cards"]["brief"]["amount"] = ""
    with pytest.raises(ValueError, match="amount"):
        validate(r)


def test_開始が終了以上なら落ちる():
    r = base()
    r["clip"] = {"start": 500.0, "end": 100.0}
    with pytest.raises(ValueError, match="clip"):
        validate(r)


def test_元動画URLが無ければ落ちる():
    r = base()
    r["source_url"] = ""
    with pytest.raises(ValueError, match="source_url"):
        validate(r)


def test_概要欄の冒頭に元動画URLとタイトルが入る():
    d = build_description(base())
    assert d.startswith("【元動画】【FULL】元動画のタイトル\nhttps://www.youtube.com/watch?v=abcdefghijk")


def test_概要欄に本文が含まれる():
    assert "本文" in build_description(base())


def test_概要欄に許諾済みである旨が入る():
    assert "ガジェット通信" in build_description(base())
```

- [ ] **Step 2: 実行して失敗を確認する**

Run: `python -m pytest tests/test_recipe.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.recipe'`

- [ ] **Step 3: 実装する**

`scripts/recipe.py`:

```python
#!/usr/bin/env python3
"""レシピの検証と概要欄の生成。

権利者ガイドラインの必須条件（概要欄の冒頭に元動画URL・タイトル）と、
過去の事故（別チャンネルへの誤投稿）への対策をここで強制する。
運用の注意書きではなく、通らなければ落ちる形にしてある。
"""

from __future__ import annotations

REQUIRED = ("id", "source_video_id", "source_url", "source_title",
            "title", "expected_channel_id")

CREDIT = ("本チャンネルはガジェット通信クリエイターネットワークを通じて"
          "切り抜き動画の許諾を得て運営しています。")


def validate(recipe: dict) -> None:
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


def build_description(recipe: dict) -> str:
    """概要欄。冒頭の元動画URL・タイトルは手書きさせず、ここで必ず付ける。"""
    body = (recipe.get("description") or "").strip()
    tags = " ".join(f"#{t}" for t in (recipe.get("tags") or []))
    parts = [
        f"【元動画】{recipe['source_title']}",
        recipe["source_url"],
        "",
        body,
        "",
        CREDIT,
    ]
    if tags:
        parts += ["", tags]
    return "\n".join(parts).strip() + "\n"
```

`recipes/_example.json` に `tests/test_recipe.py` の `base()` と同じ内容を置く（レシピを書くときの雛形）。

- [ ] **Step 4: 実行して成功を確認する**

Run: `python -m pytest tests/test_recipe.py -v`
Expected: PASS（8件）

- [ ] **Step 5: コミット**

```bash
git add scripts/recipe.py tests/test_recipe.py recipes/_example.json
git commit -m "レシピ検証と概要欄生成を追加（元動画URL挿入を強制）"
```

---

### Task 6: 図解カードの描画（cards.py）

**Files:**
- Create: `scripts/cards.py`
- Create: `tests/test_cards.py`

**Interfaces:**
- Consumes: `scripts.recipe`
- Produces:
  - `pick_font(size: int) -> ImageFont.FreeTypeFont`
  - `fit_font(draw, text: str, max_w: int, start: int) -> ImageFont.FreeTypeFont`
  - `render_brief(brief: dict, size=(1920, 1080)) -> Image.Image`
  - `render_point(text: str, size=(1920, 1080)) -> Image.Image` — 下部の帯だけ描いた RGBA
  - `render_verdict(verdict: dict, size=(1920, 1080)) -> Image.Image`

既存競合は全員が字幕止まりで、図解は空いている。ここが差別化の実体。
`bgm-youtube/scripts/build_video.py:93-103` の `pick_font` / `fit_font` と同じ手法を使う。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_cards.py`:

```python
from scripts.cards import render_brief, render_point, render_verdict


def test_案件カードは指定サイズで返る():
    img = render_brief({"amount": "希望金額 500万円", "business": "事業内容", "profile": "経歴"})
    assert img.size == (1920, 1080)


def test_論点カードは透過で返る():
    assert render_point("虎の指摘").mode == "RGBA"


def test_判定カードは指定サイズで返る():
    img = render_verdict({"result": "成立", "detail": "2名から計300万円"})
    assert img.size == (1920, 1080)


def test_長い文字列でも例外を出さない():
    render_point("あ" * 200)


def test_金額は必ず描画される(tmp_path):
    img = render_brief({"amount": "希望金額 500万円", "business": "", "profile": ""})
    p = tmp_path / "brief.png"
    img.save(p)
    assert p.stat().st_size > 0
```

- [ ] **Step 2: 実行して失敗を確認する**

Run: `python -m pytest tests/test_cards.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.cards'`

- [ ] **Step 3: 実装する**

`scripts/cards.py`:

```python
#!/usr/bin/env python3
"""図解カードの描画。

令和の虎は「志願者が事業計画を持ち込む→虎が詰める→出資判定」という定型構造を持つ。
元動画に無い整理をこの3枚で足す。既存の切り抜きは全員が字幕止まりで、ここが空いている。
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_SANS = [
    r"C:\Windows\Fonts\YuGothB.ttc",
    r"C:\Windows\Fonts\meiryob.ttc",
    r"C:\Windows\Fonts\msgothic.ttc",
]

BG = (17, 21, 34)
LINE = (238, 242, 252)
ACCENT = (255, 196, 106)
SUB = (168, 178, 204)


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


def render_brief(brief: dict, size: tuple[int, int] = (1920, 1080)) -> Image.Image:
    """案件カード。希望金額 / 事業内容 / 志願者の経歴。"""
    w, h = size
    img = Image.new("RGB", size, BG)
    d = ImageDraw.Draw(img)
    m = int(w * 0.09)
    avail = w - m * 2

    f = fit_font(d, brief.get("amount", ""), avail, int(h * 0.13))
    d.text((m, int(h * 0.22)), brief.get("amount", ""), font=f, fill=ACCENT)
    d.line([(m, int(h * 0.42)), (m + avail, int(h * 0.42))], fill=(70, 80, 110), width=3)

    y = int(h * 0.48)
    for label, key in (("事業内容", "business"), ("志願者", "profile")):
        val = (brief.get(key) or "").strip()
        if not val:
            continue
        d.text((m, y), label, font=pick_font(int(h * 0.034)), fill=SUB)
        fv = fit_font(d, val, avail, int(h * 0.055))
        d.text((m, y + int(h * 0.045)), val, font=fv, fill=LINE)
        y += int(h * 0.15)
    return img


def render_point(text: str, size: tuple[int, int] = (1920, 1080)) -> Image.Image:
    """論点カード。映像に重ねるので下部の帯だけを描いた透過画像を返す。"""
    w, h = size
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    band_h = int(h * 0.17)
    top = h - band_h - int(h * 0.06)
    d.rectangle([0, top, w, top + band_h], fill=(17, 21, 34, 225))
    d.rectangle([0, top, int(w * 0.012), top + band_h], fill=ACCENT + (255,))

    m = int(w * 0.05)
    f = fit_font(d, text, w - m * 2, int(h * 0.062))
    b = d.textbbox((0, 0), text, font=f)
    d.text((m, top + (band_h - (b[3] - b[1])) // 2 - b[1]), text, font=f,
           fill=LINE + (255,))
    return img


def render_verdict(verdict: dict, size: tuple[int, int] = (1920, 1080)) -> Image.Image:
    """判定カード。誰がいくら出したか。決裂ならその理由。"""
    w, h = size
    img = Image.new("RGB", size, BG)
    d = ImageDraw.Draw(img)
    m = int(w * 0.09)
    avail = w - m * 2

    result = (verdict.get("result") or "").strip()
    f = fit_font(d, result, avail, int(h * 0.15))
    d.text((m, int(h * 0.26)), result, font=f, fill=ACCENT)
    d.line([(m, int(h * 0.48)), (m + avail, int(h * 0.48))], fill=(70, 80, 110), width=3)

    detail = (verdict.get("detail") or "").strip()
    if detail:
        fd = fit_font(d, detail, avail, int(h * 0.06))
        d.text((m, int(h * 0.56)), detail, font=fd, fill=LINE)
    return img
```

- [ ] **Step 4: 実行して成功を確認する**

Run: `python -m pytest tests/test_cards.py -v`
Expected: PASS（5件）

- [ ] **Step 5: 見た目を目視で確認する**

```bash
python -c "from scripts.cards import *; import pathlib; pathlib.Path('work/_cards').mkdir(parents=True, exist_ok=True); render_brief({'amount':'希望金額 500万円','business':'サウナ付きコワーキング','profile':'元大手不動産・28歳'}).save('work/_cards/brief.png'); render_point('原価が見えていないのに値付けはできない').save('work/_cards/point.png'); render_verdict({'result':'ALL 成立','detail':'林社長 200万円 / 岩井社長 300万円'}).save('work/_cards/verdict.png')"
```

`work/_cards/` の3枚を開いて確認する。**文字が枠から溢れていないこと**、
帯の透過が効いていることを見る。溢れていれば `fit_font` の初期サイズを下げる。

- [ ] **Step 6: コミット**

```bash
git add scripts/cards.py tests/test_cards.py
git commit -m "図解カード（案件・論点・判定）の描画を追加"
```

---

### Task 7: 動画のビルド（build_clip.py）

**Files:**
- Create: `scripts/build_clip.py`
- Create: `tests/test_build_clip.py`

**Interfaces:**
- Consumes: `scripts.recipe.validate` / `build_description`、`scripts.cards`、`scripts.fetch_source.source_dir`
- Produces:
  - `preflight(recipe: dict, src_dir: Path) -> list[str]` — 足りない素材の一覧（空なら開始可）
  - `probe_duration(path: Path) -> float` — ffprobe で実尺を返す
  - CLI: `python scripts/build_clip.py recipes/<id>.json [--dry-run]`

出力は `work/<id>/` に `video.mp4`・`thumb.png`・`description.txt`・`meta.json`。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_build_clip.py`:

```python
import json

import pytest

from scripts.build_clip import preflight


def recipe() -> dict:
    return {
        "id": "t", "source_video_id": "vid",
        "source_url": "https://youtu.be/vid", "source_title": "元",
        "clip": {"start": 0.0, "end": 10.0},
        "cards": {"brief": {"amount": "500万円"}, "points": [], "verdict": {}},
        "title": "t", "expected_channel_id": "UC1",
    }


def test_素材が揃っていれば空リスト(tmp_path):
    (tmp_path / "source.mp4").write_bytes(b"x")
    (tmp_path / "subs.json").write_text("[]", encoding="utf-8")
    assert preflight(recipe(), tmp_path) == []


def test_足りない素材を全部列挙する(tmp_path):
    missing = preflight(recipe(), tmp_path)
    assert any("source.mp4" in m for m in missing)
    assert any("subs.json" in m for m in missing)


def test_clipが元動画より長ければ指摘する(tmp_path):
    (tmp_path / "source.mp4").write_bytes(b"x")
    (tmp_path / "subs.json").write_text("[]", encoding="utf-8")
    (tmp_path / "meta.json").write_text(
        json.dumps({"duration_sec": 5}), encoding="utf-8")
    assert any("尺" in m for m in preflight(recipe(), tmp_path))


def test_レシピ不備はValueErrorになる(tmp_path):
    r = recipe()
    r["cards"]["brief"]["amount"] = ""
    with pytest.raises(ValueError):
        preflight(r, tmp_path)
```

- [ ] **Step 2: 実行して失敗を確認する**

Run: `python -m pytest tests/test_build_clip.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.build_clip'`

- [ ] **Step 3: 実装する**

`scripts/build_clip.py`:

```python
#!/usr/bin/env python3
"""切り抜き動画をビルドする。

  python scripts/build_clip.py recipes/2026-08-10-example.json --dry-run
  python scripts/build_clip.py recipes/2026-08-10-example.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.cards import render_brief, render_point, render_verdict  # noqa: E402
from scripts.fetch_source import source_dir  # noqa: E402
from scripts.recipe import build_description, validate  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"

CARD_SEC = 4.0          # 案件カード・判定カードの表示秒数
POINT_SEC = 3.5         # 論点カードの表示秒数
DUR_TOLERANCE = 1.0     # ビルド後の尺の許容差（秒）


def preflight(recipe: dict, src_dir: Path) -> list[str]:
    """素材の実在をまとめて確認する。ffmpeg が途中で落ちるより先に出す。"""
    validate(recipe)

    missing = []
    for name in ("source.mp4", "subs.json"):
        if not (src_dir / name).exists():
            missing.append(f"{src_dir / name} が無い")

    meta_path = src_dir / "meta.json"
    if meta_path.exists():
        dur = json.loads(meta_path.read_text(encoding="utf-8")).get("duration_sec")
        if dur and recipe["clip"]["end"] > dur:
            missing.append(
                f"clip.end={recipe['clip']['end']} が元動画の尺 {dur} を超えている")
    return missing


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def build(recipe_path: Path, dry_run: bool = False) -> Path:
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    src = source_dir(recipe["source_video_id"])

    missing = preflight(recipe, src)
    if missing:
        for m in missing:
            print(f"! {m}")
        raise SystemExit("素材が足りないので中断する")

    start, end = recipe["clip"]["start"], recipe["clip"]["end"]
    length = end - start
    out = WORK / recipe["id"]

    if dry_run:
        print(f"[dry-run] {recipe['id']}")
        print(f"  切り出し {start:.1f}s - {end:.1f}s（{length:.1f}s）")
        print(f"  論点カード {len(recipe['cards'].get('points') or [])} 枚")
        print(f"  合計尺の見込み {length + CARD_SEC * 2:.1f}s")
        return out

    out.mkdir(parents=True, exist_ok=True)
    cards = out / "cards"
    cards.mkdir(exist_ok=True)

    brief = cards / "brief.png"
    verdict = cards / "verdict.png"
    render_brief(recipe["cards"]["brief"]).save(brief)
    render_verdict(recipe["cards"].get("verdict") or {}).save(verdict)

    body = out / "body.mp4"
    # 尺は -t で明示する。-ss と組み合わせても、入力側の丸めで伸びることがある
    subprocess.run(
        ["ffmpeg", "-y", "-ss", f"{start}", "-i", str(src / "source.mp4"),
         "-t", f"{length}", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-c:a", "aac", "-b:a", "192k", "-vf", "scale=1920:1080",
         "-r", "30", str(body)], check=True)

    # 論点カードを該当時刻に重ねる
    points = recipe["cards"].get("points") or []
    overlaid = body
    for i, p in enumerate(points):
        at = p["at"] - start
        if not (0 <= at < length):
            print(f"! 論点カード {i} の at={p['at']} が clip の外なので飛ばす")
            continue
        png = cards / f"point_{i}.png"
        render_point(p["text"]).save(png)
        nxt = out / f"_ov{i}.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(overlaid), "-i", str(png),
             "-filter_complex",
             f"[0:v][1:v]overlay=0:0:enable='between(t,{at},{at + POINT_SEC})'",
             "-c:a", "copy", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
             str(nxt)], check=True)
        overlaid = nxt

    # 前後にカードを静止画として付ける
    concat = out / "concat.txt"
    seg_brief = out / "_brief.mp4"
    seg_verdict = out / "_verdict.mp4"
    for png, seg in ((brief, seg_brief), (verdict, seg_verdict)):
        subprocess.run(
            ["ffmpeg", "-y", "-loop", "1", "-i", str(png),
             "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
             "-t", f"{CARD_SEC}", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-r", "30",
             str(seg)], check=True)

    concat.write_text("".join(
        f"file '{p.as_posix()}'\n" for p in (seg_brief, overlaid, seg_verdict)),
        encoding="utf-8")
    video = out / "video.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
                    "-c", "copy", str(video)], check=True)

    expected = length + CARD_SEC * 2
    actual = probe_duration(video)
    if abs(actual - expected) > DUR_TOLERANCE:
        raise SystemExit(f"! 尺が合わない: 期待 {expected:.1f}s / 実測 {actual:.1f}s")

    (out / "description.txt").write_text(build_description(recipe), encoding="utf-8")
    render_brief(recipe["cards"]["brief"], size=(1280, 720)).save(out / "thumb.png")
    (out / "meta.json").write_text(json.dumps({
        "id": recipe["id"],
        "title": recipe["title"],
        "tags": recipe.get("tags") or [],
        "category_id": recipe.get("category_id", "22"),
        "privacy_status": recipe.get("privacy_status", "private"),
        "expected_channel_id": recipe["expected_channel_id"],
        "source_url": recipe["source_url"],
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"✓ {video}  {actual:.1f}s")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("recipe", type=Path)
    ap.add_argument("--dry-run", action="store_true", help="素材確認と尺の試算だけ行う")
    a = ap.parse_args()
    build(a.recipe, a.dry_run)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 実行して成功を確認する**

Run: `python -m pytest tests/test_build_clip.py -v`
Expected: PASS（4件）

- [ ] **Step 5: 実データで1本ビルドする**

Task 2 で取得した動画のレシピを `recipes/` に書き、

```bash
python scripts/build_clip.py recipes/<id>.json --dry-run
python scripts/build_clip.py recipes/<id>.json
```

`work/<id>/video.mp4` を再生して、カードの表示位置と尺を目視で確認する。

- [ ] **Step 6: コミット**

```bash
git add scripts/build_clip.py tests/test_build_clip.py
git commit -m "切り抜き動画のビルド（カット＋図解カード合成）を追加"
```

---

### Task 8: アップロード

**Files:**
- Create: `scripts/upload_youtube.py`（`bgm-youtube/scripts/upload_youtube.py` からコピー）
- Create: `docs/daily-workflow.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: `work/<id>/` の `video.mp4` / `thumb.png` / `description.txt` / `meta.json`
- Produces: CLI `python scripts/upload_youtube.py work/<id> [--publish]`、`state/published.json`

`bgm-youtube` 版は既に `meta.json` の `expected_channel_id` を見て
不一致ならアップロードしないガードを持っている（`upload_youtube.py:118-124`）。
これをそのまま活かす。BGM固有の処理（Content ID、バナー、ローカライズ）は削る。

- [ ] **Step 1: コピーして不要部分を削る**

```bash
cp ../bgm-youtube/scripts/upload_youtube.py scripts/upload_youtube.py
```

削るもの: `--banner`（`channelBanners.insert`）、`--localize`、BGM向けのタグ既定値。
残すもの: OAuth（`--auth-only`）、`expected_channel_id` ガード、`--publish`、
`thumbnails.set` の403を警告にとどめる処理、`state/published.json` への記録。

- [ ] **Step 2: ガードが効くことを確かめる**

`meta.json` の `expected_channel_id` を意図的に別の値にして実行する。

Run: `python scripts/upload_youtube.py work/<id>`
Expected: チャンネル不一致で中断し、**アップロードされないこと**

- [ ] **Step 3: 認証を通す**

Google Cloud（`bgm-youtube-504706` を流用可）で「デスクトップアプリ」の
`client_secret.json` を取得して直下に置き、

```bash
python scripts/upload_youtube.py --auth-only
```

ブラウザで**切り抜きチャンネルのGoogleアカウント**を選ぶ。`token.json` ができる。

- [ ] **Step 4: 運用手順を書く**

`docs/daily-workflow.md` に、Task 2〜8 のコマンド列と、
「**公開はガジェット通信の申請が通ってから**」を先頭に明記する。

- [ ] **Step 5: README の「状態」を更新する**

`README.md` の「## 状態」を「パイプライン実装済み。申請の可否待ち」に書き換える。

- [ ] **Step 6: コミット**

```bash
git add scripts/upload_youtube.py docs/daily-workflow.md README.md
git commit -m "アップロードを bgm-youtube から移植し、運用手順を追加"
```

---

## 自己レビュー結果

**仕様カバレッジ**: 仕様6章のパイプライン6段はTask 2〜8に対応。
7章の各コンポーネント仕様、8章の規約担保4項目（概要欄・チャンネルID・煽りガード・テンプレ使い回し）のうち
前2つはTask 5で強制。**後2つ（煽りガード・テンプレ使い回し）はコード化していない** —
これらはタイトル生成時の判断であり、レシピを書く時点の運用で担保する。
9章のエラー処理はTask 7の `preflight` / 尺検証、Task 2の字幕欠落チェックに対応。

**未着手として残すもの**: 仕様11章の未確定事項（チャンネル作成・分配率・チャンネル名）は
大島さんの判断待ちで、`expected_channel_id` はチャンネル作成後にレシピへ入れる。
