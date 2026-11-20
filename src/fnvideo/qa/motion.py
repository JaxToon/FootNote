"""Motion QA: how much the picture changes, second by second.

Metric: mean absolute difference between consecutive frames, on a grayscale thumbnail
(108x192 portrait / 192x108 landscape), in 0..255 gray levels, averaged per second.
A second whose value stays near 0 is a visually frozen second.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

DEFAULT_THRESHOLD = 0.3


def thumb_size(width: int, height: int) -> tuple[int, int]:
    return (108, 192) if height > width else (192, 108)


def read_gray_frames(video: Path, width: int, height: int) -> np.ndarray:
    """Decode *video* to an array of shape (frames, h, w) uint8 via FFmpeg."""
    tw, th = thumb_size(width, height)
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"scale={tw}:{th}:flags=area",
         "-pix_fmt", "gray", "-f", "rawvideo", "pipe:1"],
        capture_output=True,
        check=True,
    )  # fmt: skip
    data = np.frombuffer(proc.stdout, dtype=np.uint8)
    return data.reshape(-1, th, tw)


def motion_per_second(frames: np.ndarray, fps: int) -> list[float]:
    """Mean abs inter-frame difference, aggregated per whole second of video."""
    if len(frames) < 2:
        return [0.0]
    diffs = np.abs(np.diff(frames.astype(np.int16), axis=0)).mean(axis=(1, 2))
    # diff i is the change into frame i+1; bucket by the second that frame belongs to
    seconds = (np.arange(1, len(frames)) // fps).astype(int)
    n = int(seconds.max()) + 1
    out = [float(diffs[seconds == s].mean()) if np.any(seconds == s) else 0.0 for s in range(n)]
    return [round(v, 4) for v in out]


def allowed_hold_seconds(holds: list[tuple[float, float]]) -> set[int]:
    """Whole seconds fully covered by intentional holds (absolute [start, end) windows)."""
    allowed: set[int] = set()
    for start, end in holds:
        s = int(np.ceil(start))
        while s + 1 <= end + 1e-9:
            allowed.add(s)
            s += 1
    return allowed


def motion_report(
    per_second: list[float],
    *,
    threshold: float = DEFAULT_THRESHOLD,
    allowed: set[int] | None = None,
) -> dict[str, Any]:
    allowed = allowed or set()
    low = [i for i, v in enumerate(per_second) if v < threshold and i not in allowed]
    return {
        "metric": "mean abs grayscale diff between consecutive frames (0-255), per second",
        "threshold": threshold,
        "per_second": per_second,
        "mean": round(float(np.mean(per_second)), 4) if per_second else 0.0,
        "min": round(float(min(per_second)), 4) if per_second else 0.0,
        "low_seconds": low,
        "allowed_hold_seconds": sorted(allowed),
        "passed": not low,
    }


def measure_video(
    video: Path,
    width: int,
    height: int,
    fps: int,
    output: Path,
    *,
    threshold: float = DEFAULT_THRESHOLD,
    holds: list[tuple[float, float]] | None = None,
) -> dict[str, Any]:
    frames = read_gray_frames(video, width, height)
    report = motion_report(
        motion_per_second(frames, fps),
        threshold=threshold,
        allowed=allowed_hold_seconds(holds or []),
    )
    report["video"] = str(video)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
