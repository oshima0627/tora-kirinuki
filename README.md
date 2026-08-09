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
2. probe_signals.py   Most replayed + コメント言及  → signals.json
3. find_moments.py    3点合成スコアで候補区間抽出   → candidates.json
   ↓ recipes/<id>.json を作る
4. build_clip.py      カット + テロップ + 図解カード → work/<id>/video.mp4
5. upload_youtube.py  private → 内容確認 → --publish
```

## 状態

設計のみ。実装はこれから。
