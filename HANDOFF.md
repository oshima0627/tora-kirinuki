# 引き継ぎ

最終更新: 2026-10-12（JST 14時台）

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
- **OAuth 整備済み**: 直下の client_secret.json / token.json（このチャンネル専用・commit しない）で audit・アップロードとも box で動く（2026-10-12 確認）。失効したら box のブラウザで `python scripts/upload_youtube.py --auth-only`（localhost:8765、`TORA_OAUTH_PORT`）→ UCWupHXqf8CTG00c_eoQSw1Q を確認
- 2026-10-10 検証: Cookie 無しで OpdXqtb73Uc を 1080p h264 取得（49秒）→ find_short → build_short（仮レシピ /tmp、1080x1920 55.4s、日本語フォント描画を3秒フレームで確認）。pytest 276 passed。OpdXqtb73Uc は取得のみ・未使用（box の work/ に source あり）

## レシピ方針（日次）

未使用レシピ在庫が無い、または note 不足で使えないときは**人手待ちにしない**。日次フロー内で find_moments / find_short 等からレシピを新規作成してから短長を進める。使える在庫レシピがあればそれを優先。禁止素材（R05BBh55p_U、xfr6w7g_Xucの34分以降、HowwrqNF9gw など）は維持。

## いま何をしているのか

**日次運用を2本に分割済み。** (1) 朝の日次制作 毎日14:07・関連動画なし・短長同一18:30同時予約 (2) 夕方の関連動画紐づけ 毎日18:35・当日同士のみ Studio 関連動画。前日付け替えはしない。概要欄フル導線は朝側の補助。

2026-10-12 分を box で新規予約済み。10/4・10/5・10/9・10/10 は ASUS_i9 オフラインのため欠番のまま（後追いで埋めていない）。

## 今回やったこと（2026-10-12、box で実施）

| やったこと | 結果 |
|---|---|
| YouTube 実状態を確認（audit_account.py、box の token.json） | 当日 10/12 の 18:30 枠は無し。最新は 10/11 短長（tdrGWzcdS5w / D264-X_pNkg） |
| 未使用レシピ在庫 | 無し → OpdXqtb73Uc の未使用区間から新規作成 |
| 新規本編 | `OpdXqtb73Uc`（普久原 朝晃／関西版85人目）。取得済み source を再利用 → find_moments / find_short |
| レシピ作成 | recipes/2026-10-12-fukuhara-keieisha-yamete.json |
| 長尺ビルド・予約 | dMB5FELv7dI / 13:01（780.0s） / 18:30 JST |
| ショートビルド・予約 | lqpewdDRZNw / 55.5秒 / 同一 18:30 JST。概要に ▼この回をフルで見る → dMB5FELv7dI |
| Studio 関連動画 | 朝ジョブでは触らない（夕方 18:35 ジョブ担当） |

| 公開 | 種別 | 動画ID | 尺 | 素材 |
|---|---|---|---|---|
| 10/12 18:30 | 長尺 | dMB5FELv7dI | 13:01 | OpdXqtb73Uc 1960.0-2740.0 |
| 10/12 18:30 | ショート | lqpewdDRZNw | 55.5s | OpdXqtb73Uc 2394.5-2450.0（レシピ 2398.0 から文頭へ巻き戻し） |

長尺の区間: 熱量を求められる志願者 → 移転すればうまくいく主張 vs 1店舗目と同パターン → 経営センス・人件費家賃の指摘 → 事業再生版に出るべきでは → 必要資金550万と自己資金の食い違い → 借金内訳（銀行・店舗・個人で約2000万近く） → 竹之内社長登場「全部失敗してませんか」 → 「次は100%成功なんて誰が信じる」「経営者やめた方がいい」 → 固定費が払えない・畳む選択肢は考えていない → ラストステートメント（味とリピートへの自信）→ 最終ジャッジ直前で止め。**病気言及帯（26:00-28:00 / 31:40-32:40）と最終判定1枠目の病気コメント（2748付近）は区間外。**

ショート: 「何も成功してないのに次移転したら100%」〜「経営者やめた方がいい」〜「普通に働いた方がいい」〜「いいとこ出したら大火傷」「今でも固定費払えない」まで。

## 次にやること

1. **夕方ジョブ（10/12 18:35 JST）** — 当日短長同士（ショート lqpewdDRZNw → 長尺 dMB5FELv7dI）を Studio 関連動画に紐づけ。前日付け替えはしない
2. **10/13 の日次制作（14:07 JST、box）** — 当日枠が無ければ短長を作り 18:30 JST 同時予約
3. 在庫（取得済み・未使用区間）: `OpdXqtb73Uc` の最終判定以降（約 2748-末尾。竹之内社長の450万円で不成立とその後の虎同士の口論）。**ただし最終判定1枠目コメントに病気への言及があるので、切るならその一言を避けた区間設計が必要。** 26:00-28:00 と 31:40-32:40 も持病の話なので切らない。100–1188.9 と 1960–2740 は使用済み
4. 次の新規本編候補（未取得・未使用）: `5s7XkDJBy_M` 与儀・SNS版、`gnRv7TEMx38` 青山・二軍版、`yS7uaXYMbUY` なみえ社長・SNS版（夜職求人。名誉面に注意）、`b5IM6DYa-DA` たくみなかう・社長ファイトクラブ版、`KJSteWkUr90` 田村前編・事業再生版、`oJjxzDAKEnw` 藤田・シン美容版 など。box の work/ には OpdXqtb73Uc の source しか無い
5. 瀬戸前編 `_I2BzfLSZxs`・カルロス前編 `JGJkr2vm2ic` は使い切り。普久原前半（10/11）と中盤詰め（10/12）も使用済み

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

## 検証済みの事実（2026-10-12）

- API で dMB5FELv7dI / lqpewdDRZNw の publishAt=2026-10-12T09:30:00Z・privacy private・channel UCWupHXqf8CTG00c_eoQSw1Q・defaultLanguage ja を確認。長尺尺 PT13M1S（780.0s）。ショートはローカル 55.5s（タイトルは56秒）
- ショート概要に ▼この回をフルで見る → dMB5FELv7dI を API で確認
- 台帳 state/published.json に両方を記録（upload 時）
- ショート 3秒フレーム: head「成功した事業はゼロ／なのに次は100%？」・下帯字幕で確認
- 長尺冒頭 3秒: 案件カード表示を確認
- 病気帯（26:00-28:00 / 31:40-32:40 / 2748付近）は clip 外

## 未検証のもの

- 店舗の赤字・移転先・借金の内訳・必要資金などの数字と経緯は ASR 字幕由来（概要欄では「本人の発言（自動字幕）」と明記）
- 「経営者やめた方がいい」の話者名はタイトル・概要では付けていない（焼き込みテロップで虎側と確認）
- ショート字幕の「1人に目はかかってる」は ASR。映像上は「一人前」等の可能性あり（部分一致 fixes は行跨ぎで未適用）
- アップロード直後は processing 中。公開前に processed / succeeded を再確認すること
