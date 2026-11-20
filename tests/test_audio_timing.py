from __future__ import annotations

from fnvideo.audio.timing import caption_timings, map_mouth_shapes
from fnvideo.models.episode import CaptionChunk, SceneSpec


def scene() -> SceneSpec:
    return SceneSpec(
        id="hook",
        title="Hook",
        purpose="Test",
        narration="Korelasi bukan bukti kausalitas.",
        captions=[CaptionChunk(text="Korelasi bukan", highlight=["bukan"])],
        template="title_question",
    )


def test_caption_uses_provider_alignment_when_phrase_matches() -> None:
    transcript = scene().narration
    alignment = {
        "characters": list(transcript),
        "character_start_times_seconds": [i * 0.05 for i in range(len(transcript))],
        "character_end_times_seconds": [(i + 1) * 0.05 for i in range(len(transcript))],
    }
    result = caption_timings(scene(), 2.0, alignment)
    assert result[0]["timing_quality"] == "provider_alignment"
    assert result[0]["start"] >= 0
    assert result[0]["end"] > result[0]["start"]


def test_caption_fallback_is_explicitly_marked() -> None:
    result = caption_timings(scene(), 2.0, None)
    assert result[0]["timing_quality"] == "estimated"


def test_mouth_shape_has_minimum_hold() -> None:
    shapes = map_mouth_shapes([0.0, 0.0, 0.3, 0.0, 0.0], minimum_hold_frames=2)
    assert len(shapes) == 5
    assert shapes[0] == "smile"
    assert shapes[2] == "smile"  # one-frame blip is suppressed
