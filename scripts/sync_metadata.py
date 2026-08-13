#!/usr/bin/env python3
"""レシピのタイトル・概要欄・タグを、公開済みの動画へ反映する。

  python scripts/sync_metadata.py recipes/<id>.json --dry-run
  python scripts/sync_metadata.py recipes/<id>.json
  python scripts/sync_metadata.py recipes/*.json

**動画IDは変わらない。** 再生数も登録者も維持したままタイトルだけ直せる。
映像そのものを直したい場合はビルドし直して上げ直すしかなく、そちらは
動画IDが変わる（過去に3本消している）。文言の修正はここで済ませること。

`videos.update` の snippet は部分更新ではなく丸ごと置き換えなので、
categoryId と言語設定を必ず一緒に送る。落とすと言語が推測に戻り、
日本語の動画が en と判定される。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.recipe import build_description, validate  # noqa: E402
from scripts.upload_youtube import (PUBLISHED, get_service,  # noqa: E402
                                    with_long_form_link)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def targets(recipe: dict) -> list[tuple[str, str, list[str]]]:
    """(published.json のキー, タイトル, タグ) を長尺・ショートの順に返す。

    ショートを先に返すと、概要欄に差し込む長尺のURLがまだ無い場合に気づけない。
    """
    tags = recipe.get("tags") or []
    out = [(recipe["id"], recipe["title"], tags)]
    short = recipe.get("short")
    if short:
        out.append((f"{recipe['id']}-short",
                    short.get("title") or short["hook"],
                    tags + ["Shorts"]))
    return out


def sync(service, recipe: dict, dry_run: bool = False) -> None:
    validate(recipe)
    data = json.loads(PUBLISHED.read_text(encoding="utf-8-sig"))

    for key, title, tags in targets(recipe):
        entry = data["videos"].get(key)
        if not entry:
            print(f"- {key}: 未アップロードなので飛ばす")
            continue

        description = build_description(recipe)
        description = with_long_form_link({"id": key}, description)
        vid = entry["youtube_video_id"]

        if dry_run:
            print(f"[dry-run] {key} ({vid})")
            print(f"  {entry['title']}")
            print(f"  → {title}")
            continue

        service.videos().update(part="snippet", body={
            "id": vid,
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags,
                "categoryId": recipe.get("category_id", "22"),
                "defaultLanguage": "ja",
                "defaultAudioLanguage": "ja",
            },
        }).execute()

        entry["title"] = title
        print(f"✓ {key}  {title}")

    if not dry_run:
        PUBLISHED.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("recipes", type=Path, nargs="+")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    service = None if a.dry_run else get_service()
    for p in a.recipes:
        sync(service, json.loads(p.read_text(encoding="utf-8")), a.dry_run)


if __name__ == "__main__":
    main()
