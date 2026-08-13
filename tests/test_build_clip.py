import json
from pathlib import Path

import pytest

from scripts.build_clip import CARD_SEC, overlay_filter, overlay_plan, preflight


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


def _plan(points=None):
    r = recipe()
    r["clip"] = {"start": 100.0, "end": 160.0}
    r["cards"]["points"] = points or []
    return overlay_plan(r, Path("cards"), 60.0)


def test_案件カードは0秒から出る():
    # 以前は静止画を前に連結していて、冒頭4秒が無音の止め絵になっていた。
    # 最初の数秒で維持率が決まるので、音が鳴らない区間を作らない
    png, start, end = _plan()[0]
    assert png.name == "brief.png"
    assert start == 0.0 and end == CARD_SEC


def test_判定カードは末尾に収まる():
    png, start, end = _plan()[-1]
    assert png.name == "verdict.png"
    assert end == 60.0 and start == 60.0 - CARD_SEC


def test_論点カードは本編の時間軸に直される():
    plan = _plan([{"at": 130.0, "text": "x"}])
    # clip.start=100 なので、130秒の指摘は本編の30秒地点
    assert plan[1][1] == 30.0


def test_重ねる順に入力番号が振られる():
    f = overlay_filter(_plan([{"at": 130.0, "text": "x"}]))
    # 入力0が映像、1以降がカード。最後の出力は [v3]（案件・論点・判定の3枚）
    assert f.startswith("[0:v]scale=1920:1080")
    assert "[v0][1:v]overlay" in f
    assert f.endswith("[v3]")
