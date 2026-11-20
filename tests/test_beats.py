from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from fnvideo.audio.timing import build_estimated_timing, caption_timings, resolve_beats
from fnvideo.models.episode import Beat, CaptionChunk, SceneSpec
from fnvideo.render.svg_scene import animation_plan, build_scene_html, compute_layout, template_art
from fnvideo.services.spec_loader import load_episode_spec, migrate_spec

ROOT = Path(__file__).resolve().parents[1]
SHORT = ROOT / "specs/fondasi-01-korelasi-bukan-kausalitas/short.yaml"


def _scene(beats: list[dict], template: str = "causal_diagram") -> SceneSpec:
    return SceneSpec(
        id="s",
        title="S",
        purpose="p",
        narration="Bisa jadi ada faktor ketiga: cuaca panas. Cuaca panas mendorong keduanya.",
        captions=[CaptionChunk(text="Ada faktor ketiga"), CaptionChunk(text="Cuaca panas")],
        template=template,
        beats=[Beat(**b) for b in beats],
    )


def test_v1_spec_migrates_to_v2() -> None:
    assert migrate_spec({"schema_version": 1, "meta": {}})["schema_version"] == 2
    assert migrate_spec({"meta": {}})["schema_version"] == 2
    with pytest.raises(ValueError, match="Unsupported"):
        migrate_spec({"schema_version": 9})
    assert load_episode_spec(SHORT).schema_version == 2


@pytest.mark.parametrize(
    "beat",
    [
        {"at": 1.5, "target": "x", "action": "pop"},
        {"at": "second:2", "target": "x", "action": "pop"},
        {"at": 0.5, "target": "x", "action": "explode"},
        {"at": 0.5, "target": "nodi", "action": "pop"},
    ],
)
def test_invalid_beats_are_rejected(beat: dict) -> None:
    with pytest.raises(ValidationError):
        Beat(**beat)


def test_caption_beat_must_exist() -> None:
    with pytest.raises(ValidationError, match="caption:5"):
        _scene([{"at": "caption:5", "target": "node-0", "action": "pop"}])


def test_beats_resolve_from_caption_word_and_fraction() -> None:
    scene = _scene(
        [
            {"at": 0.5, "target": "label", "action": "pop"},
            {"at": "caption:1", "target": "node-0", "action": "highlight"},
            {"at": "word:panas", "target": "node-0", "action": "pop"},
        ]
    )
    caps = caption_timings(scene, 8.0, None)
    beats = resolve_beats(scene, 8.0, 10.0, caps, None)
    by_key = {(b["target"], b["action"]): b for b in beats}
    assert by_key[("node-0", "pop")]["t"] == pytest.approx(
        8.0 * scene.narration.index("panas") / len(scene.narration), abs=1e-3
    )
    assert by_key[("node-0", "highlight")]["t"] == caps[1]["start"]
    assert [b["t"] for b in beats] == sorted(b["t"] for b in beats)
    assert by_key[("label", "pop")]["t"] == 5.0  # fraction of the scene duration


def test_word_beat_uses_provider_alignment_when_available() -> None:
    scene = _scene([{"at": "word:cuaca", "target": "node-0", "action": "pop"}])
    text = scene.narration
    alignment = {
        "characters": list(text),
        "character_start_times_seconds": [i * 0.1 for i in range(len(text))],
        "character_end_times_seconds": [(i + 1) * 0.1 for i in range(len(text))],
    }
    (beat,) = resolve_beats(scene, 8.0, 8.0, caption_timings(scene, 8.0, alignment), alignment)
    assert beat["t"] == pytest.approx(text.index("cuaca") * 0.1)
    assert beat["timing_quality"] == "provider_alignment"


def test_unknown_word_is_an_authoring_error() -> None:
    scene = _scene([{"at": "word:es-krim", "target": "node-0", "action": "pop"}])
    with pytest.raises(ValueError, match="es-krim"):
        resolve_beats(scene, 8.0, 8.0, caption_timings(scene, 8.0, None), None)


def test_plan_uses_beats_and_staggers_the_rest() -> None:
    scene = _scene([])
    els = template_art(scene, compute_layout(1080, 1920, False))
    beats = [
        {"t": 2.0, "target": "node-1", "action": "slide", "duration": None},
        {"t": 3.0, "target": "node-1", "action": "highlight", "duration": 0.6},
        {"t": 4.0, "target": "label", "action": "exit", "duration": None},
        {"t": 1.0, "target": "nodi", "action": "pose:wave", "duration": None},
        {"t": 1.5, "target": "nodi", "action": "expr:surprised", "duration": None},
    ]
    plan = animation_plan(els, beats, pose="rest", expression="neutral")
    elements = {e["id"]: e for e in plan["elements"]}
    assert elements["node-1"]["enter"] == {"t": 2.0, "action": "slide", "dur": 0.45}
    assert elements["node-1"]["highlights"] == [{"t": 3.0, "dur": 0.6}]
    assert elements["label"]["exit"]["t"] == 4.0
    defaults = [e["enter"]["t"] for e in plan["elements"] if e["id"] != "node-1"]
    assert defaults == pytest.approx([0.15 + 0.15 * k for k in range(len(defaults))])
    # causal default order: source node, then each arrow before its target node
    assert [e["id"] for e in plan["elements"]][:3] == ["node-0", "arrow-1", "node-1"]
    assert elements["arrow-1"]["enter"]["action"] == "draw"
    assert plan["nodi_pose"] == [{"t": 0.0, "value": "rest"}, {"t": 1.0, "value": "wave"}]
    assert plan["nodi_expression"][-1] == {"t": 1.5, "value": "surprised"}


def test_unknown_beat_target_lists_available_elements() -> None:
    els = template_art(_scene([]), compute_layout(1080, 1920, False))
    bad = [{"t": 1.0, "target": "nope", "action": "pop", "duration": None}]
    with pytest.raises(ValueError, match="node-0"):
        animation_plan(els, bad, pose="rest", expression="neutral")


def test_no_global_short_fade_remains() -> None:
    spec = load_episode_spec(SHORT)
    timing = build_estimated_timing(spec, 0.35)
    html = build_scene_html(spec, spec.scenes[0], timing["scenes"][0], timing)
    assert "smooth(t/0.48)" not in html
    assert 'id="scene-art" opacity' not in html
    assert html.count('data-id="') >= 3
