from __future__ import annotations

import json
import subprocess
import wave
from pathlib import Path
from typing import Any

import numpy as np


def _alignment_phrase(
    alignment: dict[str, Any] | None, transcript: str, phrase: str
) -> tuple[float, float] | None:
    if not alignment:
        return None
    chars = alignment.get("characters", [])
    starts = alignment.get("character_start_times_seconds", [])
    ends = alignment.get("character_end_times_seconds", [])
    if not chars or len(chars) != len(starts) or len(chars) != len(ends):
        return None
    joined = "".join(chars)
    idx = joined.casefold().find(phrase.casefold())
    if idx < 0 or idx + len(phrase) > len(starts):
        return None
    valid_starts = [float(x) for x in starts[idx : idx + len(phrase)] if x is not None]
    valid_ends = [float(x) for x in ends[idx : idx + len(phrase)] if x is not None]
    if not valid_starts or not valid_ends:
        return None
    return min(valid_starts), max(valid_ends)


def _estimate_phrase_windows(
    transcript: str, phrases: list[str], duration: float
) -> list[dict[str, Any]]:
    total_chars = max(1, len(transcript))
    results: list[dict[str, Any]] = []
    cursor = 0.0
    for phrase in phrases:
        idx = transcript.casefold().find(phrase.casefold())
        if idx >= 0:
            start = duration * idx / total_chars
            end = duration * min(total_chars, idx + len(phrase)) / total_chars
        else:
            start = cursor
            end = min(duration, start + duration / max(1, len(phrases)))
        start = max(cursor, start)
        end = max(start + 0.12, end)
        results.append(
            {"start": min(start, duration), "end": min(end, duration), "estimated": True}
        )
        cursor = min(end, duration)
    return results


def caption_timings(
    scene: Any, duration: float, alignment: dict[str, Any] | None
) -> list[dict[str, Any]]:
    phrases = [c.text for c in scene.captions]
    windows: list[dict[str, Any]] = []
    for phrase in phrases:
        match = _alignment_phrase(alignment, scene.narration, phrase)
        if match:
            windows.append({"start": match[0], "end": match[1], "estimated": False})
        else:
            windows = _estimate_phrase_windows(scene.narration, phrases, duration)
            break
    # Slightly expand short captions for readability, but keep scene boundaries.
    for i, window in enumerate(windows):
        window["start"] = max(0.0, float(window["start"]) - 0.08)
        window["end"] = min(
            duration, max(float(window["end"]) + 0.18, float(window["start"]) + 0.45)
        )
        if i + 1 < len(windows):
            window["end"] = min(float(window["end"]), float(windows[i + 1]["start"]) + 0.02)
    return [
        {
            "text": caption.text,
            "highlight": caption.highlight,
            "start": windows[i]["start"],
            "end": windows[i]["end"],
            "timing_quality": "estimated" if windows[i]["estimated"] else "provider_alignment",
        }
        for i, caption in enumerate(scene.captions)
    ]


def probe_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(json.loads(result.stdout)["format"]["duration"])


def build_rms_envelope(wav_path: Path, fps: int) -> list[float]:
    with wave.open(str(wav_path), "rb") as wav:
        channels = wav.getnchannels()
        sample_rate = wav.getframerate()
        frames = wav.getnframes()
        raw = wav.readframes(frames)
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    per_frame = max(1, int(sample_rate / fps))
    values: list[float] = []
    for start in range(0, len(samples), per_frame):
        chunk = samples[start : start + per_frame]
        if len(chunk) == 0:
            values.append(0.0)
        else:
            rms = float(np.sqrt(np.mean(np.square(chunk)))) / 32768.0
            values.append(min(1.0, rms * 3.2))
    return values


def map_mouth_shapes(envelope: list[float], minimum_hold_frames: int = 2) -> list[str]:
    raw: list[str] = []
    for amp in envelope:
        if amp < 0.05:
            shape = "smile"
        elif amp < 0.14:
            shape = "small"
        elif amp < 0.28:
            shape = "mid"
        else:
            shape = "wide"
        raw.append(shape)
    # Deterministic minimum-hold pass to avoid one-frame flicker.
    out: list[str] = []
    i = 0
    while i < len(raw):
        j = i + 1
        while j < len(raw) and raw[j] == raw[i]:
            j += 1
        run = raw[i:j]
        if len(run) < minimum_hold_frames and out:
            run = [out[-1]] * len(run)
        out.extend(run)
        i = j
    return out


def write_srt(timing: dict[str, Any], output: Path) -> None:
    def stamp(seconds: float) -> str:
        ms = int(round(seconds * 1000))
        h, rem = divmod(ms, 3_600_000)
        m, rem = divmod(rem, 60_000)
        s, ms = divmod(rem, 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    rows: list[str] = []
    index = 1
    for scene in timing["scenes"]:
        for cap in scene["captions"]:
            start = float(scene["start_seconds"]) + float(cap["start"])
            end = float(scene["start_seconds"]) + float(cap["end"])
            rows.extend([str(index), f"{stamp(start)} --> {stamp(end)}", cap["text"], ""])
            index += 1
    output.write_text("\n".join(rows), encoding="utf-8")
