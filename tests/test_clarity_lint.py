from __future__ import annotations

from pathlib import Path

import pytest

from fnvideo.models.episode import Beat, CaptionChunk
from fnvideo.services.clarity import (
    ClarityGateError,
    check_clarity,
    editorial_gate,
    normalize,
)
from fnvideo.services.spec_loader import load_episode_spec

ROOT = Path(__file__).resolve().parents[1]
SHORT = ROOT / "specs/fondasi-01-korelasi-bukan-kausalitas/short.yaml"


def _short():
    return load_episode_spec(SHORT)


def _with_scene(spec, index, **update):
    scenes = list(spec.scenes)
    scenes[index] = scenes[index].model_copy(update=update)
    return spec.model_copy(update={"scenes": scenes})


def _rules(spec) -> set[str]:
    return {i.rule for i in check_clarity(spec)}


def test_pilot_short_is_clarity_clean() -> None:
    assert check_clarity(_short()) == []


def test_normalize_ignores_case_and_punctuation() -> None:
    assert normalize("Jadi... makan ES KRIM, bikin?") == "jadi makan es krim bikin"


def test_a_paraphrased_caption_is_flagged_but_punctuation_is_not() -> None:
    spec = _short()
    ok = _with_scene(spec, 0, captions=[CaptionChunk(text="tahu NGGAK")])
    assert "a" not in _rules(ok)
    bad = _with_scene(spec, 0, captions=[CaptionChunk(text="Es krim bikin tenggelam")])
    assert "a" in _rules(bad)


def test_b_first_scene_needs_concrete_content() -> None:
    spec = _short()
    props = {k: v for k, v in spec.scenes[0].props.items() if k != "side_icons"}
    assert "b" in _rules(_with_scene(spec, 0, props=props))


def test_c_mascot_only_scene_longer_than_two_seconds_except_close() -> None:
    spec = _short()
    q = next(i for i, s in enumerate(spec.scenes) if s.id == "question")
    props = {k: v for k, v in spec.scenes[q].props.items() if k != "side_icons"}
    issues = check_clarity(_with_scene(spec, q, props=props))
    assert any(i.rule == "c" and i.scene == "question" for i in issues)
    # the close (last scene) is NODI-only by design and is exempt
    assert not any(i.rule == "c" and i.scene == "close" for i in check_clarity(spec))
    # a short mascot-only moment is fine
    short_q = _with_scene(spec, q, props=props, duration_hint_seconds=1.8)
    assert not any(i.rule == "c" for i in check_clarity(short_q))


def test_d_explanation_scene_needs_a_word_beat() -> None:
    spec = _short()
    i = next(k for k, s in enumerate(spec.scenes) if s.template == "causal_diagram")
    beats = [
        b for b in spec.scenes[i].beats if not (isinstance(b.at, str) and b.at.startswith("word:"))
    ]
    beats = beats or [Beat(at=0.5, target="label", action="pop")]
    assert "d" in _rules(_with_scene(spec, i, beats=beats))


def test_editorial_gate_blocks_only_approved_specs() -> None:
    spec = _short()
    bad = _with_scene(spec, 0, captions=[CaptionChunk(text="Ringkasan bebas")])
    editorial_gate(bad)  # draft: warnings only
    with pytest.raises(ClarityGateError, match="clarity a"):
        editorial_gate(bad.model_copy(update={"editorial_status": "approved"}))
    editorial_gate(spec.model_copy(update={"editorial_status": "approved"}))  # clean passes


def test_tts_refuses_unclear_approved_spec_before_any_api_call(tmp_path, monkeypatch) -> None:
    from fnvideo.audio import pipeline
    from fnvideo.config import load_settings

    spec = _with_scene(_short(), 0, captions=[CaptionChunk(text="Ringkasan bebas")])
    spec = spec.model_copy(update={"editorial_status": "approved"})

    def no_client(*args, **kwargs):  # pragma: no cover - must never be reached
        raise AssertionError("ElevenLabs client must not be created")

    monkeypatch.setattr(pipeline, "ElevenLabsClient", no_client)
    with pytest.raises(ClarityGateError):
        pipeline.generate_tts(spec, tmp_path, load_settings())
