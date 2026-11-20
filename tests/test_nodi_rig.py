from __future__ import annotations

from pathlib import Path

from fnvideo.render.svg_scene import (
    NODI_EXPRESSION_MAP,
    NODI_POSE_MAP,
    NODI_RIG_JS,
    build_scene_html,
)
from fnvideo.services.spec_loader import load_episode_spec

SPEC = Path("specs/fondasi-01-korelasi-bukan-kausalitas/short.yaml")


def _timing(scene_id: str) -> dict:
    return {
        "id": scene_id,
        "start_seconds": 0,
        "end_seconds": 4,
        "duration_seconds": 4,
        "captions": [],
    }


def test_rig_asset_defines_api() -> None:
    assert "global.NODI" in NODI_RIG_JS
    assert "GESTURES" in NODI_RIG_JS and "gestureAt" in NODI_RIG_JS
    for pose in set(NODI_POSE_MAP.values()):
        assert f"{pose}:" in NODI_RIG_JS, pose
    for expr in set(NODI_EXPRESSION_MAP.values()):
        assert f"{expr}:" in NODI_RIG_JS, expr


def test_rig_embedded_only_when_mascot_on() -> None:
    spec = load_episode_spec(SPEC)
    on = next(s for s in spec.scenes if s.character.mascot == "on")
    off = next(s for s in spec.scenes if s.character.mascot == "off")
    on_html = build_scene_html(spec, on, _timing(on.id), {})
    off_html = build_scene_html(spec, off, _timing(off.id), {})
    assert "NODI.mount" in on_html and "global.NODI" in on_html
    assert "activity" in on_html and "gestureSeed" in on_html
    assert "global.NODI" not in off_html


def test_dark_background_gets_rim() -> None:
    spec = load_episode_spec(SPEC)
    scene = next(s for s in spec.scenes if s.character.mascot == "on")
    html = build_scene_html(spec, scene, _timing(scene.id), {})
    if scene.background in {"navy", "navy_dark", "deep_blue"}:
        assert 'filter="url(#nodiRim)"' in html
