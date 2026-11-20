from __future__ import annotations

from pathlib import Path

from fnvideo.models.episode import EpisodeSpec
from fnvideo.render.svg_scene import build_scene_html
from fnvideo.services.spec_loader import load_episode_spec

ROOT = Path(__file__).resolve().parents[1]


def test_all_core_templates_build_for_portrait_and_landscape() -> None:
    base = load_episode_spec(ROOT / "specs/fondasi-01-korelasi-bukan-kausalitas/short.yaml")
    templates = [
        "title_question",
        "chapter_title",
        "definition_card",
        "paired_trend",
        "line_chart",
        "scatter_regression",
        "question_link",
        "causal_diagram",
        "takeaway",
        "follow_cta",
    ]
    for fmt, width, height in [("short", 1080, 1920), ("long", 1920, 1080)]:
        meta = base.meta.model_copy(update={"format": fmt, "width": width, "height": height})
        spec = EpisodeSpec.model_validate({**base.model_dump(), "meta": meta.model_dump()})
        for name in templates:
            scene = base.scenes[0].model_copy(update={"template": name})
            html = build_scene_html(spec, scene, {"captions": []}, {"mouth_shapes": []})
            assert "window.render" in html
            assert f'width="{width}" height="{height}"' in html
            assert "F/N" in html


def test_nodi_layer_is_optional_per_scene() -> None:
    spec = load_episode_spec(ROOT / "specs/fondasi-01-korelasi-bukan-kausalitas/short.yaml")
    scene = spec.scenes[0]
    on_html = build_scene_html(spec, scene, {"captions": []}, {})
    off_scene = scene.model_copy(
        update={"character": scene.character.model_copy(update={"mascot": "off"})}
    )
    off_html = build_scene_html(spec, off_scene, {"captions": []}, {})
    assert 'id="nodi"' in on_html
    assert 'id="nodi"' not in off_html
