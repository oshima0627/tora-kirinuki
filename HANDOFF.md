# 引き継ぎ

最終更新: 2026-08-28

## いま何をしているのか

**アナリティクスを確認した。結論は「今日は測れない」。**

8/27 に入れたもの（透かし・再生リスト・カード・終了画面）の効果を見に行ったが、
**Analytics に入っているデータは API で 2026-08-25、Studio で 2026-08-26 までしか無い。**
施策日より前で止まっている。0 が並ぶのは「効かなかった」ではなく「まだ入っていない」。

数字そのものは取り切った。**ショート 28,696 視聴に対して長尺 28 視聴（0.1%）。
導線はまだ繋がっていない。**

## 今回やったこと

- ワークツリー `channel-settings-investigation-5fc148` を main（6a3870b）に fast-forward。
  それ以前は 9f0c66f のままで `scripts/` が空だった
- `python scripts/report_stats.py --traffic` を実行
- Analytics API を直接叩いて、日別・長尺/ショート別・カード指標・再生場所を取得
  （スクラッチの使い捨てスクリプト。リポジトリには足していない）
- Studio のアナリティクス > コンテンツを、**すべて / 動画 / ショート / 再生リスト**の
  4フィルタすべてで実際に開いて読んだ

書き換えたファイルは `HANDOFF.md` だけ。**アカウント側は一切触っていない（読み取りのみ）。**

## 検証済みの事実（実際に画面に出した出力）

### いちばん大事なこと

**Analytics のデータは施策日（8/27）に届いていない。**

- API で `dimensions=day` を 08-18〜08-28 で引くと、**行は 08-25 で終わる。**
  08-26 / 08-27 / 08-28 は行そのものが無い
- Studio の「過去 28 日間」の表示は **2026/07/30〜2026/08/26**
- したがって `cardImpressions` も `RELATED_VIDEO` も `YT_PLAYLIST` も 0 だが、
  **これは施策の評価にならない。** 対象期間が施策より前

### API（最終日 2026-08-25）

| 区分 | 視聴 | 視聴分 | 平均視聴時間 | 登録 |
|---|---|---|---|---|
| 長尺 18本 合計 | **28** | 84 | 181秒 | +1 |
| ショート 18本 合計 | **28,696** | 11,112 | 39秒 | +4 |

- **長尺のトラフィック内訳**: `YT_SEARCH 18` `EXT_URL 4` `NO_LINK_OTHER 3` `YT_CHANNEL 3`（計28）。
  **`RELATED_VIDEO` も `YT_PLAYLIST` も `SUBSCRIBER` も行が無い＝0**
- 再生場所: `SHORTS_FEED 28677` / `WATCH 31` / `EMBEDDED 1`
- カード指標 全期間: `cardImpressions 0` `cardClicks 0` `cardTeaserImpressions 0` `cardTeaserClicks 0`
- チャンネル統計（`channels.list`・リアルタイム）: **登録者 6** / 総再生 36,454 / 動画 36
- 長尺の個別最高は `RSyPpzXCUiI` の 7 視聴。`id6KrvcOzy0` だけが登録を1人稼いでいる

### Studio（最終日 2026-08-26）

**「動画」フィルタ・全期間**（「過去28日間」と同値。チャンネルが28日未満なので）:

| 視聴回数 | サムネイルのインプレッション数 | サムネイルのクリック率 | 平均視聴時間 |
|---|---|---|---|
| 36 | **381** | **4.7%** | **2:32** |

- **視聴者が動画を見つけた方法**: YouTube検索 52.8% / **関連のショート動画 16.7%** /
  直接入力または不明 11.1% / 外部 11.1% / チャンネルページ 8.3%。
  **「関連動画」と「再生リスト」のボタンはグレーアウト（データ0）**
- 「再生リスト」フィルタ: **「この期間には表示できるデータがありません」**
- 「YouTube ショート」フィルタ・全期間: 視聴 3.4万 / エンゲージビュー 1.9万 / 高評価 69 / 登録 +2。
  **ショートにはインプレッション指標そのものが無い**
- 「すべて」フィルタ: 視聴回数 ショート 3.4万(99.9%) / 動画 36(0.1%)、
  登録 ショート+2・動画+1、新しい視聴者 ショート2・動画0、コアな視聴者 0

### 分かったこと

- **`cardImpressions` は Analytics API から取れる。** Studio を開く必要は無い。
  使えるメトリクス名: `cardImpressions` `cardClicks` `cardClickRate`
  `cardTeaserImpressions` `cardTeaserClicks` `cardTeaserClickRate`。
  前回の引き継ぎは「Studio 側で見る」と書いていたが、API で測れる
- **Studio に「関連のショート動画 16.7%」が出ている。** 長尺36視聴のうち約6。
  8/26 に入れた関連動画16本が効き始めた可能性がある。ただし
  **API の `insightTrafficSourceType` にこの区分は現れていない**（08-25 まででは
  `NO_LINK_OTHER 3` と `YT_CHANNEL 3` しかない）。対応関係は未確認
- **前回の「インプレッション 2,387」は今日の画面のどこにも再現できなかった。**
  動画=381、ショートにはインプレッション指標が無く、「すべて」にも出ない。
  **366（8/27）→ 381（8/28）は連続している。** 2,387 の出所は不明のまま
- 8/28 公開の長尺 `NSAi-BfomiU` は videos.list で **0 視聴**、ショートは 1,378 視聴

## 次にやること

### 1. 8/28 公開分を再生リストに流し込む（まだやっていない）

8/28 の `komazawa-ginkou` は公開済み。8/29 の `yotsui-kakkoii` は予約のまま private。

```bash
cd C:/Users/oshim/Documents/projects/tora-kirinuki
python scripts/sync_playlists.py          # 差分を見る
python scripts/sync_playlists.py --apply  # 入れる
```

**クォータは JST 16:00 に回復する。**

### 2. 8/30 以降にもう一度測る（今日できなかったこと）

データが 08-27 に届いてから。見るのはこの4つ:

```bash
cd C:/Users/oshim/Documents/projects/tora-kirinuki
python scripts/report_stats.py --traffic
```

| 見るもの | いまの値 | 期待 |
|---|---|---|
| `RELATED_VIDEO`（長尺） | 0 | 8/26の関連動画16本で動くか |
| `YT_PLAYLIST`（長尺） | 0 | 8/27の再生リスト3本で動くか |
| `cardImpressions` | 0 | 8/27のカード7本で動くか |
| Studio「関連のショート動画」 | 16.7% | 増えるか |

カード指標は API で取れる。`report_stats.py` に足すのが素直
（`metrics="cardImpressions,cardClicks,cardClickRate"`、dimensions なしで channel 合計）。

### 3. 関連動画をもう一度試す

8/27 は候補が0件で入れられなかった。今日は試していない。

```
studio.youtube.com/video/U9FMPUTeZ-Y/edit
→ 右カラム「関連動画」の鉛筆 → 検索欄に aPof751FH1U
→ 出た1件をクリック → 右上「保存」（グレーになれば保存済み）
```

| ショート | 長尺 |
|---|---|
| `U9FMPUTeZ-Y` | `aPof751FH1U` |
| `ji7bvZ1syLA` | `NSAi-BfomiU`（8/28公開済み） |
| `Yl3wV9uQnxU` | `B9iCtgqAZaY`（8/29公開予定） |

### 4. カードを残りの長尺9本にも入れる

APIには無いので Studio で1本ずつ。

| 指す先 | 動画 |
|---|---|
| 完全ALL成立回 | `EDRPTR5yGUs` `VBYY-SU03uM` `9ngQ_04cv0k` `K_eAlE4vS6o` `_COv48LWvT0` |
| 不成立 | `RSyPpzXCUiI` |
| 協力確約 | `QFKFzKi3zuo` `3Be5bKiduVY` `O3_81hOC0j4` |

```
studio.youtube.com/video/<ID>/edit
→ 右カラム「カード」の鉛筆（位置は動画ごとに違う。押す前に画面を見る）
→ 「再生リスト」の＋ → 一覧から選ぶ（検索は要らない）
→ 時刻を 0:45 に → ティーザーテキストを入れる → 右上「保存」
```

## 触ってはいけないところ・保留中の判断

**Studio に入るときは必ず
`studio.youtube.com/channel/UCWupHXqf8CTG00c_eoQSw1Q` から。**
ブラウザの既定チャンネルは別チャンネル（「日本の最新ニュースまるわかり」）。

**Studio 上部の「218 / 219 / 11.1K」は vidIQ 拡張の数字。登録者数ではない**（実際は6人）。

**Studio の保存はダイアログが閉じきる前に押しても効かない。**
「保存」がグレーになったことを目で確認する。
**カード編集で「＋」や再生リストのタイルを2回押すと2枚できる。** 1回押して待つ。

**`upload_youtube.py` はカレントディレクトリではなく `__file__` で台帳の場所を決める。**
ワークツリーから実行するとワークツリー側の `state/published.json` を見る。
**書き込む系（upload / sync_playlists --apply）は本体
（`C:/Users/oshim/Documents/projects/tora-kirinuki`）から実行する。**
読み取りだけの `report_stats.py` はどちらでもよい。

**`sync_playlists.py` は非公開の動画を入れない。** 予約公開の分は公開日に流し直す。
判定が「成立／不成立／協力確約」のどれにも当たらない回（`mai-teian`）は触らない。

**重複アップロード `yHxbK4Y05zI`（`NSAi-BfomiU` と同じ内容）が残っている。
削除は取り返しがつかないので相談してから。**

**8/26公開の `Atsm_3CKLx8`（akutsu-hantei-short）は焼き込み字幕が訂正前のまま。**
差し替えは公開済み動画の取り下げになる。やるかどうかは相談してから。

**音を聞かないと確定しないASRの崩れが残っている。推測で `recipe.fixes` に足さないこと。**

| レシピ | 残っている崩れ |
| --- | --- |
| `akutsu-hantei` | 「めっちゃおろいや」「え、ごめんなさい。しょが」 |
| `imamura-ai` | 「ただ1点研したサービス」「今姉社長が」「いやいやいですか?」 |
| `komazawa-ginkou` | 「価確」（2箇所）「知持っております」「私もせていただきます」「津田さん」「紫さん」 |
| `yotsui-kakkoii` | 「リアルバリオー」「会社員さんみたいに」 |

**8/30以降の公開枠は空**（新しく作る素材が無い）。予約は 8/29 まで。

**引き継ぎはフックで強制されている。** `SessionStart` でこのファイルが context に流し込まれ、
`Stop` で未pushかつ `HANDOFF.md` 未更新なら止まる。中身は `.claude/hooks/`。

## 未検証のもの

- **8/27 に入れたもの（透かし・再生リスト・カード・終了画面）の効果は今日も未測定。**
  Analytics が 08-25/26 で止まっているため。**8/30 以降**
- **Studio の「関連のショート動画 16.7%」が API のどのソース名に対応するかは未確認**
- **前回の「インプレッション 2,387」の出所は不明。** 今日は再現できなかった
- **終了画面が入っている長尺の全数は数えていない。** 分かっているのは
  `VwO47R4gGsE` `O3_81hOC0j4` `aPof751FH1U` の3本
- **終了画面が実際にプレーヤーに出ているかは見ていない**（透かしは 8/27 に目で確認済み）
- **カード7本のうち再読み込みで確認したのは `xlqEPCrF6cI` の1本だけ**
- 長尺の残存カーブ（`elapsedVideoTimeRatio`）は未測定
- 08-20 の配信断絶の原因は不明のまま
- 全動画に `suggestions.processingHints: ["nonStreamableMov"]`。実害は確かめていない
