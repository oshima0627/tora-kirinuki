# 引き継ぎ

最終更新: 2026-08-26

## いま何をしているのか

**アカウントを調査した。結論: アカウント側は無傷で、原因は設定ではない。**
測った内容はすべて [docs/2026-08-26-account-audit.md](docs/2026-08-26-account-audit.md)。

前回（08-25）は「長尺が完全に死んでいる」「23,012再生で登録者2人」を未解決のまま
置いていた。その2つに数字がついた。

- **長尺はクリックされていないのではなく、表示されていない。**
  インプレッション 2,387 / CTR 3.1% / おすすめ由来 2.6% / ブラウジング機能 0.0%。
  CTR は正常域。サムネイルとタイトルを直しても母数が動かない
- **ショート 2.6万再生からの登録は 0人。** 28日で増えた1人は25再生の長尺から来ている
- **長尺への導線が物理的に無い。** カードのインプレッション0、終了画面0、
  概要欄リンク経由は期間全体で5再生

## 今回やったこと

| ファイル | 何を |
|---|---|
| `scripts/audit_account.py` | 新規。アカウントとチャンネルの状態を出す。書き込みはしない |
| `docs/2026-08-26-account-audit.md` | 新規。今回の測定結果すべて |
| `state/published.json` | `imamura-ai-short` を差し替え。旧 `irfzXTmIqQQ` は `retired` へ |

ワークツリーのブランチが初期コミットのままだったので `git merge main` で追いつかせた。

## 検証済みの事実（実際に画面に出したもの）

- `python -m pytest -q` → **172 passed**（前回161→166→172。今回テストは足していない）
- `python scripts/audit_account.py` の出力:
  - チャンネル public / isLinked true / longUploadsStatus allowed / 登録者3
  - **42本アップロード済み。うち8本が `published.json` に無い**
    （前回の引き継ぎの「6本」は誤り。`op5uGCFQJ5s` `FureBeVFerE` が漏れていた）
  - 42本すべて `madeForKids: false`、地域制限なし、埋め込み可、`uploadStatus: processed`
  - 長尺の再生合計 **26**、ショートの再生合計 **26,776**
- Studio の画面で確認:
  - **著作権の申し立て 0件**、削除リクエスト 0件、警告なし
  - 長尺の漏斗: インプレッション 2,387 / おすすめ 2.6% / CTR 3.1% / 視聴73 / 平均視聴時間 1:18
  - ショート: 視聴2.6万 / エンゲージビュー1.5万(57.7%) / 高評価48 / **登録者 —(0)**
  - 収益化: 有効な総再生時間 **0時間**/3,000、有効ショート視聴 2,994/300万（08/20時点）
- Analytics API:
  - 流入 `SHORTS` 20,712(97%) / `YT_SEARCH` 317 / `YT_CHANNEL` 78 / `EXT_URL` 5
  - 長尺6本の期間中の流入は**合計9再生**。おすすめ由来ゼロ
  - 日本100% / モバイル89% / 男性25〜54歳80%。**狙った層に届いている**
  - 共有 0件、`cardImpressions` 0
  - ショート残存(`Pi1SplRFskQ`): 25% 0.810 / 50% 0.641 / 75% 0.554 / 100% 0.373
- コメント全3件。うち1件が「切り抜き方が下手でどういう意味なのか全くわからない」
- `upload_youtube.py --unschedule` → `✓ 予約を解除しました: irfzXTmIqQQ（private のまま残ります）`
- `upload_youtube.py --schedule "2026-08-27T03:00:00Z"` →
  `✓ https://www.youtube.com/watch?v=U9FMPUTeZ-Y (private)` / `2026-08-27T03:00:00Z に自動公開されます`
- 差し替え後に `videos.list` で確認: 新 `U9FMPUTeZ-Y` は private + publishAt 08-27T03:00Z、
  旧 `irfzXTmIqQQ` は private + publishAt なし、長尺 `aPof751FH1U` は 08-27T03:10Z のまま無傷
- `published.json` は 34件のまま。`retired` に `irfzXTmIqQQ` が1件入った

### 8/26公開分は訂正前のまま出た。8/27ぶんは差し替えた

`Atsm_3CKLx8`（akutsu-hantei-short）は **2026-08-26T03:00:28Z = 12:00 JST に公開済み**。
前回の引き継ぎにあった差し替えは間に合わなかった。**焼き込み字幕は訂正前のまま公開されている。**
差し替えるなら公開済み動画の取り下げになるので、やるかどうかは相談してから。

`irfzXTmIqQQ`（imamura-ai-short / 8/27）は **13:05 JST に差し替え済み**（実行ログは §検証済み）。

## 次にやること

### 1. 未投稿の2組を上げる（クォータは JST 16:00 に PT日が変わる）

**長尺が先**（ショートの概要欄が長尺のURLを持つため）。

```bash
python scripts/upload_youtube.py work/2026-08-20-komazawa-ginkou       --schedule "2026-08-28T03:10:00Z"
python scripts/upload_youtube.py work/2026-08-20-komazawa-ginkou-short --schedule "2026-08-28T03:00:00Z"
python scripts/upload_youtube.py work/2026-08-20-yotsui-kakkoii        --schedule "2026-08-29T03:10:00Z"
python scripts/upload_youtube.py work/2026-08-20-yotsui-kakkoii-short  --schedule "2026-08-29T03:00:00Z"
```

**1日6本が上限**（10,000ユニット ÷ 1,600）。1と合わせるとちょうど埋まる。

### 2. 測っていない穴を2つ埋める

どちらも安く、次の判断に直接効く。

```bash
# 長尺がどこで切れているか（1:18 の内訳）。--retention はショート用なので長尺は未対応
python scripts/report_stats.py --retention
```

- **長尺の残存カーブ**を `elapsedVideoTimeRatio` で引く。平均視聴時間 1:18 が
  「冒頭で切れている」のか「途中まで見て抜ける」のかで打ち手が変わる
- **カードと終了画面**を1本に入れて、`cardImpressions` が0から動くかを見る。
  いま0なのは効果が無いからではなく、**置いていないから**

### 3. 相談したいこと（手を動かす前に）

数字が出たので、前回「まだ相談していない判断」と書いた3つは形が変わった。

- **長尺15本は、いまの作りのままでは露出が増えない。**
  平均視聴率8.6%を上げるか、長尺をやめるか。作り直しても表示2,387の母数は動かない
- **ショートは届いているが1人も登録に変わっていない。** 2.6万再生・エンゲージ57.7%で登録0。
  チャンネル名も出口も、いまのショートには入っていない
- 概要欄がショートと長尺で共用（`recipe["description"]`）。66秒の動画に「…15分です」と書いてある

## 触ってはいけないところ・保留中の判断

**音を聞かないと確定しないASRの崩れが残っている。推測で `recipe.fixes` に足さないこと。**

| レシピ | 残っている崩れ |
| --- | --- |
| `akutsu-hantei` | 「めっちゃおろいや」「え、ごめんなさい。しょが」 |
| `imamura-ai` | 「ただ1点研したサービス」「今姉社長が」「いやいやいですか?」 |
| `komazawa-ginkou` | 「価確」（2箇所）「知持っております」「私もせていただきます」「津田さん」「紫さん」 |
| `yotsui-kakkoii` | 「リアルバリオー」「会社員さんみたいに」 |

`python scripts/build_short.py recipes/<id>.json --dry-run` で焼く字幕が全部出る。

**`published.json` に無い private 動画が8本ある。**（6本ではない）
台帳に無いので差し替えも削除も手作業になる。すべて0再生。

```
ZpsydtIqHm4  cjeTzX5kFIw  5LbLIA1YTw8  xcrKdusnOz0  wjoh-MPER6M  -whIQ-8kiaw  (08-10)
op5uGCFQJ5s  FureBeVFerE                                                       (08-13)
```

**引き継ぎはフックで強制されている。** `SessionStart` でこのファイルが context に流し込まれ、
`Stop` で未pushかつ `HANDOFF.md` 未更新なら止まる。中身は `.claude/hooks/`、
判定のテストは `tests/test_hooks.py`。

## 未検証のもの

- **08-20 の配信断絶の原因は不明のまま。** ファイル仕様を前後で比べたが、
  `08-17` `08-18` `08-20` はすべて mov / 1080x1920 / 30fps / h264 / aac 2ch で同一。
  タグもタイトル形式も尺も同じ。こちら側の変更では説明できない
- 全動画に `suggestions.processingHints: ["nonStreamableMov"]`（faststart 未適用のMOV）。
  `processingStatus` は `succeeded`。**実害があるかは確かめていない**
- **作り直したショートが伸びるかは、まだ分からない。** 訂正版の初回公開は
  8/27 12:00 JST の `U9FMPUTeZ-Y`。比べる相手は
  [ベースライン](docs/2026-08-25-baseline.md) §2 ではなく、08-20以降の同じ配信条件の回。
  **見るのは再生数ではなく 25%地点の残存と高評価率**
- 「視聴者の種類（新規/リピート）」は Analytics API が 500 を返して取れない
