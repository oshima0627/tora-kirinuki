# 引き継ぎ（2026-08-24）

## いま何をしているのか

**視聴者コメントを受けてショートの切り出し方を作り直した。** 実装・テスト・
未投稿4本のビルドまで終わっている。**まだ1本もアップロードしていない。**

```
2026-08-19-akutsu-gyutan-short / nIulWMDR7dQ
[2026-08-22T13:32:15Z] @Tkkrchu: 「切り抜き方が下手でどういう意味なのか全くわからない」
```

チャンネルに付いた唯一のコメント。公開済み26本を `commentThreads.list` で
確認した（他は0件、`2026-08-20` の3本はコメント無効）。

## 検証済みの事実

- **投稿済み19本のうち18本が発話の途中から始まっていた**（`recipes/*.json` の
  `short.start` を `work/<src>/subs.json` と突き合わせて計測。最大ズレ +18.4秒）
- `akutsu-gyutan` は前提（「ちょっとある推理していいですか?」ほか）を10.6秒ぶん
  切り落とし、結論の接続詞「で、なんでかって言うと」から始まっていた
- 横クロップ（中央61%）で元動画のテロップが切れていた。フレームを抜いて確認、
  「マイナスな発言が多い」が「ナスな発言が多」になっていた
- `pytest` **161件すべて通る**（変更前は109件）
- 未投稿4本＋`akutsu-gyutan` を実ビルドし、フレームを抜いて目視確認した。
  元動画の名前カード（`林 尚弘(41) 令和の虎 二代目 主宰`）まで読める

## 変えたもの

| ファイル | 何を |
| --- | --- |
| `scripts/moments.py` | `rewind_to_topic_head()` … 開始点を文の頭まで最大15秒戻す |
| `scripts/subtitles.py` | `burn_plan()` / `risky_lines()` / `unused_fixes()` … 時間同期字幕の割り付け |
| `scripts/cards.py` | `render_short_caption()`、映像を16:9等倍（1080x608）に |
| `scripts/recipe.py` | `validate_short(recipe, cues)` … 字幕の有無と巻き戻し後の尺で判定 |
| `scripts/build_short.py` | 全面的に書き直し。`--dry-run` が焼く字幕を全部出す |
| `recipes/2026-08-19-akutsu-gyutan.json` | `fixes`（ASR訂正表）を追加 |

設計は [`docs/superpowers/specs/2026-08-24-short-comprehension-design.md`](docs/superpowers/specs/2026-08-24-short-comprehension-design.md)。

## 未検証のもの

- **実際に伸びるかどうかは分からない。** コメント1件への対処であり、
  再生数への効果は測っていない。公開後に `report_stats.py` で見ること
- 顔が小さくなることの是非。等倍にしたぶん縦型としての寄りは弱くなった

## 次にやること

### 1. 未投稿4本のアップロード（長尺4・ショート4）

`akutsu-hantei` / `imamura-ai` / `komazawa-ginkou` / `yotsui-kakkoii`。
ショートは新しい形でビルド済み。**長尺は 2026-08-20 のビルドのまま**（今回
長尺は触っていない）。**長尺を先に上げること**（ショートの概要欄が長尺のURLを持つ）。

```bash
python scripts/upload_youtube.py work/<id>       --schedule "<日>T03:10:00Z"   # JST 12:10
python scripts/upload_youtube.py work/<id>-short --schedule "<日>T03:00:00Z"   # JST 12:00
```

クォータは太平洋時間の0時（JST 16〜17時）に戻る。1日6本まで。

### 2. サムネイルの再試行（積み残し）

`RveQoV1zud4` ほか3件が 429（`uploadRateLimitExceeded`）で入っていない。

```bash
python scripts/upload_youtube.py --retry-thumbnails
```

### 3. `state/published.json` が実態とずれている

予約投稿が公開に変わっても `privacy_status` が `private` のまま。
`nIulWMDR7dQ` は実際には公開されている（コメントが付いている）。

## 触ってはいけないところ

- **投稿済み19本は作り直さない。** 映像を差し替える手段が無く、上げ直すと
  動画IDが変わって再生数とコメントを失う
- **長尺（15分）の切り出し方は今回変えていない。** ショートの効果を見てから
- **`fixes` は必ず裏取りした語だけ入れる。** ASRの推測を焼くと誤情報になる

## 残っている課題

**元動画の要約テロップと自前のASR字幕が二重になることがある。**
`komazawa-ginkou` の実ビルドで、元テロップ「トレーナーを育てる知見も持ってる」と
自前の字幕「トレーナーを育てるっていうところの知持っておりま」が同時に出た。
**元動画のほうが正確。** 焼き込みテロップは読めないと検出できないので、
気づいたら `fixes` で直すか、区間をずらす。
