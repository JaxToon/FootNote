from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

SUPPORTED_SUFFIXES = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}


@dataclass(frozen=True)
class VoiceSample:
    path: str
    duration_seconds: float
    size_bytes: int


def inspect_voice_samples(
    paths: list[Path], *, profile: str = "ivc"
) -> tuple[list[VoiceSample], list[str], list[str]]:
    """Inspect samples locally without uploading audio to a provider.

    IVC and PVC have very different recommended training lengths, so the
    selected profile controls duration warnings and minimums.
    """
    if profile not in {"ivc", "pvc"}:
        raise ValueError("profile must be 'ivc' or 'pvc'")
    if not paths:
        raise ValueError("No voice sample files were provided")

    samples: list[VoiceSample] = []
    errors: list[str] = []
    warnings: list[str] = []
    seen: set[Path] = set()

    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if not path.is_file():
            errors.append(f"File not found: {path}")
            continue
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            errors.append(f"Unsupported audio extension: {path.name}")
            continue
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "json",
                    str(path),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            duration = float(json.loads(result.stdout)["format"]["duration"])
        except (subprocess.CalledProcessError, KeyError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"Could not read duration for {path}: {exc}")
            continue
        samples.append(VoiceSample(str(path), duration, path.stat().st_size))
        if duration < 5:
            errors.append(
                f"{path.name} is {duration:.1f}s; each sample must be at least 5 seconds."
            )

    total = sum(sample.duration_seconds for sample in samples)
    if profile == "ivc":
        if total < 10:
            errors.append(
                f"Combined sample duration is {total:.1f}s; at least 10 seconds is required for IVC."
            )
        if 0 < total < 60:
            warnings.append(
                "For stronger IVC results, target 1–2 minutes of clean, consistent speech."
            )
        if total > 180:
            warnings.append(
                "More than 3 minutes may add little benefit and can reduce clone consistency; select the cleanest 1–2 minutes for IVC."
            )
    else:
        if total < 1800:
            errors.append(
                f"Combined sample duration is {total / 60:.1f} minutes; prepare at least 30 minutes for PVC."
            )
        elif total < 3600:
            warnings.append(
                "PVC can use this dataset, but provider guidance recommends at least 1 hour and ideally close to 3 hours for best results."
            )
        elif total <= 10800:
            warnings.append(
                "PVC dataset is within the 1–3 hour target; prioritize consistent clean audio over adding more minutes."
            )
        else:
            warnings.append(
                "Dataset exceeds 3 hours. Review for consistency and keep only clean samples in the intended narration style."
            )
    if len(samples) > 1:
        warnings.append(
            "Check that every sample uses the same room, microphone, distance, speaking style, and volume."
        )
    return samples, errors, warnings


def samples_as_dicts(samples: list[VoiceSample]) -> list[dict[str, object]]:
    return [asdict(sample) for sample in samples]
