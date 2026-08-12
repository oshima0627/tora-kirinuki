#!/usr/bin/env python3
"""ビルドした切り抜きを YouTube に上げる。

  python scripts/upload_youtube.py --auth-only          # 初回の認証だけ
  python scripts/upload_youtube.py work/<id>            # private で投稿
  python scripts/upload_youtube.py work/<id> --publish  # 内容確認後に公開へ

bgm-youtube/scripts/upload_youtube.py から移植した。
BGM固有の処理（バナー・ローカライズ・Content ID・投稿スケジュール）は落とし、
チャンネル取り違えのガードとサムネイル403の扱いはそのまま持ってきている。

**公開はガジェット通信の申請が通ってから。** 許諾前の公開は無断転載になる。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
CLIENT_SECRET = ROOT / "client_secret.json"
TOKEN = ROOT / "token.json"
PUBLISHED = ROOT / "state" / "published.json"

# 必要なスコープは4つの要件から決まる。
#
#   videos.insert    → youtube.upload
#   channels.list    → youtube.readonly
#                      ブランドアカウントを持つと同意画面はアカウントを選ぶだけで、
#                      API は既定チャンネルに上げる。実際に一度、意図しない
#                      チャンネルに入った。事前確認の手段が無いとこの事故は静かに続く。
#   videos.update    → youtube.force-ssl（公開設定の変更に必要。狭いスコープが無い）
#   reports.query    → yt-analytics.readonly（インプレッション数・トラフィックソースの確認用）
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def die(msg: str) -> None:
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(1)


def get_service():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        die("依存が足りません。"
            "`pip install google-api-python-client google-auth-oauthlib`")

    creds = None
    if TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        if not CLIENT_SECRET.exists():
            die(f"{CLIENT_SECRET.name} がありません。\n"
                "  Google Cloud で YouTube Data API v3 を有効化し、\n"
                "  OAuth クライアント（デスクトップアプリ）を作成して配置してください。")
        # 初回のみブラウザが開く。以降は token.json の refresh_token で無人化される
        creds = InstalledAppFlow.from_client_secrets_file(
            str(CLIENT_SECRET), SCOPES).run_local_server(port=0)
        TOKEN.write_text(creds.to_json(), encoding="utf-8")
        print(f"✓ 認証情報を保存しました: {TOKEN.name}（コミットしないこと）")

    return build("youtube", "v3", credentials=creds)


def current_channel(service) -> dict | None:
    """いま認証しているトークンがどのチャンネルに紐づくかを返す。"""
    from googleapiclient.errors import HttpError
    try:
        items = service.channels().list(
            part="snippet", mine=True).execute().get("items", [])
    except HttpError as e:
        print(f"! チャンネルを確認できませんでした: {e}")
        return None
    return {"id": items[0]["id"], "title": items[0]["snippet"]["title"]} if items else None


def assert_expected_channel(service, meta: dict) -> dict | None:
    """meta の expected_channel_id と一致しない限りアップロードしない。

    間違ったチャンネルに上げると消して上げ直すことになる。上げる前に止めるほうが安い。
    """
    ch = current_channel(service)
    expected = meta.get("expected_channel_id")
    if not expected:
        die("meta.json に expected_channel_id がありません。"
            "取り違えを防げないのでアップロードしません")
    if ch is None or ch["id"] != expected:
        got = f"{ch['title']}（{ch['id']}）" if ch else "取得できず"
        die("アップロード先のチャンネルが指定と一致しません。\n"
            f"  期待: {expected}\n"
            f"  実際: {got}\n"
            f"  {TOKEN.name} を削除し、同意画面で正しいチャンネルを選び直してください。")
    return ch


FUNNEL_HEAD = "▼この回をフルで見る"


def with_long_form_link(meta: dict, description: str) -> str:
    """ショートの概要欄に、同じ回の長尺へのリンクを差し込む。

    **ショートは長尺への導線として出している。** それなのに概要欄のリンクが
    元動画（公式チャンネル）だけだと、ショートを見た人の行き先が公式にしか
    無い。実際に7本ともその状態で公開されていた。

    長尺のURLはアップロードするまで決まらないので、ビルド時ではなくここで
    差し込む。運用手順どおり長尺 → ショートの順に上げれば必ず解決する。
    """
    vid_id = meta["id"]
    if not vid_id.endswith("-short"):
        return description
    if FUNNEL_HEAD in description:
        return description

    base = vid_id[: -len("-short")]
    data = json.loads(PUBLISHED.read_text(encoding="utf-8-sig"))
    entry = data["videos"].get(base)
    if not entry:
        die(f"長尺 {base} が未アップロードです。"
            f"ショートは長尺へのリンクを持つので、先に長尺を上げてください")

    # 元動画URL（MCNの条件で冒頭に置く）の直後。本文より前に出す
    lines = description.split("\n")
    at = 2 if len(lines) >= 2 else len(lines)
    lines[at:at] = ["", FUNNEL_HEAD, entry["url"]]
    return "\n".join(lines)


def upload(service, workdir: Path, meta: dict, description: str, privacy: str) -> str:
    from googleapiclient.http import MediaFileUpload

    video = workdir / "video.mp4"
    if not video.exists():
        die(f"{video} がありません。先に build_clip.py を実行してください")

    # 言語は必ず明示する。省略すると YouTube が推測し、BGMチャンネルでは
    # 日本語の動画9本中8本が en と判定された
    body = {
        "snippet": {
            "title": meta["title"][:100],
            "description": description[:5000],
            "tags": meta.get("tags", []),
            "categoryId": meta.get("category_id", "22"),
            "defaultLanguage": "ja",
            "defaultAudioLanguage": "ja",
        },
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }

    media = MediaFileUpload(str(video), chunksize=8 * 1024 * 1024,
                            resumable=True, mimetype="video/mp4")
    request = service.videos().insert(part="snippet,status", body=body,
                                      media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  アップロード {int(status.progress() * 100)}%")
    return response["id"]


def set_thumbnail(service, video_id: str, workdir: Path) -> bool:
    """サムネイルを設定する。電話番号確認が未了だと403になるが、動画自体は
    既に上がっているのでここで止めない。"""
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    thumb = workdir / "thumb.png"
    if not thumb.exists():
        print("! thumb.png が無いのでサムネイル設定をスキップします")
        return False
    try:
        service.thumbnails().set(
            videoId=video_id, media_body=MediaFileUpload(str(thumb))).execute()
        return True
    except HttpError as e:
        print(f"! サムネイル設定に失敗しました: {e}")
        if getattr(e, "status_code", None) == 429 or "429" in str(e):
            # 短時間に何度も差し替えると弾かれる。クォータ超過ではないので待てば通る
            print("  差し替えの回数制限です。時間を置いて --thumbnail-only を再実行してください")
        else:
            print("  チャンネルの電話番号確認が済んでいるか確認してください")
        return False


def set_privacy(service, video_id: str, privacy: str, publish_at: str | None = None) -> None:
    """公開設定を変更する。

    videos.update は部分更新ではなく part を丸ごと置き換える。status だけを渡すと
    selfDeclaredMadeForKids などが既定値に戻る恐れがあるため、現在の status を
    読んでから必要な項目だけ差し替えて送る。

    publish_at を渡すと即座には公開せず、YouTube 側の予約公開に乗せる。
    このとき privacyStatus は "private" のまま送る（"public" と同時に送ると
    無視されて即時公開になる）。指定時刻になると YouTube が自動で public に切り替える。
    """
    items = service.videos().list(part="status", id=video_id).execute().get("items", [])
    if not items:
        die(f"動画が見つかりません: {video_id}")
    cur = items[0]["status"]
    # update で送れるのはこの範囲だけ。uploadStatus / madeForKids などは
    # 読み取り専用で、そのまま送り返すとエラーになる
    writable = ("license", "embeddable", "publicStatsViewable",
                "selfDeclaredMadeForKids")
    status = {k: cur[k] for k in writable if k in cur}
    if publish_at:
        status["privacyStatus"] = "private"
        status["publishAt"] = publish_at
    else:
        status["privacyStatus"] = privacy
    service.videos().update(part="status",
                            body={"id": video_id, "status": status}).execute()


def record(meta: dict, video_id: str, privacy: str, thumb_ok: bool,
           ch: dict | None) -> None:
    PUBLISHED.parent.mkdir(parents=True, exist_ok=True)
    data = (json.loads(PUBLISHED.read_text(encoding="utf-8-sig"))
            if PUBLISHED.exists() else {"videos": {}})
    data["videos"][meta["id"]] = {
        "youtube_video_id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "title": meta["title"],
        "privacy_status": privacy,
        # どのチャンネルに上がったかを必ず残す。追跡できないと取り違えに気づけない
        "channel_id": (ch or {}).get("id"),
        "channel_title": (ch or {}).get("title"),
        "thumbnail_set": thumb_ok,
        "source_url": meta.get("source_url"),
    }
    PUBLISHED.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("workdir", type=Path, nargs="?",
                    help="--auth-only のときは省略できる")
    ap.add_argument("--auth-only", action="store_true",
                    help="認証だけ通して token.json を作る")
    ap.add_argument("--publish", action="store_true",
                    help="アップロード済みの動画を公開に切り替える")
    ap.add_argument("--schedule", metavar="ISO8601",
                    help="即時公開せず、指定時刻に自動公開する予約を入れる"
                         "（例: 2026-08-11T03:00:00Z。JSTなら+09:00を付ける）")
    ap.add_argument("--thumbnail-only", action="store_true",
                    help="アップロード済みの動画のサムネイルだけ差し替える")
    a = ap.parse_args()

    service = get_service()
    if a.auth_only:
        ch = current_channel(service)
        print(f"✓ 認証しました: {ch['title']}（{ch['id']}）" if ch else "✓ 認証しました")
        return
    if not a.workdir:
        die("workdir を指定してください")

    meta = json.loads((a.workdir / "meta.json").read_text(encoding="utf-8"))
    ch = assert_expected_channel(service, meta)
    print(f"- チャンネル: {ch['title']}（{ch['id']}）")

    if a.thumbnail_only:
        data = json.loads(PUBLISHED.read_text(encoding="utf-8-sig"))
        entry = data["videos"].get(meta["id"]) or die(
            f"{meta['id']} はまだアップロードされていません")
        ok = set_thumbnail(service, entry["youtube_video_id"], a.workdir)
        entry["thumbnail_set"] = ok
        PUBLISHED.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{'✓ 差し替えました' if ok else '! 差し替えできませんでした'}: {entry['url']}")
        return

    if a.publish or a.schedule:
        data = json.loads(PUBLISHED.read_text(encoding="utf-8-sig"))
        entry = data["videos"].get(meta["id"]) or die(
            f"{meta['id']} はまだアップロードされていません")
        if a.schedule:
            set_privacy(service, entry["youtube_video_id"], "private", publish_at=a.schedule)
            entry["privacy_status"] = "private"
            entry["publish_at"] = a.schedule
            PUBLISHED.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"✓ 予約しました: {entry['url']}  → {a.schedule} に自動公開")
        else:
            set_privacy(service, entry["youtube_video_id"], "public")
            entry["privacy_status"] = "public"
            PUBLISHED.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"✓ 公開しました: {entry['url']}")
        return

    description = (a.workdir / "description.txt").read_text(encoding="utf-8")
    description = with_long_form_link(meta, description)
    privacy = meta.get("privacy_status", "private")
    vid = upload(service, a.workdir, meta, description, privacy)
    thumb_ok = set_thumbnail(service, vid, a.workdir)
    record(meta, vid, privacy, thumb_ok, ch)
    print(f"✓ https://www.youtube.com/watch?v={vid}  ({privacy})")
    print("  内容を確認してから --publish で公開してください")


if __name__ == "__main__":
    main()
