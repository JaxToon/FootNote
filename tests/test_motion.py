from __future__ import annotations

import numpy as np

from fnvideo.qa.motion import allowed_hold_seconds, motion_per_second, motion_report


def test_static_video_has_zero_motion_and_fails() -> None:
    frames = np.zeros((90, 192, 108), dtype=np.uint8)
    per_second = motion_per_second(frames, 30)
    assert per_second == [0.0, 0.0, 0.0]
    assert motion_report(per_second)["low_seconds"] == [0, 1, 2]


def test_changing_video_is_measured_per_second() -> None:
    frames = np.zeros((60, 4, 4), dtype=np.uint8)
    frames[30:] = np.arange(30, dtype=np.uint8)[:, None, None]  # second 1 brightens 1/frame
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
