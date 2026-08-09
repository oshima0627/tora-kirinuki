import json

import pytest

from scripts.build_clip import preflight


def recipe() -> dict:
    return {
        "id": "t",
        "source_video_id": "vid",
        "source_url": "https://youtu.be/vid",
        "source_title": "元動画",
        "clip": {"start": 0.0, "end": 10.0},
        "cards": {"brief": {"amount": "200万円"}, "points": [], "verdict": {}},
        "title": "t",
        "expected_channel_id": "UCVrCOqLMVJhdciCFUSg0TOw",
    }


def _materials(d):
    (d / "source.mp4").write_bytes(b"x")
    (d / "subs.json").write_text("[]", encoding="utf-8")


def test_素材が揃っていれば空リスト(tmp_path):
    _materials(tmp_path)
    assert preflight(recipe(), tmp_path) == []


def test_足りない素材を全部列挙する(tmp_path):
    missing = preflight(recipe(), tmp_path)
    # 途中で ffmpeg が落ちるより、何が無いかを先に全部出す
    assert any("source.mp4" in m for m in missing)
    assert any("subs.json" in m for m in missing)


def test_clipが元動画より長ければ指摘する(tmp_path):
    _materials(tmp_path)
    (tmp_path / "meta.json").write_text(
        json.dumps({"duration_sec": 5}), encoding="utf-8")
    assert any("尺" in m for m in preflight(recipe(), tmp_path))


def test_clipが尺に収まっていれば通る(tmp_path):
    _materials(tmp_path)
    (tmp_path / "meta.json").write_text(
        json.dumps({"duration_sec": 100}), encoding="utf-8")
    assert preflight(recipe(), tmp_path) == []


def test_論点カードがclipの外なら指摘する(tmp_path):
    _materials(tmp_path)
    r = recipe()
    r["cards"]["points"] = [{"at": 999.0, "text": "外れている"}]
    assert any("論点カード" in m for m in preflight(r, tmp_path))


def test_レシピ不備はValueErrorになる(tmp_path):
    _materials(tmp_path)
    r = recipe()
    r["cards"]["brief"]["amount"] = ""
    with pytest.raises(ValueError):
        preflight(r, tmp_path)
