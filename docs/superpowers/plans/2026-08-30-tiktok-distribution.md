# TikTok への配信 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 同じ縦型ショートを YouTube Shorts と TikTok の両方に出せるよう、尺の窓を 65〜73秒に固定し、手動投稿用の `caption.txt` を出す。

**Architecture:** 新しいビルダーもバリアント機構も作らない。`scripts/recipe.py` の `validate_short` に下限を1つ足し、推奨上限を下げ、`build_caption()` を新設する。`scripts/build_short.py` は出力を1ファイル増やすだけ。TikTok への投稿と記録は手作業（`state/tiktok.json`）。

**Tech Stack:** Python 3.13 / pytest（`pytest.ini` の `testpaths = tests`）/ ffmpeg・ffprobe

設計: [`docs/superpowers/specs/2026-08-30-tiktok-distribution-design.md`](../specs/2026-08-30-tiktok-distribution-design.md)

## Global Constraints

- **尺の窓は 65〜73秒。** 65秒未満はエラー、73秒超は警告、180秒超はエラー（据え置き）
- **尺は巻き戻し後の長さで測る。** `cues` を渡されたときは `rewind_to_topic_head` の着地点を起点にする
- **`state/published.json` には絶対に書かない。** YouTube 専用の台帳。TikTok は `state/tiktok.json`
- **YouTube Data API のクォータを1ユニットも使わない。** この計画にAPI呼び出しは無い
- **`CREDIT` の文言を変えない。** 現行は `"本チャンネルはガジェット通信クリエイターネットワークに申請済みの切り抜きチャンネルです。公式チャンネルではありません。"`
- **元動画のタイトルとURLは手書きさせない。** コードが必ず挿入する（権利者ガイドラインの必須条件）
- テスト実行は `python -m pytest` をリポジトリ直下で。`python -m pytest tests/test_short.py -v` のようにファイル指定も可
- **本体（`C:/Users/oshim/Documents/projects/tora-kirinuki`）で作業する。** ワークツリーは main から分岐していることがあるので、着手前に `git log --oneline -3` を見る

---

### Task 1: `SHORT_MIN_SEC` を入れる

65秒未満をエラーにする。既存フィクスチャ `with_short()` の既定は50秒なので、これを窓の中に直す。

**Files:**
- Modify: `scripts/recipe.py`（`SHORT_MAX_SEC` の定義の近く、および `validate_short` の尺判定）
- Test: `tests/test_short.py`

**Interfaces:**
- Consumes: `scripts.recipe.validate_short(recipe, cues=None)`（既存）、`tests.test_short.with_short(**over)`（既存）
- Produces: `scripts.recipe.SHORT_MIN_SEC: float = 65.0`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_short.py` の `test_3分を超えたら落ちる()` の直後に足す。

```python
def test_65秒未満は落ちる():
    # TikTok の収益化対象は1分以上。実測誤差の余裕を含めて65秒を下限にしている
    with pytest.raises(ValueError, match="65"):
        validate_short(with_short(start=2300.0, end=2364.9))


def test_巻き戻して65秒に届けば通る():
    # 尺はレシピの値ではなく巻き戻し後の長さで測る
    cues = cue_list((0.0, "前の話が終わりました。"), (5.0, "ここから話が始まります。"))
    validate_short(with_short(start=12.0, end=70.0), cues)
```

`cue_list` は同ファイルの後方で定義されている。Python は実行時に解決するので定義順は問題ない。

- [ ] **Step 2: 落ちることを確認する**

Run: `python -m pytest tests/test_short.py::test_65秒未満は落ちる -v`
Expected: FAIL（`DID NOT RAISE <class 'ValueError'>`）

- [ ] **Step 3: 定数を足す**

`scripts/recipe.py` の `SHORT_MAX_SEC = 180.0` の直後に足す。

```python
# TikTok の収益化対象は1分以上の動画。ffmpeg の実測誤差（DUR_TOLERANCE = 1秒）と
# TikTok 側の処理で数フレーム削られる分の余裕を取って65秒を下限にする。
# ギリギリを狙って対象外になるのがいちばん無駄なので、警告ではなくエラーにする
SHORT_MIN_SEC = 65.0
```

- [ ] **Step 4: 判定を足す**

`scripts/recipe.py` の `validate_short` 内、`if end - start > SHORT_MAX_SEC:` の**直前**に足す。

```python
    if end - start < SHORT_MIN_SEC:
        raise ValueError(
            f"short が {end - start:.1f}秒。TikTok の収益化対象は1分以上なので "
            f"{SHORT_MIN_SEC:.0f}秒を下限にしている")
```

`.1f` にするのは、64.9秒を `.0f` で出すと「short が 65秒。…65秒を下限にしている」と読めなくなるため。

- [ ] **Step 5: 新しいテストが通ることを確認する**

Run: `python -m pytest "tests/test_short.py::test_65秒未満は落ちる" "tests/test_short.py::test_巻き戻して65秒に届けば通る" -v`
Expected: 2 passed

- [ ] **Step 6: 巻き添えで落ちた既存テストを確認する**

Run: `python -m pytest tests/test_short.py -v`
Expected: 3 failed — `test_正しいショートは通る` / `test_字幕があれば通る` / `test_開始が発話の途中なら警告する`

いずれも `with_short()` の既定が 2300.0–2350.0（50秒）に依存している。

- [ ] **Step 7: フィクスチャの尺を窓の中に直す**

`tests/test_short.py` の `with_short()` の既定を 68秒にする。

```python
def with_short(**over) -> dict:
    r = base()
    # 既定は窓（65〜73秒）の中。下限を割ると validate_short が落ちる
    r["short"] = {"start": 2300.0, "end": 2368.0,
                  "hook": "粗利は1棟20万円。それでも満額200万円",
                  "head": HEAD, "quote": QUOTE}
    r["short"].update(over)
    return r
```

`test_字幕があれば通る()` は明示的に 2350.0 を渡しているので、そこも直す。

```python
def test_字幕があれば通る():
    cues = cue_list((2300.0, "ここから話が始まります。"), (2310.0, "続きです。"))
    validate_short(with_short(start=2300.0, end=2368.0), cues)
```

`test_開始が発話の途中なら警告する()` は巻き戻し後 55秒になるので 70秒にする。

```python
def test_開始が発話の途中なら警告する():
    cues = cue_list((0.0, "前の話が終わりました。"), (5.0, "ここから話が始まります。"))
    warnings = validate_short(with_short(start=8.0, end=75.0), cues)
    assert any("5.0" in w for w in warnings)
```

`test_区間に字幕が無ければ落ちる()` は 2350.0 のままでよい。字幕の判定が尺の判定より先に落ちるため。

- [ ] **Step 8: 全部通ることを確認する**

Run: `python -m pytest tests/ -v`
Expected: すべて PASS（失敗0）

- [ ] **Step 9: コミット**

```bash
git add scripts/recipe.py tests/test_short.py
git commit -m "追加: ショートの尺に65秒の下限を入れる

TikTokの収益化対象は1分以上。実測誤差の余裕を含めて65秒をエラーの下限にした。
尺は巻き戻し後の長さで測る。with_short() の既定が50秒だったので窓の中に直した。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: 推奨上限を 75 → 73秒 に下げる

**Files:**
- Modify: `scripts/recipe.py:58`（`SHORT_RECOMMENDED_SEC`）
- Test: `tests/test_short.py`

**Interfaces:**
- Consumes: Task 1 の `SHORT_MIN_SEC`
- Produces: `scripts.recipe.SHORT_RECOMMENDED_SEC: float = 73.0`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_short.py` の `test_推奨に収まれば警告は出ない()` の直後に足す。

```python
def test_73秒を超えたら警告になる():
    # 実測の高再生ゾーンは67〜73秒。103秒・132秒は0〜2再生だった
    from scripts.recipe import validate_short
    warnings = validate_short({"short": {"start": 0.0, "end": 74.0, "hook": "h"}})
    assert any("完走されにくい" in w for w in warnings)


def test_73秒ちょうどは警告しない():
    from scripts.recipe import validate_short
    assert validate_short({"short": {"start": 0.0, "end": 73.0, "hook": "h"}}) == []
```

- [ ] **Step 2: 落ちることを確認する**

Run: `python -m pytest "tests/test_short.py::test_73秒を超えたら警告になる" -v`
Expected: FAIL（74秒は現在の推奨 75秒に収まるので警告が出ない）

- [ ] **Step 3: 定数を下げる**

`scripts/recipe.py` の `SHORT_RECOMMENDED_SEC = 75.0` を書き換える。コメントの実測部分はそのまま残す。

```python
# 実際に伸びている競合の尺（2026-08-13 実測）。令和の虎塾のショートは67〜73秒で
# 公開1〜4日に3,925〜28,477再生、【忙しい人のための】は22〜37秒。
# こちらの103秒・132秒は0〜2再生だった。上限180秒に収まっていても長すぎる。
# 落とすほどではないので警告にとどめる（尺は素材で決まることもある）
# 2026-08-30: TikTok と共用する窓を 65〜73秒に決めたので 75.0 から下げた
SHORT_RECOMMENDED_SEC = 73.0
```

- [ ] **Step 4: 全部通ることを確認する**

Run: `python -m pytest tests/ -v`
Expected: すべて PASS

`test_巻き戻したぶんも警告の尺に含める()` は start=16.0 / end=81.0 で巻き戻し後 **76秒**。
下限65秒は満たし、推奨73秒は超えるので警告が出る。**このタスクでは壊れない。**

- [ ] **Step 5: コミット**

```bash
git add scripts/recipe.py tests/test_short.py
git commit -m "変更: ショートの推奨上限を75秒から73秒へ

実測の高再生ゾーン（令和の虎塾 67〜73秒で3,925〜28,477再生）の上端に合わせた。
TikTokと共用する窓を65〜73秒にするため。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: `build_caption()` を新設する

TikTok へ手で投稿するときに貼り付けるテキスト。元動画URLの挿入は `build_description()` と共通の関数に寄せ、手書きさせない担保を崩さない。

**Files:**
- Modify: `scripts/recipe.py`（`build_description` の直前に `_source_lines`、直後に `build_caption`）
- Test: `tests/test_recipe.py`

**Interfaces:**
- Consumes: `scripts.recipe.CREDIT`（既存）
- Produces:
  - `scripts.recipe._source_lines(recipe: dict) -> list[str]`
  - `scripts.recipe.build_caption(recipe: dict) -> str`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_recipe.py` の末尾に足す。1行目のインポートに `build_caption` を加える。

```python
from scripts.recipe import CREDIT, build_caption, build_description, validate
```

```python
def with_short_for_caption() -> dict:
    r = base()
    r["short"] = {"start": 2300.0, "end": 2368.0,
                  "hook": "粗利は1棟20万円。それでも満額200万円",
                  "title": "【令和の虎】粗利は1棟20万円 #令和の虎 #切り抜き"}
    return r


def test_キャプションの1行目はショートのタイトル():
    c = build_caption(with_short_for_caption())
    assert c.splitlines()[0] == "【令和の虎】粗利は1棟20万円 #令和の虎 #切り抜き"


def test_titleが無ければhookを使う():
    r = with_short_for_caption()
    del r["short"]["title"]
    assert build_caption(r).splitlines()[0] == "粗利は1棟20万円。それでも満額200万円"


def test_キャプションに元動画のURLが入る():
    # 権利者ガイドラインの必須条件。手書きさせない
    c = build_caption(with_short_for_caption())
    assert "https://www.youtube.com/watch?v=TuYYB2N0JGE" in c
    assert "【元動画】" in c


def test_キャプションにCREDITがそのまま入る():
    # CREDIT 自体が「公式チャンネルではありません」という否定文なので、
    # 「公式」の単純禁止では判定できない。文言がそのまま入っていることを見る
    assert CREDIT in build_caption(with_short_for_caption())


def test_キャプションの末尾はハッシュタグ():
    c = build_caption(with_short_for_caption())
    assert c.rstrip().endswith("#令和の虎 #切り抜き")


def test_概要欄にも同じ元動画行が入る():
    # _source_lines を共通化しても build_description が壊れないことを見る
    d = build_description(base())
    assert "【元動画】" in d
    assert "https://www.youtube.com/watch?v=TuYYB2N0JGE" in d
```

- [ ] **Step 2: 落ちることを確認する**

Run: `python -m pytest tests/test_recipe.py -v`
Expected: FAIL（`ImportError: cannot import name 'build_caption'`）

- [ ] **Step 3: 実装する**

`scripts/recipe.py` の `build_description` を書き換え、共通部分を抜き出して `build_caption` を足す。

```python
def _source_lines(recipe: dict) -> list[str]:
    """元動画のタイトルとURL。**概要欄にもキャプションにも必ず入れる。**

    権利者ガイドラインの必須条件なので、書き手に任せず1箇所で作る。
    """
    return [f"【元動画】{recipe['source_title']}", recipe["source_url"]]


def build_description(recipe: dict) -> str:
    """概要欄。冒頭の元動画URL・タイトルは手書きさせず、ここで必ず付ける。"""
    body = (recipe.get("description") or "").strip()
    tags = " ".join(f"#{t}" for t in (recipe.get("tags") or []))
    parts = [*_source_lines(recipe), "", body, "", CREDIT]
    if tags:
        parts += ["", tags]
    return "\n".join(parts).strip() + "\n"


def build_caption(recipe: dict) -> str:
    """TikTok へ手で投稿するときに貼り付けるテキスト。

    **概要欄（build_description）は YouTube 用の長文なので使わない。**
    TikTok の URL はリンクにならないが、元動画へのリンクは権利者ガイドラインの
    必須条件なので、意図として必ず書く。
    """
    short = recipe.get("short") or {}
    head = (short.get("title") or short.get("hook") or recipe["title"]).strip()
    tags = " ".join(f"#{t}" for t in (recipe.get("tags") or []))
    parts = [head, "", *_source_lines(recipe), "", CREDIT]
    if tags:
        parts += ["", tags]
    return "\n".join(parts).strip() + "\n"
```

- [ ] **Step 4: 通ることを確認する**

Run: `python -m pytest tests/ -v`
Expected: すべて PASS

- [ ] **Step 5: コミット**

```bash
git add scripts/recipe.py tests/test_recipe.py
git commit -m "追加: TikTok手動投稿用の build_caption()

元動画のタイトルとURLは _source_lines() に寄せ、概要欄とキャプションの
両方で必ず入るようにした。CREDIT はそのまま入れる。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: `build_short.py` が `caption.txt` を書く

**Files:**
- Modify: `scripts/build_short.py`（インポート行と、`description.txt` を書いている箇所）

**Interfaces:**
- Consumes: Task 3 の `scripts.recipe.build_caption(recipe) -> str`
- Produces: `work/<id>-short/caption.txt`

- [ ] **Step 1: インポートに足す**

`scripts/build_short.py` の該当行を書き換える。

```python
from scripts.recipe import (build_caption, build_description,  # noqa: E402
                            validate, validate_short)
```

- [ ] **Step 2: 書き出しを足す**

`(out / "description.txt").write_text(...)` の**直後**に足す。

```python
    # TikTok へは手で投稿する。貼り付けるテキストをここで出しておく
    (out / "caption.txt").write_text(build_caption(recipe), encoding="utf-8")
```

- [ ] **Step 3: 実際にビルドして確認する**

尺の窓に入っている既存レシピで実際に流す。`mai-namesugi` は 70.1秒で窓の中。

Run:
```bash
python scripts/build_short.py recipes/2026-08-29-mai-namesugi.json
```
Expected: `✓ ...\work\2026-08-29-mai-namesugi-short\video.mp4  70.1s  1080x1920  字幕29枚`

- [ ] **Step 4: caption.txt の中身を目で読む**

Run:
```bash
python -c "import sys,io; sys.stdout.reconfigure(encoding='utf-8'); print(io.open('work/2026-08-29-mai-namesugi-short/caption.txt',encoding='utf-8').read())"
```
Expected: 1行目にショートのタイトル、続いて `【元動画】…` と `https://www.youtube.com/watch?v=DSCYmCBAp_I`、`CREDIT`、末尾にハッシュタグ。

- [ ] **Step 5: 尺が変わっていないことを確認する**

**これが最重要。** 既存の出力が変わっていないことを見る。

Run:
```bash
ffprobe -v error -show_entries format=duration -of csv=p=0 work/2026-08-29-mai-namesugi-short/video.mp4
```
Expected: `70.133333`（この計画に着手する前の値と一致すること）

- [ ] **Step 6: 全テストを流す**

Run: `python -m pytest tests/ -v`
Expected: すべて PASS

- [ ] **Step 7: コミット**

```bash
git add scripts/build_short.py
git commit -m "追加: ショートのビルドで caption.txt を出す

TikTokへは手で投稿するので、貼り付けるテキストをビルド時に出しておく。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: `state/tiktok.json` と照会文、手順の追記

投稿と記録は手作業なのでスクリプトは書かない。空の台帳と、権利者への照会文の草案、運用手順への追記だけ作る。

**Files:**
- Create: `state/tiktok.json`
- Create: `docs/2026-08-30-tiktok-inquiry-draft.md`
- Modify: `docs/daily-workflow.md`（「守ること」の表の直後に節を足す）

**Interfaces:**
- Consumes: Task 4 の `work/<id>-short/caption.txt`
- Produces: なし（コードから読まない）

- [ ] **Step 1: 空の台帳を作る**

`state/tiktok.json`:

```json
{
  "videos": {}
}
```

- [ ] **Step 2: 照会文の草案を書く**

`docs/2026-08-30-tiktok-inquiry-draft.md`:

```markdown
# TikTok 投稿の可否を照会する（草案）

**大島さんご自身が送信してください。** 契約意思の表明にあたるため代理送信はしません
（2026-08-09 設計書の方針）。

宛先: get-clip@razil.jp
件名: 【切り抜き許諾】TikTokへの投稿可否についてのご相談（図解でわかる令和の虎）

---

ガジェット通信クリエイターネットワーク ご担当者様

いつもお世話になっております。
切り抜きチャンネル「図解でわかる令和の虎」
（https://www.youtube.com/@reiwanotora-second2 、チャンネルID: UCWupHXqf8CTG00c_eoQSw1Q）
を運営しております大島と申します。

令和の虎Second の切り抜きにつきまして、2026年8月10日に申請を受理いただき、
現在ガイドラインに沿って YouTube にて公開しております。

今回、同じ切り抜き動画を **TikTok にも投稿すること**が可能かどうかを
ご相談させてください。

- 投稿するのは YouTube に公開しているものと同一の縦型動画です
- 元動画のタイトルとURL、および「ガジェット通信クリエイターネットワークに
  申請済みの切り抜きチャンネルです。公式チャンネルではありません。」の記載は
  キャプションにも同様に入れます
- ロゴの使用、本編の連結、「マネーの虎」を想起させる表現は行いません

切り抜き運用レギュレーションを拝見しましたところ、投稿先のプラットフォームに
ついての記載を見つけられませんでした。許諾はチャンネル単位でいただいているものと
理解しておりますので、TikTok への投稿が許諾の範囲に含まれるか、
また別途申請が必要かをご教示いただけますと幸いです。

お手数をおかけしますが、よろしくお願いいたします。

（氏名・連絡先）
---

## 返事が来るまで

**投稿しない。** mp4 と caption.txt を作って貯めるだけ。
（作ることにリスクは無く、リスクは投稿にだけある）
```

- [ ] **Step 3: 運用手順に節を足す**

`docs/daily-workflow.md` の「## 守ること（受付メールとガイドラインより）」の表の直後、
「**1ヶ月に警告3回以上で…**」の行の**前**に足す。

```markdown
### TikTok への投稿は照会の返事が来るまでしない

ガイドラインに投稿先プラットフォームの記載は無いが、許諾はチャンネルID単位で、
権利者の立場は「黙認」。**下振れが YouTube 側の許諾ごと失うことになり得る。**

照会文の草案: `docs/2026-08-30-tiktok-inquiry-draft.md`

ビルドは止めない。`work/<id>-short/caption.txt` を貯めておき、返事が来てから
手で投稿し、`state/tiktok.json` に手で記録する。
**`state/published.json` には絶対に書かない**（YouTube 専用の台帳）。

**ショートの尺は 65〜73秒。** 65秒未満は `validate_short` が落とす
（TikTok の収益化対象が1分以上のため）。
```

- [ ] **Step 4: 何も壊れていないことを確認する**

Run: `python -m pytest tests/ -v`
Expected: すべて PASS（ドキュメントとJSONだけなので影響は無いはずだが、念のため）

- [ ] **Step 5: コミット**

```bash
git add state/tiktok.json docs/2026-08-30-tiktok-inquiry-draft.md docs/daily-workflow.md
git commit -m "追加: TikTokの台帳・照会文の草案・運用手順

投稿と記録は手作業なのでスクリプトは書かない。
照会の返事が来るまで投稿しない旨を daily-workflow.md に明記した。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## 着手前に済んでいること

**設計 6.2（`mai-namesugi` のショートを 43.0s → 70.1s に切り直す）は 2026-08-30 に実施済み。**
コミット `9ecb158`。Task 4 の検証で 70.1秒を期待値として使うのはこのため。

## 完了後の状態

- `python -m pytest tests/` が全 PASS
- 新規レシピで 65秒未満のショートを書くとビルド前に落ちる
- `work/<id>-short/` に `caption.txt` が出る
- `docs/2026-08-30-tiktok-inquiry-draft.md` が用意されている（送信は大島さん）
- **TikTok にはまだ1本も投稿していない**（照会の返事待ち）

## この計画でやらないこと

- TikTok Content Posting API の実装と審査申請（未審査だと `SELF_ONLY` でしか投稿できず、審査に2〜4週間かかる）
- `state/tiktok.json` を書くスクリプト
- 公開済みショートの差し替え（取り下げ扱いになる）
- 既存14本（65秒未満）の作り直し
