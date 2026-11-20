from __future__ import annotations

import json
import re
import subprocess
import wave
from pathlib import Path
from typing import Any

import numpy as np

CAPTION_LEAD_SECONDS = 0.08


def _find_from(haystack: str, needle: str, cursor: int) -> int:
    return haystack.casefold().find(needle.casefold(), cursor)


def _aligned_windows(
    alignment: dict[str, Any] | None, phrases: list[str]
) -> list[tuple[float, float]] | None:
    """Locate every caption phrase, in order, in provider character alignment.

    Returns None unless *all* phrases match, so a scene is never half exact, half guessed.
    """
    if not alignment:
        return None
    chars = alignment.get("characters", [])
    starts = alignment.get("character_start_times_seconds", [])
    ends = alignment.get("character_end_times_seconds", [])
    if not chars or len(chars) != len(starts) or len(chars) != len(ends):
        return None
    joined = "".join(chars)
    if len(joined) != len(chars):  # multi-char entries would break index mapping
        return None
    cursor = 0
    windows: list[tuple[float, float]] = []
    for phrase in phrases:
        idx = _find_from(joined, phrase, cursor)
        if idx < 0:
            return None
        span = range(idx, idx + len(phrase))
        valid_starts = [float(starts[i]) for i in span if starts[i] is not None]
        valid_ends = [float(ends[i]) for i in span if ends[i] is not None]
        if not valid_starts or not valid_ends:
            return None
        windows.append((min(valid_starts), max(valid_ends)))
        cursor = idx + len(phrase)
    return windows


def _estimated_windows(
    transcript: str, phrases: list[str], duration: float
) -> list[tuple[float, float]]:
    """Estimate caption windows without provider timing.

    If every phrase occurs verbatim and in order, place it proportionally by character
    position. Otherwise captions are paraphrases: tile the speech duration in order,
    weighted by caption length.
    """
    total = max(1, len(transcript))
    cursor = 0
    positions: list[tuple[int, int]] = []
    for phrase in phrases:
        idx = _find_from(transcript, phrase, cursor)
        if idx < 0:
            break
        positions.append((idx, idx + len(phrase)))
        cursor = idx + len(phrase)
    if len(positions) == len(phrases):
        return [(duration * a / total, duration * b / total) for a, b in positions]
    weights = [max(1, len(p)) for p in phrases]
    scale = duration / sum(weights)
    windows: list[tuple[float, float]] = []
    t = 0.0
    for w in weights:
        windows.append((t, t + w * scale))
        t += w * scale
    return windows


def caption_timings(
    scene: Any, duration: float, alignment: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """Scene-relative caption windows within [0, duration] (speech duration).

    Each caption is held until the next one starts, so there are no blank gaps while the
    narrator is still speaking; the last caption holds until the end of speech.
    """
    phrases = [c.text for c in scene.captions]
    exact = _aligned_windows(alignment, phrases)
    raw = exact if exact is not None else _estimated_windows(scene.narration, phrases, duration)
    quality = "provider_alignment" if exact is not None else "estimated"
    starts = [max(0.0, min(duration, s - CAPTION_LEAD_SECONDS)) for s, _ in raw]
    result: list[dict[str, Any]] = []
    for i, caption in enumerate(scene.captions):
        start = starts[i]
        # Contiguous: hand over exactly when the next caption starts (no overlap, no gap).
        end = starts[i + 1] if i + 1 < len(raw) else max(duration, raw[i][1])
        result.append(
            {
                "text": caption.text,
                "highlight": caption.highlight,
                "start": round(start, 4),
                "end": round(end, 4),
                "timing_quality": quality,
            }
        )
    return result


_WORD = re.compile(r"\w[\w'-]*", re.UNICODE)


def _word_start(
    word: str, narration: str, speech_duration: float, alignment: dict[str, Any] | None
) -> tuple[float, str]:
    """Start time of the first whole-word occurrence of *word*, plus its timing quality."""
    # tolerate punctuation copied from the caption ("word:Bukan." == "word:Bukan")
    target = word.strip(".,!?:;\"'()…").casefold()
    exact = _aligned_windows(alignment, []) is not None if alignment else False
    if alignment and exact:
        joined = "".join(alignment["characters"])
        starts = alignment["character_start_times_seconds"]
        for m in _WORD.finditer(joined):
            if m.group(0).casefold() == target and starts[m.start()] is not None:
                return float(starts[m.start()]), "provider_alignment"
    for m in _WORD.finditer(narration):
        if m.group(0).casefold() == target:
            return speech_duration * m.start() / max(1, len(narration)), "estimated"
    raise ValueError(f"beat word '{word}' does not occur in the scene narration")


def resolve_beats(
    scene: Any,
    speech_duration: float,
    scene_duration: float,
    captions: list[dict[str, Any]],
    alignment: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Resolve each beat's `at` to scene-relative seconds, sorted by time."""
    resolved: list[dict[str, Any]] = []
    for beat in getattr(scene, "beats", []):
        quality = "exact"
        if isinstance(beat.at, float):
            t = beat.at * scene_duration
        elif beat.at.startswith("caption:"):
            cap = captions[int(beat.at.split(":", 1)[1])]
            t, quality = float(cap["start"]), cap.get("timing_quality", "estimated")
        else:
            t, quality = _word_start(
                beat.at.split(":", 1)[1], scene.narration, speech_duration, alignment
            )
        resolved.append(
            {
                "t": round(min(max(0.0, t), scene_duration), 4),
                "target": beat.target,
                "action": beat.action,
                "duration": beat.duration,
                "timing_quality": quality,
            }
        )
    return sorted(resolved, key=lambda b: b["t"])


def estimate_scene_seconds(scene: Any) -> float:
    """Speech-duration estimate for previews (~13 characters/second Indonesian narration)."""
    return float(scene.duration_hint_seconds or max(4.0, len(scene.narration) / 13.0))


def build_estimated_timing(
    spec: Any, gap_seconds: float, tail_seconds: float = 0.25
) -> dict[str, Any]:
    """Timing manifest from duration hints only; used for previews and silent test renders."""
    cursor = 0.0
    scenes: list[dict[str, Any]] = []
    for index, scene in enumerate(spec.scenes):
        speech = estimate_scene_seconds(scene)
        pad = gap_seconds if index < len(spec.scenes) - 1 else tail_seconds
        captions = caption_timings(scene, speech, None)
        scenes.append(
            {
                "id": scene.id,
                "title": scene.title,
                "speech_duration_seconds": speech,
                "duration_seconds": speech + pad,
                "start_seconds": cursor,
                "end_seconds": cursor + speech + pad,
                "captions": captions,
                "beats": resolve_beats(scene, speech, speech + pad, captions, None),
            }
        )
        cursor += speech + pad
    return {
        "episode_id": spec.meta.id,
        "fps": spec.meta.fps,
        "scene_duration_seconds": cursor,
        "gap_seconds": gap_seconds,
        "timing_source": "estimated from duration hints; no audio",
        "scenes": scenes,
        "rms_envelope": [],
        "mouth_shapes": [],
        "preview_timing_only": True,
    }


def scene_frame_range(start_seconds: float, end_seconds: float, fps: int) -> tuple[int, int]:
    """Global [first, last) frame indices for a scene.

    Frames come from cumulative boundaries so rounding never drifts across scenes:
    concatenated scene frame counts always sum to round(total * fps).
    """
    first = int(round(start_seconds * fps))
    last = max(first + 1, int(round(end_seconds * fps)))
    return first, last


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


def mouth_shape_for(amp: float) -> str:
    if amp < 0.05:
        return "smile"
    if amp < 0.14:
        return "small"
    if amp < 0.28:
        return "mid"
    return "wide"


def map_mouth_shapes(envelope: list[float], minimum_hold_frames: int = 2) -> list[str]:
    """Map a per-frame RMS envelope to mouth shapes with a deterministic minimum hold.

    Runs shorter than *minimum_hold_frames* are absorbed into the previous run (or the next
    run when at the start), so no shape is shown for fewer frames than the hold unless the
    whole track is shorter than the hold.
    """
    runs: list[list[Any]] = []
    for amp in envelope:
        shape = mouth_shape_for(amp)
        if runs and runs[-1][0] == shape:
            runs[-1][1] += 1
        else:
            runs.append([shape, 1])
    merged: list[list[Any]] = []
    carry = 0
    for shape, count in runs:
        count += carry
        carry = 0
        if count < minimum_hold_frames:
            if merged:
                merged[-1][1] += count
            else:
                carry = count
            continue
        if merged and merged[-1][0] == shape:
            merged[-1][1] += count
        else:
            merged.append([shape, count])
    if carry:  # whole track shorter than the hold: keep a single stable shape
        merged.append([runs[0][0], carry])
    out: list[str] = []
    for shape, count in merged:
        out.extend([shape] * count)
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
