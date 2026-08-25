# 引き継ぎ

最終更新: 2026-08-25

## いま何をしているのか

Studio の数字を測ってベースラインを記録した（[docs/2026-08-25-baseline.md](docs/2026-08-25-baseline.md)）。
その流れで**未投稿ぶんの焼いた字幕を読んだら、ASRの崩れがそのまま入っていた**ので、
訂正表を入れてショート4本を作り直した。

**YouTube 側の操作は1つも通っていない。** 403 `quotaExceeded` で止まっている。
リセットは太平洋時間0時＝**JST 16:00**（2026-08-25 13:29 時点で PT は 08-24 21:29 だと確認）。

## 次にやること

### 1. クォータが戻ったら（JST 16:00 以降）、予約2本を差し替える

`akutsu-hantei-short`（8/26 12:00 JST 公開）と `imamura-ai-short`（8/27）は
**訂正前の字幕が焼かれた状態でアップロード済み**。作り直したものに差し替える。

```bash
python scripts/upload_youtube.py work/2026-08-20-akutsu-hantei-short --unschedule
python scripts/upload_youtube.py work/2026-08-20-imamura-ai-short   --unschedule
python scripts/upload_youtube.py work/2026-08-20-akutsu-hantei-short --schedule "2026-08-26T03:00:00Z"
python scripts/upload_youtube.py work/2026-08-20-imamura-ai-short   --schedule "2026-08-27T03:00:00Z"
```

- 旧ID `Atsm_3CKLx8`（akutsu-hantei-short）/ `irfzXTmIqQQ`（imamura-ai-short）
- `--unschedule` は予約を外して private のまま残し、`published.json` のエントリを
  `retired` に移す。**消さない**（消すと旧動画の行方が分からなくなる）
- **長尺2本は触らない。** 字幕を焼いていないので崩れは入っていない。8/26・8/27 の予約はそのまま
- 約 3,400ユニット（update 50×2、insert 1,600×2、サムネ 50×2）

### 2. 余ったぶんで未投稿の2組を上げる

**長尺が先。** ショートの概要欄が長尺のURLを持つので、長尺が `published.json` に
無いとショートは上がらない。

```bash
python scripts/upload_youtube.py work/2026-08-20-komazawa-ginkou       --schedule "2026-08-28T03:10:00Z"
python scripts/upload_youtube.py work/2026-08-20-komazawa-ginkou-short --schedule "2026-08-28T03:00:00Z"
python scripts/upload_youtube.py work/2026-08-20-yotsui-kakkoii        --schedule "2026-08-29T03:10:00Z"
python scripts/upload_youtube.py work/2026-08-20-yotsui-kakkoii-short  --schedule "2026-08-29T03:00:00Z"
```

**1日6本が上限。** 1と合わせるとちょうど埋まる。足りなければ `komazawa` を先に、
`yotsui` を翌日へ回す。

### 3. 8/29〜8/30 に効果を測る

8/26公開分が、作り直したショート（字幕焼き込み）の初回。

```bash
python scripts/report_stats.py --retention
```

比較の相手は [ベースライン](docs/2026-08-25-baseline.md) §2 の旧方式4本。
**見るのは再生数ではなく 25%地点の残存と高評価率。**
再生数はショートフィードの配信量に支配されていて、作りの差が出ない。

## 検証済みの事実

- **08-20公開分でショートの配信が始まった。** 08-10〜08-18公開の9本は6〜15再生（合計88）、
  08-20以降は707〜5,997再生。トラフィックは `SHORTS` が15,297再生で97%
- **こちらの変更では説明できない。** 08-14公開分から既に insert予約（`1ea2ff2`）で、
  それでも10〜15再生だった。ショートの尺も08-18と08-20で同じ66秒
- **累計23,012再生に対して登録者2人。** 期間中の純増+1。高評価率 0.14〜0.23%
- **長尺16本の合計再生は27**（最大6）。ショートが19,000再生を集めた期間中も0〜6のまま
- **ショート4本を作り直した。** `akutsu-hantei` / `imamura-ai` / `komazawa-ginkou` /
  `yotsui-kakkoii`。フレームを抜いて「低価格帯の居酒屋」「年商の高い社長」「駒澤さん」に
  直っていることを目視確認した
- `pytest` **166件すべて通る**（セッション開始時161件）
- `published.json` は無傷。34件のまま、予約も旧IDのまま動いていない

## 今回変えたもの

| ファイル | 何を |
| --- | --- |
| `docs/2026-08-25-baseline.md` | 新規。実測ベースライン |
| `scripts/report_stats.py` | 境目を `SHORTS_PICKUP = "2026-08-20"` に。`--retention` を追加 |
| `scripts/subtitles.py` | `unused_fixes` … キューをまたぐ訂正の見逃しを直した |
| `scripts/upload_youtube.py` | `retire()` と `--unschedule` を追加 |
| `recipes/2026-08-20-{akutsu-hantei,imamura-ai,komazawa-ginkou,yotsui-kakkoii}.json` | `fixes`（ASR訂正表） |
| `tests/test_burn.py` / `tests/test_publish_state.py` | +5件 |

コミット `9a22d01` / `6cfdc9f` / `ebda376`。

## 未検証のもの

- **作り直したショートが伸びるかは分からない。** 8/26公開分が出るまで測れない
- 08-20の断絶の原因。相関しか見ていない。インプレッション数は API に無く Studio の画面でしか見られない

## 触ってはいけないところ・保留中の判断

**音を聞かないと確定しないASRの崩れが残っている。** 裏取りできないものは
`recipe.fixes` に入れていない。**推測で足さないこと。**

| レシピ | 残っている崩れ |
| --- | --- |
| `akutsu-hantei` | 「めっちゃおろいや」「え、ごめんなさい。しょが」 |
| `imamura-ai` | 「ただ1点研したサービス」「今姉社長が」「いやいやいですか?」 |
| `komazawa-ginkou` | 「価確」（2箇所）「知持っております」「私もせていただきます」「津田さん」「紫さん」 |
| `yotsui-kakkoii` | 「リアルバリオー」「会社員さんみたいに」 |

`python scripts/build_short.py recipes/<id>.json --dry-run` で焼く字幕が全部出る。
`fixes` に足すと、当たらなかったものを `! recipe.fixes のうち当たらなかったもの` が名指しする。

**まだ相談していない判断:**

- **長尺が完全に死んでいる。** 作り方ではなく導線の問題。ショート概要欄の
  「フルで見る」からの流入は `EXT_URL` 5再生
- **23,012再生で登録者2人。** 転換がまったく起きていない
- ショートの概要欄が長尺のコピー。66秒の動画に「…15分です」と書いてある
  （`recipe["description"]` を長尺とショートが共用）
- `published.json` に無い private動画が6本（すべて 2026-08-10・0再生）
  `ZpsydtIqHm4` `wjoh-MPER6M` `-whIQ-8kiaw` `xcrKdusnOz0` `5LbLIA1YTw8` `cjeTzX5kFIw`
