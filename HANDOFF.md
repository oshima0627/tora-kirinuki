# 引き継ぎ

最終更新: 2026-10-11（JST 14時台）

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
- **OAuth 整備済み**: 直下の client_secret.json / token.json（このチャンネル専用・commit しない）で audit・アップロードとも box で動く（2026-10-11 確認）。失効したら box のブラウザで `python scripts/upload_youtube.py --auth-only`（localhost:8765、`TORA_OAUTH_PORT`）→ UCWupHXqf8CTG00c_eoQSw1Q を確認
- 2026-10-10 検証: Cookie 無しで OpdXqtb73Uc を 1080p h264 取得（49秒）→ find_short → build_short（仮レシピ /tmp、1080x1920 55.4s、日本語フォント描画を3秒フレームで確認）。pytest 276 passed。OpdXqtb73Uc は取得のみ・未使用（box の work/ に source あり）

## レシピ方針（日次）

未使用レシピ在庫が無い、または note 不足で使えないときは**人手待ちにしない**。日次フロー内で find_moments / find_short 等からレシピを新規作成してから短長を進める。使える在庫レシピがあればそれを優先。禁止素材（R05BBh55p_U、xfr6w7g_Xucの34分以降、HowwrqNF9gw など）は維持。

## いま何をしているのか

**日次運用を2本に分割済み。** (1) 朝の日次制作 毎日14:07・関連動画なし・短長同一18:30同時予約 (2) 夕方の関連動画紐づけ 毎日18:35・当日同士のみ Studio 関連動画。前日付け替えはしない。概要欄フル導線は朝側の補助。

2026-10-11 分を box で新規予約済み（box 移行後の初回）。10/4・10/5・10/9・10/10 は ASUS_i9 オフラインのため欠番のまま（後追いで埋めていない）。

## 今回やったこと（2026-10-11、box で実施）

| やったこと | 結果 |
|---|---|
| YouTube 実状態を確認（audit_account.py、box の token.json） | 当日 10/11 の 18:30 枠は無し。最新は 10/8 短長（BkoqZX1Bdyo / rX6EE71ZfeE） |
| 未使用レシピ在庫 | 無し → 新規作成 |
| 新規本編 | `OpdXqtb73Uc`（普久原 朝晃／関西版85人目、56:49）。10/10 に box で取得済みだった source を使用 → probe_signals → find_moments / find_short |
| レシピ作成 | recipes/2026-10-11-fukuhara-okinawa-iten.json |
| 長尺ビルド・予約 | tdrGWzcdS5w / 18:09（1088.9s） / 18:30 JST |
| ショートビルド・予約 | D264-X_pNkg / 55.9秒 / 同一 18:30 JST。概要に ▼この回をフルで見る → tdrGWzcdS5w |
| ショートのタイトル | 当初「54秒」で上げたが実尺55.9秒なので sync_metadata で「56秒」に直した（動画IDは不変） |
| Studio 関連動画 | 朝ジョブでは触らない（夕方 18:35 ジョブ担当） |

| 公開 | 種別 | 動画ID | 尺 | 素材 |
|---|---|---|---|---|
| 10/11 18:30 | 長尺 | tdrGWzcdS5w | 18:09 | OpdXqtb73Uc 100.0-1188.9 |
| 10/11 18:30 | ショート | D264-X_pNkg | 55.9s | OpdXqtb73Uc 1082.8-1138.6（レシピ 1085.0 から文頭へ巻き戻し） |

長尺の区間: 名前・希望額（1:44）→ 事業プランを聞かれて言葉が出ない → 赤字の沖縄料理店・移転プラン・介護撤退の経緯・実家のヤギ料理店 → 児島社長登場 → そば実食（評価が割れる・1250円は普通すぎる）→ 持参のお酒 → 収支表の原価一定を突かれ「ミスってます」→ SNS 未記載・「何しに来たんですか？」「出してもらいに来ました」→ 自己資金ゼロなら本気で取りに来るべき、まで。19:49「どれぐらい赤字あるんですか」の手前で止めた。
ショート: 「そこを説明してもらえますか？」〜「ミスってます」→ SNS 未記載・本気度 → 「何しに来たんですか？」「出してもらいに来ました」→「ずっと緩く生きてきたんでしょうね」「今のとこ感じないです」まで。

## 次にやること

1. **夕方ジョブ（10/11 18:35 JST）** — 当日短長同士（ショート D264-X_pNkg → 長尺 tdrGWzcdS5w）を Studio 関連動画に紐づけ。前日付け替えはしない
2. **10/12 の日次制作（14:07 JST、box）** — 当日枠が無ければ短長を作り 18:30 JST 同時予約
3. 在庫（取得済み・未使用区間）: `OpdXqtb73Uc` の 1189-末尾（赤字月340万・借金の内訳・介護も失敗という指摘・「経営者やめた方がいい」・最終判定＝竹之内社長の450万円で不成立とその後の虎同士の口論 45:20-53:20）。**ただし 26:00-28:00 と 31:40-32:40 は志願者の持病（双極性障害）に触れるので切らない**。最終判定区間の 1枠目コメントにも病気への言及が一言ある
4. 次の新規本編候補（未取得・未使用）: `5s7XkDJBy_M` 与儀・SNS版、`gnRv7TEMx38` 青山・二軍版、`yS7uaXYMbUY` なみえ社長・SNS版（夜職求人。名誉面に注意）、`b5IM6DYa-DA` たくみなかう・社長ファイトクラブ版、`KJSteWkUr90` 田村前編・事業再生版、`oJjxzDAKEnw` 藤田・シン美容版 など。box の work/ には OpdXqtb73Uc の source しか無い（ASUS_i9 側の取得済み素材は box に無いので、在庫区間を使うなら再取得が要る）
5. 瀬戸前編 `_I2BzfLSZxs`・カルロス前編 `JGJkr2vm2ic` は使い切り

## 触ってはいけないところ

- **「公式」「公認」と書かない。** 令和の虎Channel / Youth は切らない
- **アップロードは --schedule を未アップロードに直接付ける。** 先上げてから入れ直さない（クォータ）
- **1日6本まで。** 回復は JST 16:00 前後（太平洋時間0時）
- **HowwrqNF9gw（VEALL）** はそのまま切ると名誉を害しやすい
- **R05BBh55p_U（岩谷）** は元字幕が語中改行するので使わない
- **xfr6w7g_Xuc（駒澤）の34分以降**（恋愛遍歴）は外す
- head は元テロップとも字幕とも別の言葉にする。ビルド後に3秒フレームを見ること
- build_clip の preflight は案件カード事業内容が2行に収まらないと「素材が足りない」で止まる
- 論点カードの1枚目は clip.start から8秒ほど後ろに置く（案件カードと被らないように。今回 60→68）
- **thumb.faces の x は「元フレーム内の顔の横位置」。** 今回は左 x 0.37 / bias 0.12 / crop_top 0.16、右 x 0.5 / bias 0.28 / crop_top 0.15 / crop_bottom 0.28（名前カードを落とす）で収まった
- **タイル画像（ffmpeg fps=1/2 + drawtext pts）のラベル秒は数秒ずれることがある。** thumb.faces.at はラベルを信用せず、build_clip と同じ `ffmpeg -ss <秒> -i source.mp4 -frames:v 1` で単発に抜いて確かめる（今回 943 と書いたら三原が出た）
- **fixes は部分一致置換。** 「原君→三原君」のような訂正は「三原君」を「三三原君」にするので入れない
- **JGJkr2vm2ic の志願者は白Tシャツの坊主の男性（カルロス）。** 眼鏡にネクタイの男性は進行役。取り違えない
- カルロス回は志願者が強く詰められる回。タイトル・サムネは「準備不足」と虎の一言を軸にし、本人の経歴・無償運営の実績・虎の代案（体験会→リフォーム集客）も区間に残して詰めだけの編集にしなかった

## 検証済みの事実（2026-10-11）

- API で tdrGWzcdS5w / D264-X_pNkg の publishAt=2026-10-11T09:30:00Z・privacy private・channel UCWupHXqf8CTG00c_eoQSw1Q・defaultLanguage ja を確認。尺 PT18M9S（1088.9s）/ PT56S（55.9s）。両方 uploadStatus processed・processingStatus succeeded
- ショート概要に ▼この回をフルで見る → tdrGWzcdS5w を API で確認
- 台帳 state/published.json に両方 thumbnail_set=true・publish_at 2026-10-11T09:30:00Z で記録
- 焼き込みテロップで確認: 志願者「普久原 朝晃 (44歳)」「沖縄の人も沖縄じゃない人も本場沖縄の味が楽しめる場(BAR)や居酒屋を作りたい」、「500万円 投資」、帯「希望額500万円 残り500万円」、名前カード「児島 雄太 (40) 株式会社こじま 代表取締役」「坂口 貴徳 (39) 株式会社CHAINONエンターテイメント 代表」、テロップ「ミスってます」「SNSも書かれてない」「本気度が全く伝わらない」「愛想も悪い」「何をしに来た?」「お金を出してもらいに」
- 長尺冒頭 3/6/10秒フレーム: 案件カード → 本編、1枚目論点カード（108s）が案件カードと別に出ることを確認
- ショート 3秒フレーム: head「資料も準備も足りない／それでも来た理由は」・元画面テロップなし・下帯字幕で三重回避を確認
- 長尺サムネ（左＝志願者 1130s、右＝坂口 1104s）を目視。上端の帯テロップ・名前カード・希望額帯の映り込みなし（crop_top 0.17/0.16、右 crop_bottom 0.27 で消えた）。吹き出し被り警告は出るが顔の中心には被っていない
- タイル画像のラベル秒はやはりずれた（1124 を志願者と思ったら坂口だった）。thumb.faces.at は単発抜きで確認すること

## 未検証のもの

- 店舗の赤字・移転先・介護撤退の理由・そばのこだわり・1250円などの数字と経緯は ASR 字幕由来（概要欄では「本人の発言（自動字幕）」と明記）
- 「何しに来たんですか？」は坂口社長が映るカットにテロップが出ているが、タイトル・概要では話者名を付けていない
- fixes「酒の市社長→竹之内社長」は ASR の音から推定（1132s 付近に「竹之内」の名前カードが一瞬映る）。長尺の該当行のみ
