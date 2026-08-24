# tora-kirinuki

令和の虎Second（`@reiwanotora_second`）の切り抜き動画を制作して YouTube に投稿するパイプライン。

投稿先は [`@reiwanotora-second2`](https://www.youtube.com/@reiwanotora-second2)（図解でわかる令和の虎）。

- 設計: [`docs/superpowers/specs/2026-08-09-tora-kirinuki-design.md`](docs/superpowers/specs/2026-08-09-tora-kirinuki-design.md)
- チャンネル設定: [`docs/superpowers/specs/2026-08-10-channel-settings.md`](docs/superpowers/specs/2026-08-10-channel-settings.md)

## 前提

**2026-08-09 に申請が受理され、活動許可が出た。** 公開してよい。
ただし**収益化したら必ず <get-clip@razil.jp> へ連絡する**（無断で収益化するとペナルティ）。

権利者の立場は「あくまで**黙認**」。**「公式」「公認」とは書かないこと。**
守るべきルールと手順は [`docs/daily-workflow.md`](docs/daily-workflow.md)。
ガイドライン <https://reiwanotora.jp/clipping-guidelines/> は随時更新される。

| 項目 | 導入方法 |
| --- | --- |
| ffmpeg / ffprobe | `winget install Gyan.FFmpeg` |
| yt-dlp | `python -m pip install --user yt-dlp` |
| Python パッケージ | `pip install pillow google-api-python-client google-auth-oauthlib` |
| OAuth クライアント | Google Cloud で YouTube Data API v3 を有効化 →「デスクトップアプリ」→ `client_secret.json` を直下に配置 |

## パイプライン

```
1. fetch_source.py    本編DL + 日本語字幕 + メタ    → work/<video_id>/
2. probe_signals.py   音量 + 語彙 + コメント + 熱   → signals.json
3. find_moments.py    4信号の合成で候補区間を抽出   → candidates.json
   ↓ recipes/<id>.json を作る（長尺とショートで共有）
4. build_clip.py      横型・カット + 図解カード     → work/<id>/video.mp4
   build_short.py     縦型・巻き戻し + 時間同期字幕 → work/<id>-short/video.mp4
5. upload_youtube.py  private → 内容確認 → --publish
```

1つのレシピから**長尺とショートの両方**を作る。ショートで見つけてもらい、
長尺へ送る導線にしている。

手順は [`docs/daily-workflow.md`](docs/daily-workflow.md)。

## 切り抜き地点の探し方

当初は Most replayed ヒートマップを主軸に置いたが、実測で**30本中7本にしか
存在しない**と分かったため組み替えた（条件は「5万回以上」かつ「3週間以上経過」の
両方らしく、新着＝一番切り抜きたい動画では使えない）。

常に使える2つを主軸に、4信号を合成している。

| 信号 | 常時 | 性質 |
| --- | --- | --- |
| 音量スパイク | ○ | 量は多いがノイズも多い（最大スパイクが笑いの場面だった） |
| 字幕の語彙 | ○ | 詰め・判定は盛り上がり、金額は案件カードの材料 |
| コメント言及 | ほぼ○ | 件数は少ないが精度が高い |
| ヒートマップ | 23% | あれば加点 |

単純加算にはしていない。**音量と詰め語彙が10秒以内で同時に立つ箇所**を加点する。
片方だけなら笑い声や単なる言い回しの可能性が残るため。

## 同じ回から2本目を切る

**初期の8本は既定420秒で切っていたので、1回あたり25〜60分が手つかずで残っている。**
落とし直さずに在庫を作れるので、新しい回を取る前にここを掘るほうが早い。

```bash
python scripts/find_moments.py <video_id> --count 3 --length 900 --exclude-used
```

`--exclude-used` は `recipes/` から同じ `source_video_id` の `clip` を集めて、
そこにかかる候補を落とす。区間は1本の連続区間のままなので、ガイドラインの
「分割された本編を連結した投稿の禁止」には触れない。

区間の中身を読むには `show_subs.py` を使う。

```bash
python scripts/show_subs.py <video_id> 1909 2808 --every 30
```

## カードの文字数には上限がある

**`wrap(...)[:2]` は2行を超えた本文を黙って切り落とす。** 実際に事業内容が
「送客してもらう座」で終わったまま焼き込まれていた。いまは `build_clip.py` が
`--dry-run` の時点で名指しして止める。

| カード | 上限（全角） |
| --- | --- |
| 案件カードの事業内容・志願者 | 56文字 |
| 論点カード | 52文字 |
| 判定カードの詳細 | 3行（およそ78文字） |

金額と判定結果は `fit_font` で縮むので溢れない。

## ショートは「前提」から切る

**視聴者コメント「切り抜き方が下手でどういう意味なのか全くわからない」（2026-08-22）**
を受けて作り直した。実物を測ると、投稿済み19本のうち**18本が発話の途中から
始まっていた。** 信号のピークで切ると山の頂上に着地し、そこへ至る登り＝前提が
入らない。実例（`akutsu-gyutan`）では「ちょっとある推理していいですか?」も
その根拠も切り落とされ、**結論の接続詞「で、なんでかって言うと」から始まっていた。**

いまは `build_short.py` が3つを自動でやる。

| | 何をするか |
| --- | --- |
| 巻き戻し | `short.start` を直前の文の頭まで最大15秒戻す。相槌・接続詞では止まらない |
| 時間同期字幕 | 区間のASR字幕を1枚ずつ焼く（以前は1枚を全区間に重ねていた） |
| 等倍の映像 | 横のトリミングをやめる。元動画のテロップが読める |

`--dry-run` は**何秒戻したか・どの質で着地したか・焼く字幕の全文**を出す。

```bash
python scripts/build_short.py recipes/<id>.json --dry-run
```

着地は3段階（`文頭` / `境界` / `そのまま`）で申告する。`境界` と `そのまま` は
前提が入っていない可能性が高いので、区間を選び直すかどうかを人が決める。

## 横にトリミングしない

元動画は制作側が画面下いっぱいに要約テロップを、右下に名前カードを焼き込んでいる。
**これは理解の助けになる素材である。** 横を中央61%に詰めていたので、
実測で「マイナスな発言が多い」が「ナスな発言が多」に化けて画面中央に残っていた。

いまは 16:9 のまま 1080x608 で置く。顔は小さくなるが、名前カード
（`林 尚弘(41) 令和の虎 二代目 主宰`）まで読めるようになった。

## ASRの崩れはレシピの訂正表で直す

字幕はASRなので固有名詞が崩れる。実測で「阿久津さん→その悪さん」
「焼き鳥3級→焼き鳥産」。**数字が無いので機械では検出できない。**

```json
"fixes": { "その悪": "阿久津", "焼き鳥産": "焼き鳥3級" }
```

`--dry-run` は数字を含む行を名指しし、当たらなかった訂正も名指しする
（他の回から引き写した訂正が残っていると「直したつもり」になる）。

## サムネは絵だけ作り直せる

顔の切り取りは1回では決まらない。**元動画のテロップ（募集告知・名前カード・
会話テロップ）が残っていないかを実物で見て、`crop_top` / `crop_bottom` で潰す。**

```bash
python scripts/build_clip.py recipes/<id>.json --thumb-only
```

本編は再エンコードしないので数秒で終わる。

## 状態

パイプライン実装済み・テスト161件。申請受理済みで**公開可能**。
