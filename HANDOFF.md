# 引き継ぎ

最終更新: 2026-08-26

## いま何をしているのか

**ショートの「関連動画」欄に長尺を紐づけた。公開済み16本は完了。残り3本は予約が明けてから。**

2.6万再生のショートから長尺へ26再生しか流れていない、という漏斗に対する打ち手。
概要欄のリンクは全部入っていたが、モバイル89%のショート視聴では概要欄が開かれない
（期間中の `EXT_URL` は5再生）。**Shorts の「関連動画」欄はプレイヤー本体に出る**ので、
置き場所が根本的に違う。

上級者向け機能の本人確認が通ったので、Studio で1本ずつ設定した。

## 今回やったこと

| ファイル | 何を |
|---|---|
| `scripts/audit_links.py` | 新規。ショートの概要欄に対応長尺のリンクがあるかを全数で出す。書き込みはしない |

YouTube Studio をブラウザで操作し、**公開済みショート16本の「関連動画」に対応する長尺を設定して保存**した。

## 検証済みの事実（実際に画面に出したもの）

- `python -m pytest -q` → **172 passed**（今回テストは足していない）
- **関連動画を設定した16本。全部、保存後に再読み込みして「関連動画」に長尺のタイトルが
  入っていることをスクリーンショットで確認した**（「なし」ではない）:

  | ショート | 長尺 | 台帳キー |
  |---|---|---|
  | `uJ7Flv8wHrE` | `VBYY-SU03uM` | horie-candle |
  | `-_jMpiDbvZU` | `EDRPTR5yGUs` | saito-mokutomo |
  | `sN5y77i04cs` | `9ngQ_04cv0k` | kawai-rehab |
  | `sH974Ldu3VU` | `VwO47R4gGsE` | higaki-library |
  | `YdwiWspfTSs` | `id6KrvcOzy0` | hayama-kyoudoukoubai |
  | `FM09y9dx2z4` | `K_eAlE4vS6o` | komazawa-fitness |
  | `1Kx7ecVFGhk` | `_COv48LWvT0` | imamura-revenge |
  | `vwXkHHnZU64` | `RSyPpzXCUiI` | mai-nushima |
  | `9NXyPfs-gqY` | `9L95DRUbMWg` | mai-teian |
  | `nIulWMDR7dQ` | `QFKFzKi3zuo` | akutsu-gyutan |
  | `Pi1SplRFskQ` | `axZrTqutD34` | yotsui-kyushoku |
  | `19nBjuV4evc` | `3Be5bKiduVY` | sakaguchi-cvc |
  | `BHhxA4jk7VU` | `xlqEPCrF6cI` | kawai-eigyou |
  | `Db824zUyJ3c` | `OsHhgXI5OgI` | hayama-torabattle |
  | `RveQoV1zud4` | `phatA361FTg` | higaki-nihanka |
  | `Atsm_3CKLx8` | `O3_81hOC0j4` | akutsu-hantei |

- **「特定の動画の選択」ダイアログは videoID で検索できる。** ID を入れると候補が1件だけ出る。
  タイトルで探すより安全（取り違えが起きない）
- **予約中（公開予約 = private）の長尺は候補に出ない。**
  `aPof751FH1U` を ID で検索 → 「一致する結果がありません」。
  タイトルの一部「今のうちに辞めた」で検索しても → 同じく0件。
  公開済みの長尺はどれも ID 検索で1件ヒットしたので、**非公開が候補から外れている**
- `python scripts/audit_links.py`: 動画48本 / 180秒未満24本。
  **台帳にあるショートは19本で、19本すべて概要欄に対応長尺のURLがある**
  （前のセッションで「20/20」と書いたのは数え違い。正しくは19）
- Studio の画面: 設定 > チャンネル > 機能の利用資格 で
  **3.上級者向け機能** が「利用資格あり」→ 本人確認後、関連動画の編集が可能になった
- `videos.list` を全パートで引いても**関連動画のフィールドは無い**。API からは読めない／設定できない

## 次にやること

### 1. 残り3本を、公開された日に設定する

**予約が明けて公開になってから**でないと候補に出ない。長尺の公開時刻は 12:10 JST。

| 設定するショート | 選ぶ長尺 | 長尺の公開 |
|---|---|---|
| `U9FMPUTeZ-Y` | `aPof751FH1U` | 2026-08-27 12:10 JST |
| `ji7bvZ1syLA` | `NSAi-BfomiU` | 2026-08-28 12:10 JST |
| `Yl3wV9uQnxU` | `B9iCtgqAZaY` | 2026-08-29 12:10 JST |

手順（1本あたり）:

```
studio.youtube.com/video/<ショートのID>/edit
→ 右カラム「関連動画」の鉛筆
→ 検索欄に長尺の videoID をそのまま入れる（1件だけ出る）
→ その1件をクリック
→ 右上「保存」（ダイアログが閉じきってから押す。グレーになれば保存済み）
```

**今後アップロードするショートも、公開後に同じ作業が要る。**
API では設定できないので、投稿手順に「公開日に関連動画を入れる」を足すこと。

### 2. 効果を測る

関連動画が効いているかは**長尺側**で見る。いま長尺の再生は合計26。

```bash
python scripts/report_stats.py
```

見るのは長尺の総再生と流入元。`YT_RELATED` が0から動くかどうか。
8/26に16本入れたので、8/28以降に差が出るはず。

### 3. 8/27〜8/29 の公開を見届ける

予約は 8/29 まで。**8/30以降の枠は空**（新しく作る素材が無い）。

```bash
python scripts/report_stats.py --retention
```

8/27公開の `U9FMPUTeZ-Y` が訂正版ショートの初回。比べる相手は 08-20以降の同じ配信条件の回
（`nIulWMDR7dQ` `Pi1SplRFskQ` `19nBjuV4evc` `BHhxA4jk7VU` `Db824zUyJ3c` `RveQoV1zud4`）。
**見るのは再生数ではなく 25%地点の残存と高評価率。**

### 4. まだ埋めていない穴

- **長尺の残存カーブ**を `elapsedVideoTimeRatio` で引く。平均視聴時間 1:18 が
  「冒頭で切れている」のか「途中まで見て抜ける」のかで打ち手が変わる
- **カードと終了画面**を1本に入れて `cardImpressions` が0から動くか見る。
  いま0なのは効果が無いからではなく、**置いていないから**

## 触ってはいけないところ・保留中の判断

**Studio の保存はダイアログが閉じきる前に押しても効かない。** 動画を選んだ直後に「保存」を
押すと、オーバーレイに吸われて無反応のまま「保存」が白（未保存）で残る。
**グレーになったことを必ず目で確認する。** 今回は2回押しが必要な回が多かった。

**音を聞かないと確定しないASRの崩れが残っている。推測で `recipe.fixes` に足さないこと。**

| レシピ | 残っている崩れ |
| --- | --- |
| `akutsu-hantei` | 「めっちゃおろいや」「え、ごめんなさい。しょが」 |
| `imamura-ai` | 「ただ1点研したサービス」「今姉社長が」「いやいやいですか?」 |
| `komazawa-ginkou` | 「価確」（2箇所）「知持っております」「私もせていただきます」「津田さん」「紫さん」 |
| `yotsui-kakkoii` | 「リアルバリオー」「会社員さんみたいに」 |

`python scripts/build_short.py recipes/<id>.json --dry-run` で焼く字幕が全部出る。

**`published.json` に無い private 動画が8本ある。**（ショート4・長尺4のペア）
台帳に無いので差し替えも削除も手作業になる。すべて0再生。**関連動画は入れていない。**

```
ZpsydtIqHm4  cjeTzX5kFIw  5LbLIA1YTw8  xcrKdusnOz0  wjoh-MPER6M  -whIQ-8kiaw  (08-10)
op5uGCFQJ5s  FureBeVFerE                                                       (08-13)
```

`irfzXTmIqQQ`（差し替えで retired にした旧ショート）にも入れていない。private のまま。

**`upload_youtube.py` はカレントディレクトリで台帳の場所が変わる。**
`ROOT = Path(__file__).parents[1]` なので、ワークツリーから実行すると
ワークツリー側の `state/published.json` を見る。本体側と食い違ったまま両方から
上げると、**同じ動画が二重にアップロードされる**（`yHxbK4Y05zI` で起きた）。
**実行は本体（`C:/Users/oshim/Documents/projects/tora-kirinuki`）からに統一する。**

**8/26公開の `Atsm_3CKLx8`（akutsu-hantei-short）は焼き込み字幕が訂正前のまま。**
差し替えるなら公開済み動画の取り下げになるので、やるかどうかは相談してから。

**引き継ぎはフックで強制されている。** `SessionStart` でこのファイルが context に流し込まれ、
`Stop` で未pushかつ `HANDOFF.md` 未更新なら止まる。中身は `.claude/hooks/`、
判定のテストは `tests/test_hooks.py`。

## 未検証のもの

- **関連動画を入れて長尺の再生が増えるかは、まだ分からない。** 入れたのが 8/26。
  効果を見るのはこれから
- **ショートのプレイヤー上で実際にリンクが出ているかを、視聴者の画面で見ていない。**
  確認したのは Studio の設定値だけ
- **08-20 の配信断絶の原因は不明のまま。** ファイル仕様は前後で同一
  （mov / 1080x1920 / 30fps / h264 / aac 2ch）。こちら側の変更では説明できない
- 全動画に `suggestions.processingHints: ["nonStreamableMov"]`（faststart 未適用のMOV）。
  `processingStatus` は `succeeded`。**実害があるかは確かめていない**
- 「視聴者の種類（新規/リピート）」は Analytics API が 500 を返して取れない
- **今日のクォータ消費は測っていない。** Studio の操作は Data API を使わないので
  クォータには乗らない。読み取りに使ったのは十数ユニット。
  確かめるなら Google Cloud コンソールの「YouTube Data API v3 > 割り当て」。
  PT日が変わるのは **JST 16:00**
