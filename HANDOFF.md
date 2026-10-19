# 引き継ぎ

最終更新: 2026-10-19（JST 14時台・日次制作完了）

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

2026-10-19 分を box で新規予約済み。10/4・10/5・10/9・10/10 は ASUS_i9 オフラインのため欠番のまま（後追いで埋めていない）。

## 今回やったこと（2026-10-19、box で実施）

| やったこと | 結果 |
|---|---|
| YouTube 実状態を確認（audit_account.py、box の token.json） | 当日 10/19 の 18:30 枠は無し。最新は 10/18 短長（K0P-6nCmQME / XeH_aayxxes）で公開済み |
| 新着チェック（Data API で Second の直近回の公開日・再生数） | `du2oQuFbPlw`（馬場龍太・クラファン版5人目・10/17公開・約7.8万／2日）を採用。他: lJ01U5keezg 11.4万、MPhBGdIVQpc 10.3万、s8lyBpmNgHg 7.9万、l0ZqTEuI6lg 6.5万 |
| 新規本編 | `du2oQuFbPlw`（馬場龍太／ClearEngine合同会社／水分補給ドリンク「ClearEngine」、クラファンPR協力） |
| レシピ作成 | recipes/2026-10-19-baba-clearengine-koutai.json（cta_question: 1杯450円のこのドリンクにPR協力する？しない？／ショートだけ cta_question「あなたが主宰なら、この選手交代を認める？認めない？」） |
| 長尺ビルド・予約 | Y9cIbD_RxqY / 19:14（1153.6s） / 18:30 JST |
| ショートビルド・予約 | 6y8VEp0LPPU / 50.4秒 / 同一 18:30 JST。概要に ▼この回をフルで見る → Y9cIbD_RxqY |
| Studio 関連動画 | 朝ジョブでは触らない（夕方 18:35 ジョブ担当） |

| 公開 | 種別 | 動画ID | 尺 | 素材 |
|---|---|---|---|---|
| 10/19 18:30 | 長尺 | Y9cIbD_RxqY | 19:14 | du2oQuFbPlw 1375.4-2529.0 |
| 10/19 18:30 | ショート | 6y8VEp0LPPU | 50.4s | du2oQuFbPlw 1666.679-1717.08（長尺区間内） |

長尺の区間: 質疑中盤「ずっとQAずれてる」→市場を広く取ればスポドリも競合・アガベならダイエット向けでは・誰に届ける設計か・パッケージがマウスウォッシュ風→「設計が素人」→三浦「450円で買わせたいのか」志願者「買わせたい」→「水でいいよね」→茂木の提案で令虎初の選手交代（開発者の奥様）→ペルソナ・売れた場所と価格帯・プロダクトアウト→奥様のラストステートメント→リターン3種→ファイナルジャッジメント（車谷・渡辺・宮本ごめんなさい、オカラッキーは③法人・部活向け200包購入を表明、主宰三浦が否決→ナッシング）→馬場さんの感想まで。

ショート: 「ちょっと提案があります」→「彼は元々野球選手」「選手交代していい？」→奥様だったら魅力を伝えられるのでは→旦那さん退場→「奥様の方が商品には詳しいよね」まで（直後の車谷の「ヘラヘラしないで」は入れていない）。

## 次にやること

0. **伸び悩み診断（2026-10-16）**: [docs/2026-10-16-growth-diagnosis.md](docs/2026-10-16-growth-diagnosis.md) の §6 打ち手・§7 日次の変更は**提案のみ・未承認**（パイプラインは未変更）

1. **夕方ジョブ（10/19 18:35 JST）** — 当日短長同士（ショート 6y8VEp0LPPU → 長尺 Y9cIbD_RxqY）を Studio 関連動画に紐づけ。`python scripts/post_question.py recipes/2026-10-19-baba-clearengine-koutai.json --apply` で問いコメント投稿→Studioでピン留め。長尺に終了画面。前日付け替えはしない。**10/18 夕方時点で box ブラウザの Google セッションが切れていた（ユーザーに再ログイン依頼済み）ので、Studio 作業の前にログイン状態を確認すること**
2. **10/20 の日次制作（14:07 JST、box）** — 当日枠が無ければ短長を作り 18:30 JST 同時予約。最初に Second の直近4日の新着を再生数つきで確認（診断 §7）
3. 在庫（取得済み）: `du2oQuFbPlw` は 1375.4–2529.0 使用。前半（0:00〜22:55：開発経緯・価格450円の詰め・試飲・大手がやらない理由）は未使用だが、4:00〜4:40 に双子の出生時の体の弱さへの言及があるので切るならそこは外す。`L1i9-YUwHnM` は 2170.96–2957.36 使用、前半〜中盤は優先度低。`gnRv7TEMx38` 優先度低。`lJ01U5keezg` 残り 29:00〜46:40 は喉の手術・カット依頼に注意。`OpdXqtb73Uc` の最終判定以降は病気言及あり・慎重に
4. 次の新規本編候補（未取得・未使用）: `MPhBGdIVQpc` 神尾前編（10.3万）、`l0ZqTEuI6lg` ゆうしん前編、`KJSteWkUr90` 田村前編、`oJjxzDAKEnw` 藤田・シン美容版。`s8lyBpmNgHg` MURACO（コンカフェ）・`yS7uaXYMbUY` なみえ社長は夜職・名誉面に注意で後回し
5. 伊谷・青山・与儀・たくみなかう・普久原・西村判定区間・馬場（10/19）は使用済み

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

## 検証済みの事実（2026-10-19）

- API で Y9cIbD_RxqY / 6y8VEp0LPPU の publishAt=2026-10-19T09:30:00Z・privacy private・channel UCWupHXqf8CTG00c_eoQSw1Q を確認（両方アップロード直後は duration P0D＝processing）
- ショート概要に ▼この回をフルで見る → Y9cIbD_RxqY を API で確認。両方とも概要1行目が問い
- 台帳 state/published.json に両方を記録（upload 時）。長尺サムネ thumbnail_set=true
- 長尺冒頭 CTA（12.5秒〜）・終盤 CTA（1143秒〜）・案件カード／判定カードをフレーム確認
- ショート 3秒フレーム: head「「水でいい」で詰んだ／令虎初の交代劇」・元テロップ「彼は元々野球選手」・字幕「彼は元々野球選手だったんです。」で head は別。締め CTA を 48秒台で確認
- サムネは元動画上部のテロップ（志願者募集中／ClearEngineを届けたい）が割れて映り込んだので crop_top 0.15・crop_bottom 0.3 に上げて消した。志願者は目を閉じていた 1636 を 1631.5 に差し替え
- 人物（画面の名前テロップで確認）: 志願者 馬場龍太（33・黒T）、奥様（キャップ・眼鏡・デニム、名前テロップなし）、三浦哲郎（51・トリアイナグループ会長・主宰）、茂木哲也（ピナイ・インターナショナル代表・進行台に立つ眼鏡の男性）、車谷セナ（TELESA代表）、渡辺いずみ（43・Twenty Company代表）、オカラッキー（41・ミライユ代表・ピンクのジャケット）、宮本せな（36・ecxia代表）
- 価格・リターンは元テロップで確認: 「10包入りで4,500円」「170〜180ml」「① 超早割 ギフト箱10包 3,980円」「② シェアセット40包 13,800円」「③ 法人・部活向け200包 60,000円（送料込）」。オカラッキーのボードは「③ □個購入 PR協力決定」。元動画に「※収録時と実際のリターンが異なります」の注記
- 再認証不要（token.json 有効）

## 未検証のもの

- 商品の効果・原材料の話は ASR／本人発言由来（概要欄では「本人の発言（自動字幕）」「効果を保証するものではない」と明記）
- 「選手交代していい？」の発言者（テロップは三浦の顔に重なるが、元タイトルは「茂木の一声」。レシピでは「主宰への提案」とだけ書き、発言者を断定していない）
- アップロード直後の短長は processing 中（API duration が P0D）。公開前に processed を再確認すること
