# tora-kirinuki

令和の虎Second（`@reiwanotora_second`）の切り抜き動画を制作して YouTube に投稿するパイプライン。

設計は [`docs/superpowers/specs/2026-08-09-tora-kirinuki-design.md`](docs/superpowers/specs/2026-08-09-tora-kirinuki-design.md)。

## 前提

**公開には権利者の許諾が要る。** 切り抜きはガジェット通信クリエイターネットワーク経由で
申請したチャンネルのみ許される。申請フォームは <https://forms.gle/knE8kFVfjTgr7Qa89>。
申請が通るまで動画を公開しない。

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
   ↓ recipes/<id>.json を作る
4. build_clip.py      カット + 図解カード合成       → work/<id>/video.mp4
5. upload_youtube.py  private → 内容確認 → --publish
```

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

## 状態

パイプライン実装済み・テスト64件。**公開は申請の可否待ち。**
