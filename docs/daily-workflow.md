# 運用手順

> **公開はガジェット通信の申請が通ってからです。** 許諾前に公開すると無断転載になり、
> 削除・チャンネル停止の対象になります。申請フォームは
> <https://forms.gle/knE8kFVfjTgr7Qa89>（申請は大島さん本人が送信）。
> ビルドと private 投稿までは先行して構いません。

## 準備（初回だけ）

```bash
python -m pip install --user -r requirements.txt
```

`client_secret.json` を直下に置いてから認証を通します。
**同意画面では必ず切り抜きチャンネルのアカウントを選んでください。**

```bash
python scripts/upload_youtube.py --auth-only
```

表示されたチャンネルが `図解でわかる令和の虎`（`UCVrCOqLMVJhdciCFUSg0TOw`）であることを確認します。
違っていたら `token.json` を消してやり直してください。

## 1本作る

### 1. 本編を取る

```bash
python scripts/fetch_source.py --latest 5 --list
python scripts/fetch_source.py https://www.youtube.com/watch?v=<video_id>
```

`work/<video_id>/` に `source.mp4` / `subs.json` / `meta.json` が出ます。
44分の動画で約380MB、取得に1〜2分。

### 2. 信号を集める

```bash
python scripts/probe_signals.py <video_id>
```

音量の測定に尺の1割ほどかかります（44分で約35秒）。

ヒートマップは**新しい動画には存在しません**（実測で30本中7本のみ。
条件は「5万回以上」かつ「3週間以上経過」の両方）。無くても他の3信号で動きます。
過去回を掘るときだけ、ブラウザで取った `ytInitialData` を `--ytdata` で渡してください。

### 3. 候補を見る

```bash
python scripts/find_moments.py <video_id> --count 5 --length 420
```

候補と一緒に「金額の言及」が出ます。案件カードの下書きに使えますが、
**字幕はASRなので金額は必ず映像で裏取りしてください。** 令和の虎は金額が命です。

### 4. レシピを書く

`recipes/_example.json` をコピーして `recipes/<id>.json` を作ります。
`clip` は候補から選び、カードの中身は映像を見て書きます。

`cards.brief.amount` が空だとビルドが止まります。裏取り前の公開を防ぐためです。

### 5. ビルドする

```bash
python scripts/build_clip.py recipes/<id>.json --dry-run
python scripts/build_clip.py recipes/<id>.json
```

`work/<id>/video.mp4` を再生して、カードの位置と尺を目で確かめてください。

### 6. 投稿する

```bash
python scripts/upload_youtube.py work/<id>            # private
python scripts/upload_youtube.py work/<id> --publish  # 内容確認後に公開
```

`expected_channel_id` が一致しないとアップロードしません。

## 気をつけること

- **概要欄の冒頭の元動画URL・タイトルは自動で入ります。** 手で書かないでください
- **タイトル・概要欄・タグをテンプレの使い回しにしないこと。** YouTube の
  Inauthentic content ポリシーの対象になります
- **煽りサムネと誹謗中傷は禁止**（権利者ガイドライン）
- 収益化には YPP の条件に加えて再利用コンテンツ審査があります。
  図解カードが「元の配信に無い独自の付加価値」の根拠になるので、
  **カードを省いた手抜き版を出さないでください**

## チャンネル

| 項目 | 値 |
| --- | --- |
| チャンネル | 図解でわかる令和の虎【令和の虎Second 切り抜き】 |
| チャンネルID | `UCVrCOqLMVJhdciCFUSg0TOw` |
| ハンドル | `@zukai-reiwanotora` |
| Googleアカウント | `oshima6.27@gmail.com` |
| 切り抜き元 | 令和の虎Second（`UC9cD37sXfBNCQpz3vINa3TA`） |

チャンネルアートを作り直すときは `python scripts/build_brand.py --guide`。
