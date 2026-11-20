from __future__ import annotations

import numpy as np
import pytest

from fnvideo.qa.motion import allowed_hold_seconds, motion_per_second, motion_report


def test_static_video_has_zero_motion_and_fails() -> None:
    frames = np.zeros((90, 192, 108), dtype=np.uint8)
    per_second = motion_per_second(frames, 30)
    assert per_second == [0.0, 0.0, 0.0]
    assert motion_report(per_second)["low_seconds"] == [0, 1, 2]


def test_changing_video_is_measured_per_second() -> None:
    frames = np.zeros((60, 4, 4), dtype=np.uint8)
    frames[30:] = np.arange(1, 31, dtype=np.uint8)[:, None, None]  # +1 gray level per frame
    per_second = motion_per_second(frames, 30)
    assert per_second[0] == 0.0
    assert abs(per_second[1] - 1.0) < 1e-6
    report = motion_report(per_second, threshold=0.3)
    assert report["low_seconds"] == [0] and not report["passed"]


def test_intentional_holds_are_excused() -> None:
    assert allowed_hold_seconds([(1.0, 3.0)]) == {1, 2}
    assert allowed_hold_seconds([(0.5, 1.9)]) == set()  # no whole second covered
    report = motion_report([0.0, 0.0, 1.0], allowed={0, 1})
    assert report["passed"]


def test_grain_tiles_are_deterministic_and_distinct() -> None:
    from fnvideo.render.svg_scene import GRAIN_TILES, grain_tiles

    tiles = grain_tiles()
    assert len(tiles) == GRAIN_TILES == len(set(tiles))
    grain_tiles.cache_clear()
    assert grain_tiles() == tiles


def test_scene_has_secondary_motion_hooks() -> None:
    from pathlib import Path

    from fnvideo.audio.timing import build_estimated_timing
    from fnvideo.render.svg_scene import build_scene_html
    from fnvideo.services.spec_loader import load_episode_spec

    root = Path(__file__).resolve().parents[1]
    spec = load_episode_spec(root / "specs/fondasi-01-korelasi-bukan-kausalitas/short.yaml")
    timing = build_estimated_timing(spec, 0.35)
    i = next(k for k, sc in enumerate(spec.scenes) if sc.template == "causal_diagram")
    html = build_scene_html(spec, spec.scenes[i], timing["scenes"][i], timing)
    assert html.count("data-drift=") >= 18
    assert html.count("data-grain=") == 3 and "mix-blend-mode:overlay" in html
    assert 'data-idle="spin"' in html  # the sun icon keeps turning


def test_spec_holds_become_absolute_windows(tmp_path) -> None:
    import json
    from pathlib import Path

    from fnvideo.audio.timing import build_estimated_timing
    from fnvideo.cli import _motion_holds
    from fnvideo.models.episode import Hold
    from fnvideo.services.spec_loader import load_episode_spec

    root = Path(__file__).resolve().parents[1]
    spec = load_episode_spec(root / "specs/fondasi-01-korelasi-bukan-kausalitas/short.yaml")
    scenes = list(spec.scenes)
    scenes[1] = scenes[1].model_copy(update={"holds": [Hold(start=0.5, end=1.0, reason="beat")]})
    spec = spec.model_copy(update={"scenes": scenes})
    timing = build_estimated_timing(spec, 0.35)
    (tmp_path / "timing.json").write_text(json.dumps(timing), encoding="utf-8")
    st = timing["scenes"][1]
    ((a, b),) = _motion_holds(spec, tmp_path)
    assert a == st["start_seconds"] + 0.5 * st["duration_seconds"]
    assert b == pytest.approx(st["end_seconds"])
