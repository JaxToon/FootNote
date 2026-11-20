from __future__ import annotations

from pathlib import Path

from fnvideo.audio.timing import (
    build_estimated_timing,
    caption_timings,
    map_mouth_shapes,
    scene_frame_range,
    write_srt,
)
from fnvideo.models.episode import CaptionChunk, SceneSpec
from fnvideo.services.spec_loader import load_episode_spec

ROOT = Path(__file__).resolve().parents[1]


def _scene(narration: str, captions: list[str]) -> SceneSpec:
    return SceneSpec(
        id="s",
        title="S",
        purpose="p",
        narration=narration,
        captions=[CaptionChunk(text=c) for c in captions],
        template="title_question",
    )


def _alignment(text: str, step: float = 0.05) -> dict:
    return {
        "characters": list(text),
        "character_start_times_seconds": [i * step for i in range(len(text))],
        "character_end_times_seconds": [(i + 1) * step for i in range(len(text))],
    }


def test_exact_alignment_labels_every_caption_and_is_contiguous() -> None:
    text = "Dua hal terjadi bersamaan. Tapi belum tentu menyebabkan."
    scene = _scene(text, ["Dua hal terjadi bersamaan", "belum tentu menyebabkan"])
    caps = caption_timings(scene, 3.0, _alignment(text))
    assert [c["timing_quality"] for c in caps] == ["provider_alignment"] * 2
    second_start = text.index("belum") * 0.05 - 0.08
    assert abs(caps[1]["start"] - second_start) < 1e-3
    assert caps[0]["end"] == caps[1]["start"]  # handover, no blank gap
    assert caps[-1]["end"] == 3.0


def test_repeated_phrase_matches_in_order() -> None:
    text = "naik lalu naik lagi"
    scene = _scene(text, ["naik", "naik"])
    caps = caption_timings(scene, 1.0, _alignment(text))
    assert caps[1]["start"] > caps[0]["start"]


def test_one_unmatched_phrase_marks_whole_scene_estimated() -> None:
    text = "Korelasi bukan bukti kausalitas."
    scene = _scene(text, ["Korelasi bukan", "teks yang tidak diucapkan"])
    caps = caption_timings(scene, 2.0, _alignment(text))
    assert {c["timing_quality"] for c in caps} == {"estimated"}


def test_paraphrase_fallback_tiles_whole_speech_without_gaps() -> None:
    scene = _scene(
        "Kalimat narasi yang panjang sekali.", ["Ringkas A", "Ringkasan B lebih panjang"]
    )
    caps = caption_timings(scene, 4.0, None)
    assert caps[0]["start"] == 0.0
    assert caps[0]["end"] == caps[1]["start"]
    assert caps[1]["end"] == 4.0
    assert all(c["timing_quality"] == "estimated" for c in caps)


def test_estimated_timing_inter_scene_gaps_and_contiguity() -> None:
    spec = load_episode_spec(ROOT / "specs/fondasi-01-korelasi-bukan-kausalitas/short.yaml")
    timing = build_estimated_timing(spec, gap_seconds=0.35)
    scenes = timing["scenes"]
    assert [s["id"] for s in scenes] == [s.id for s in spec.scenes]
    assert scenes[0]["start_seconds"] == 0.0
    for prev, nxt in zip(scenes, scenes[1:], strict=False):
        assert abs(prev["end_seconds"] - nxt["start_seconds"]) < 1e-9
        assert abs(prev["duration_seconds"] - prev["speech_duration_seconds"] - 0.35) < 1e-9
    assert abs(scenes[-1]["duration_seconds"] - scenes[-1]["speech_duration_seconds"] - 0.25) < 1e-9
    assert timing["preview_timing_only"] is True


def test_srt_uses_absolute_scene_offsets(tmp_path: Path) -> None:
    timing = {
        "scenes": [
            {"start_seconds": 0.0, "captions": [{"text": "A", "start": 0.0, "end": 1.5}]},
            {"start_seconds": 61.25, "captions": [{"text": "B", "start": 0.5, "end": 2.0}]},
        ]
    }
    out = tmp_path / "c.srt"
    write_srt(timing, out)
    text = out.read_text(encoding="utf-8")
    assert "1\n00:00:00,000 --> 00:00:01,500\nA" in text
    assert "2\n00:01:01,750 --> 00:01:03,250\nB" in text


def test_scene_frame_ranges_never_drift() -> None:
    fps = 30
    bounds = [0.0, 5.35, 12.701, 22.05, 32.3333]
    frames = [scene_frame_range(a, b, fps) for a, b in zip(bounds, bounds[1:], strict=False)]
    for (_, end), (start, _) in zip(frames, frames[1:], strict=False):
        assert end == start
    assert sum(b - a for a, b in frames) == round(bounds[-1] * fps)


def _runs(shapes: list[str]) -> list[int]:
    runs: list[int] = []
    for i, s in enumerate(shapes):
        if i and shapes[i - 1] == s:
            runs[-1] += 1
        else:
            runs.append(1)
    return runs


def test_mouth_minimum_hold_applies_everywhere_including_start() -> None:
    env = [0.3, 0.0, 0.0, 0.2, 0.0, 0.3, 0.3, 0.1, 0.0, 0.0, 0.2]
    shapes = map_mouth_shapes(env, minimum_hold_frames=2)
    assert len(shapes) == len(env)
    assert min(_runs(shapes)) >= 2
    assert shapes == map_mouth_shapes(env, minimum_hold_frames=2)  # deterministic


def test_mouth_thresholds() -> None:
    env = [0.0] * 3 + [0.1] * 3 + [0.2] * 3 + [0.5] * 3
    assert map_mouth_shapes(env) == ["smile"] * 3 + ["small"] * 3 + ["mid"] * 3 + ["wide"] * 3
