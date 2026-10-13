# 引き継ぎ

最終更新: 2026-10-13（JST 14時台）

## 実行環境（2026-10-10 移行）

**実行環境は box（共有Linux）の `/workspace/tora-kirinuki`。ASUS_i9 は不要。**

```bash
cd /workspace/tora-kirinuki && git pull && source box_setup.sh   # venv・deno・POトークン(:4416)を用意
python scripts/audit_account.py                                   # 当日枠の確認
python scripts/fetch_source.py --latest 25 --list
python scripts/fetch_source.py https://www.youtube.com/watch?v=<id>
python scripts/probe_signals.py <id>; python scripts/find_moments.py <id>; python scripts/find_short.py <id> --letterbox
python scripts/build_clip.py recipes/<recipe>.json; python scripts/build_short.py recipes/<recipe>.json
python scripts/upload_youtube.py work/<recipe> --schedule <UTC>; python scripts/upload_youtube.py work/<recipe>-short --schedule <UTC>
```

- box 固有の差分（環境変数で切替、Windows の既定は従来どおり）: フォントは Noto Sans CJK Bold（`TORA_FONT` で上書き）。Cookie は使わない（`TORA_COOKIES=<cookies.txt>` / `TORA_COOKIES_BROWSER`）。プレイヤーは `tv_simply,web_embedded`（`TORA_PLAYER_CLIENT`）、字幕は `web_embedded`（`TORA_CAPTION_CLIENT`）、形式は avc1+m4a（`TORA_FORMAT`。av01/251-1 は途中で403）。JS は deno（~/.deno/bin。node 20 は yt-dlp で unsupported）
- **OAuth 整備済み**: 直下の client_secret.json / token.json（このチャンネル専用・commit しない）で audit・アップロードとも box で動く（2026-10-13 確認）。失効したら box のブラウザで `python scripts/upload_youtube.py --auth-only`（localhost:8765、`TORA_OAUTH_PORT`）→ UCWupHXqf8CTG00c_eoQSw1Q を確認
- 2026-10-10 検証: Cookie 無しで OpdXqtb73Uc を 1080p h264 取得（49秒）→ find_short → build_short（仮レシピ /tmp、1080x1920 55.4s、日本語フォント描画を3秒フレームで確認）。pytest 276 passed。OpdXqtb73Uc は取得のみ・未使用（box の work/ に source あり）

## レシピ方針（日次）

未使用レシピ在庫が無い、または note 不足で使えないときは**人手待ちにしない**。日次フロー内で find_moments / find_short 等からレシピを新規作成してから短長を進める。使える在庫レシピがあればそれを優先。禁止素材（R05BBh55p_U、xfr6w7g_Xucの34分以降、HowwrqNF9gw など）は維持。

## いま何をしているのか

**日次運用を2本に分割済み。** (1) 朝の日次制作 毎日14:07・関連動画なし・短長同一18:30同時予約 (2) 夕方の関連動画紐づけ 毎日18:35・当日同士のみ Studio 関連動画。前日付け替えはしない。概要欄フル導線は朝側の補助。

2026-10-13 分を box で新規予約済み。10/4・10/5・10/9・10/10 は ASUS_i9 オフラインのため欠番のまま（後追いで埋めていない）。

## 今回やったこと（2026-10-13、box で実施）

| やったこと | 結果 |
|---|---|
| YouTube 実状態を確認（audit_account.py、box の token.json） | 当日 10/13 の 18:30 枠は無し。最新は 10/12 短長（dMB5FELv7dI / lqpewdDRZNw）で公開済み |
| 未使用レシピ在庫 | 無し → 新規本編を取得 |
| 新規本編 | `b5IM6DYa-DA`（たくみなかう／社長ファイトクラブ版12人目）。OpdXqtb73Uc 残りは病気言及・尺不足のため見送り |
| レシピ作成 | recipes/2026-10-13-takuminakau-himodasai.json |
| 長尺ビルド・予約 | I02o4TFDsdg / 15:04（903.7s） / 18:30 JST |
| ショートビルド・予約 | crXQB0SkGQw / 53.8秒 / 同一 18:30 JST。概要に ▼この回をフルで見る → I02o4TFDsdg |
| Studio 関連動画 | 朝ジョブでは触らない（夕方 18:35 ジョブ担当） |

| 公開 | 種別 | 動画ID | 尺 | 素材 |
|---|---|---|---|---|
| 10/13 18:30 | 長尺 | I02o4TFDsdg | 15:04 | b5IM6DYa-DA 346.8-1250.52 |
| 10/13 18:30 | ショート | crXQB0SkGQw | 53.8s | b5IM6DYa-DA 611.24-665.04（長尺区間内） |

長尺の区間: 自分が目立ちたい → 起業は後・再起にかけてくれる社長を探しに来た → YouTubeで十分なら起業しなくて良くない？ → 今もファン宅に入り浸り・恋愛感情なし → TikTokライブ月100万 → 「ヒモんなきゃいいじゃん。ダサいよマジで」 → 「ヒモはダサいとは思わない」→「じゃ、犬だ」／ペット → 閲覧50人・有名じゃない指摘 → 自己顕示欲求・自立の意思が見えない → YouTube業界への恩返し・PF案まで。判定は含まない。

ショート: 「いいよって言ってても…」〜「ダサいよマジで」〜「ヒモはダサいよな」まで。

## 次にやること

1. **夕方ジョブ（10/13 18:35 JST）** — 当日短長同士（ショート crXQB0SkGQw → 長尺 I02o4TFDsdg）を Studio 関連動画に紐づけ。前日付け替えはしない
2. **10/14 の日次制作（14:07 JST、box）** — 当日枠が無ければ短長を作り 18:30 JST 同時予約
3. 在庫（取得済み・未使用区間）: `b5IM6DYa-DA` の後半（約 1348-2247、判定含む候補）。`OpdXqtb73Uc` の最終判定以降（約 2748-末尾）は病気言及あり・慎重に。100–1188.9 と 1960–2740 は使用済み
4. 次の新規本編候補（未取得・未使用）: `5s7XkDJBy_M` 与儀・SNS版、`gnRv7TEMx38` 青山・二軍版、`yS7uaXYMbUY` なみえ社長・SNS版（夜職求人。名誉面に注意）、`KJSteWkUr90` 田村前編・事業再生版、`oJjxzDAKEnw` 藤田・シン美容版 など。box の work/ には OpdXqtb73Uc と b5IM6DYa-DA の source あり
5. 瀬戸前編 `_I2BzfLSZxs`・カルロス前編 `JGJkr2vm2ic`・普久原前半/中盤・たくみなかう前半（10/13）は使用済み

## 触ってはいけないところ

- **「公式」「公認」と書かない。** 令和の虎Channel / Youth は切らない
- **アップロードは --schedule を未アップロードに直接付ける。** 先上げてから入れ直さない（クォータ）
- **1日6本まで。** 回復は JST 16:00 前後（太平洋時間0時）
- **HowwrqNF9gw（VEALL）** はそのまま切ると名誉を害しやすい
- **R05BBh55p_U（岩谷）** は元字幕が語中改行するので使わない
- **xfr6w7g_Xuc（駒澤）の34分以降**（恋愛遍歴）は外す
- **OpdXqtb73Uc の 26:00-28:00 と 31:40-32:40** は志願者の持病（双極性障害）に触れるので切らない。最終判定1枠目コメント（2748付近）にも病気への言及あり
- head は元テロップとも字幕とも別の言葉にする。ビルド後に3秒フレームを見ること
- build_clip の preflight は案件カード事業内容が2行に収まらないと「素材が足りない」で止まる
- 論点カードの1枚目は clip.start から8秒ほど後ろに置く（案件カードと被らないように）
- **thumb.faces の x は「元フレーム内の顔の横位置」。** 吹き出し被り警告は bias を下げて外側へ寄せる
- **タイル画像（ffmpeg fps=1/2 + drawtext pts）のラベル秒は数秒ずれることがある。** thumb.faces.at はラベルを信用せず、build_clip と同じ `ffmpeg -ss <秒> -i source.mp4 -frames:v 1` で単発に抜いて確かめる
- **fixes は部分一致置換。** 「原君→三原君」のような訂正は「三原君」を「三三原君」にするので入れない
- **JGJkr2vm2ic の志願者は白Tシャツの坊主の男性（カルロス）。** 眼鏡にネクタイの男性は進行役。取り違えない

## 検証済みの事実（2026-10-13）

- API で I02o4TFDsdg / crXQB0SkGQw の publishAt=2026-10-13T09:30:00Z・privacy private・channel UCWupHXqf8CTG00c_eoQSw1Q・defaultLanguage ja を確認。長尺ローカル 903.7s（15:04）。ショートはローカル 53.8s（タイトルは54秒）
- ショート概要に ▼この回をフルで見る → I02o4TFDsdg を API で確認
- 台帳 state/published.json に両方を記録（upload 時）
- ショート 3秒フレーム: head「入り浸りを認めた直後／虎「ダサいよマジで」」・下帯字幕で確認
- 長尺冒頭 3秒: 案件カード表示を確認

## 未検証のもの

- TikTokライブの月収・閲覧数・チャンネル経歴などの数字は ASR 字幕由来（概要欄では「本人の発言（自動字幕）」と明記）
- 「ダサいよマジで」「じゃ、犬だ」の話者名はタイトル・概要では付けていない（焼き込みテロップで虎側と確認）
- アップロード直後は processing 中。公開前に processed / succeeded を再確認すること
