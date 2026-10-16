# 引き継ぎ

最終更新: 2026-10-16（JST 14時台・日次制作完了）

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
- **OAuth 整備済み**: 直下の client_secret.json / token.json（このチャンネル専用・commit しない）で audit・アップロードとも box で動く（2026-10-16 確認）。失効したら box のブラウザで `python scripts/upload_youtube.py --auth-only`（localhost:8765、`TORA_OAUTH_PORT`）→ UCWupHXqf8CTG00c_eoQSw1Q を確認
- 2026-10-10 検証: Cookie 無しで OpdXqtb73Uc を 1080p h264 取得（49秒）→ find_short → build_short（仮レシピ /tmp、1080x1920 55.4s、日本語フォント描画を3秒フレームで確認）。pytest 276 passed。OpdXqtb73Uc は取得のみ・未使用（box の work/ に source あり）

## 視聴者参加の方針（2026-10-15 承認・常設）→ [docs/engagement.md](docs/engagement.md)

- **朝の日次制作（自動）**: build_clip が長尺の冒頭（案件カード直後）と終盤（判定カード直前）に問いかけ帯を、build_short が最後の4秒に締めの問いを上帯に焼く。概要欄の1行目は問い、元動画タイトル・URLは2〜3行目。レシピ項目 `cta_question` / `cta_start` / `cta_end` / `shorts[i].cta_question` / `cta:false`（無ければタイトル等から既定）
- **夕方ジョブ（18:35）に追加**: `python scripts/post_question.py recipes/<id>.json --apply`（長尺＋ショートに問いを投稿）→ Studio で手でピン留め（API に無い）、長尺の終了画面（登録＋関連動画）、直近7日の新着コメントに短く返信（1日20件程度まで、スパム・中傷・出演者攻撃・個人情報・宣伝は返信しない、炎上しそうなものは大島さんへ）
- 禁止: 自作自演の高評価・登録・コメント、見返り付きの依頼、「公式」「公認」
- 2026-10-15 実施: token.json の scopes に youtube.force-ssl あり（ファイル記載で確認）。試験ビルド `work/_boxtest-cta-20261015`（長尺80秒）/ `-short`（55.4秒）でフレーム確認済み（未アップロード）。本番日次（与儀）でも冒頭・終盤・ショート締めの CTA 帯をフレーム確認済み。pytest 289 passed
- 未検証: 実際のコメント投稿（--apply）・返信の運用、Studio ピン留め手作業

## レシピ方針（日次）

未使用レシピ在庫が無い、または note 不足で使えないときは**人手待ちにしない**。日次フロー内で find_moments / find_short 等からレシピを新規作成してから短長を進める。使える在庫レシピがあればそれを優先。禁止素材（R05BBh55p_U、xfr6w7g_Xucの34分以降、HowwrqNF9gw など）は維持。

## いま何をしているのか

**日次運用を2本に分割済み。** (1) 朝の日次制作 毎日14:07・関連動画なし・短長同一18:30同時予約 (2) 夕方の関連動画紐づけ 毎日18:35・当日同士のみ Studio 関連動画。前日付け替えはしない。概要欄フル導線は朝側の補助。

2026-10-16 分を box で新規予約済み。10/4・10/5・10/9・10/10 は ASUS_i9 オフラインのため欠番のまま（後追いで埋めていない）。

## 今回やったこと（2026-10-16、box で実施）

| やったこと | 結果 |
|---|---|
| YouTube 実状態を確認（audit_account.py、box の token.json） | 当日 10/16 の 18:30 枠は無し。最新は 10/15 短長（jLqqtV38Y7c / RS_GitxDLWs）で公開済み |
| 未使用レシピ在庫 | 無し → 新規本編 `gnRv7TEMx38`（青山・二軍版26人目）を取得してレシピ作成 |
| 新規本編 | `gnRv7TEMx38`（青山玲也／二軍版26人目）。ARグラス技術継承。「流行んなかったから儲からないのでは？」の詰め〜完全ALL |
| レシピ作成 | recipes/2026-10-16-aoyama-hayaranai.json（cta_question: 出資する？しない？） |
| 長尺ビルド・予約 | QGbte-b_DPg / 20:00（1200s、API PT20M1S） / 18:30 JST |
| ショートビルド・予約 | clWXpKjr-Hs / 56.0秒（API PT57S） / 同一 18:30 JST。概要に ▼この回をフルで見る → QGbte-b_DPg |
| Studio 関連動画 | 朝ジョブでは触らない（夕方 18:35 ジョブ担当） |

| 公開 | 種別 | 動画ID | 尺 | 素材 |
|---|---|---|---|---|
| 10/16 18:30 | 長尺 | QGbte-b_DPg | 20:00 | gnRv7TEMx38 2048.0-3248.0 |
| 10/16 18:30 | ショート | clWXpKjr-Hs | 56.0s | gnRv7TEMx38 3191.5-3247.5（長尺区間内） |

長尺の区間: 虎「ARグラスは枯れた技術。意外と流行らない」→「流行んなかったから儲かんなかっただけ説はないか」→一瞬すごいが使わない／かける・ケーブルが面倒→ワイヤレスは今は無理→リターンは2年後に倍→ラストステートメント→ファイナル（馬場30万・梅田50万・ぷろたん20万）→完全オール。視聴者向け宣伝（先着半額）は含むが短く通過。エロ系冗談の短いやり取りは判定直前に含まれるがカード・タイトルでは触れていない。

ショート: 馬場の「30万」直後〜梅田50万（100万検討→違和感で減額）〜ぷろたん20万〜完全オール宣言〜サムネ冗談まで。

## 次にやること

0. **伸び悩み診断（2026-10-16）**: [docs/2026-10-16-growth-diagnosis.md](docs/2026-10-16-growth-diagnosis.md) の §6 打ち手・§7 日次の変更は**提案のみ・未承認**（パイプラインは未変更）

1. **夕方ジョブ（10/16 18:35 JST）** — 当日短長同士（ショート clWXpKjr-Hs → 長尺 QGbte-b_DPg）を Studio 関連動画に紐づけ。`post_question.py --apply` で問いコメント投稿→Studioでピン留め。前日付け替えはしない
2. **10/17 の日次制作（14:07 JST、box）** — 当日枠が無ければ短長を作り 18:30 JST 同時予約
3. 在庫（取得済み）: `gnRv7TEMx38` は今回区間を使用（前半〜中盤の別論点は未使用だが、判定済み本編のため優先度低）。`5s7XkDJBy_M`・`b5IM6DYa-DA` は使用済み。`OpdXqtb73Uc` の最終判定以降（約 2748-末尾）は病気言及あり・慎重に。100–1188.9 と 1960–2740 は使用済み
4. 次の新規本編候補（未取得・未使用）: `KJSteWkUr90` 田村前編・事業再生版、`oJjxzDAKEnw` 藤田・シン美容版、`lJ01U5keezg` 伊谷・関西版、`L1i9-YUwHnM` 西村・シン美容版 など。`yS7uaXYMbUY` なみえ社長・SNS版は夜職求人・名誉面に注意で後回し。box の work/ には OpdXqtb73Uc・b5IM6DYa-DA・5s7XkDJBy_M・gnRv7TEMx38 の source あり
5. 瀬戸前編 `_I2BzfLSZxs`・カルロス前編 `JGJkr2vm2ic`・普久原前半/中盤・たくみなかう前半（10/13）・たくみなかう後半＋判定（10/14）・与儀（10/15）・青山（10/16）は使用済み

## 触ってはいけないところ

- **「公式」「公認」と書かない。** 令和の虎Channel / Youth は切らない（概要末尾の「公式チャンネルではありません」免責は維持）
- **アップロードは --schedule を未アップロードに直接付ける。** 先上げてから入れ直さない（クォータ）
- **1日6本まで。** 回復は JST 16:00 前後（太平洋時間0時）
- **HowwrqNF9gw（VEALL）** はそのまま切ると名誉を害しやすい
- **R05BBh55p_U（岩谷）** は元字幕が語中改行するので使わない
- **xfr6w7g_Xuc（駒澤）の34分以降**（恋愛遍歴）は外す
- **OpdXqtb73Uc の 26:00-28:00 と 31:40-32:40** は志願者の持病（双極性障害）に触れるので切らない。最終判定1枠目コメント（2748付近）にも病気への言及あり
- head は元テロップとも字幕とも別の言葉にする。ビルド後に3秒フレームを見ること
- build_clip の preflight は案件カード事業内容が2行に収まらないと「素材が足りない」で止まる。判定カード detail は3行以内
- 論点カードの1枚目は clip.start から8秒ほど後ろに置く（案件カードと被らないように）
- **thumb.faces の x は「元フレーム内の顔の横位置」。** 吹き出し被り警告は bias を下げて外側へ寄せる
- **タイル画像（ffmpeg fps=1/2 + drawtext pts）のラベル秒は数秒ずれることがある。** thumb.faces.at はラベルを信用せず、build_clip と同じ `ffmpeg -ss <秒> -i source.mp4 -frames:v 1` で単発に抜いて確かめる
- **fixes は部分一致置換。** 「原君→三原君」のような訂正は「三原君」を「三三原君」にするので入れない
- **JGJkr2vm2ic の志願者は白Tシャツの坊主の男性（カルロス）。** 眼鏡にネクタイの男性は進行役。取り違えない
- **SNS版は全員いいね（オール）必須。** 1人でもごめんなさいならナッシング（与儀 10/15 で確認）

## 検証済みの事実（2026-10-16）

- API で QGbte-b_DPg / clWXpKjr-Hs の publishAt=2026-10-16T09:30:00Z・privacy private・channel UCWupHXqf8CTG00c_eoQSw1Q を確認。長尺 API duration PT20M1S。ショート API PT57S（ローカル 56.0s）
- ショート概要に ▼この回をフルで見る → QGbte-b_DPg を API で確認
- 台帳 state/published.json に両方を記録（upload 時）
- ショート 1秒フレーム: head「梅田50万・ぷろたん20万／完全ALL成立」。締め CTA「あなたが虎なら出資する？しない？理由もコメントで」を確認
- 長尺冒頭: CTA「あなたが虎なら出資する？最後に答えを聞きます」。終盤 CTA「あなたならどうする？コメントで／学びになったら高評価・チャンネル登録を」＋「完全ALL」を確認
- 再認証不要（token.json 有効）

## 未検証のもの

- TikTokライブの月収・閲覧数・チャンネル経歴などの数字は ASR 字幕由来（概要欄では「本人の発言（自動字幕）」と明記）※本回は該当薄い
- アップロード直後は processing 中（API duration が P0D のことがある）。公開前に processed / succeeded を再確認すること
- サムネ吹き出し被り警告（肌色判定）は残る場合あり。目視で問題なければ通す（椅子・肌色服の誤検知あり）
