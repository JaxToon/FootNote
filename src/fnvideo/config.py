from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    elevenlabs_api_key: str | None
    elevenlabs_voice_id: str | None
    elevenlabs_model_id: str
    elevenlabs_output_format: str
    elevenlabs_stability: float
    elevenlabs_similarity: float
    elevenlabs_clone_strength: float
    elevenlabs_language_code: str
    elevenlabs_style: float
    elevenlabs_speaker_boost: bool
    audio_gap_seconds: float
    target_lufs: float
    true_peak_db: float
    output_root: Path
    chromium_executable: str | None


def load_settings(root: Path | None = None) -> Settings:
    root = root or Path.cwd()
    load_dotenv(root / ".env", override=False)
    return Settings(
        elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY") or None,
        elevenlabs_voice_id=os.getenv("ELEVENLABS_VOICE_ID") or None,
        elevenlabs_model_id=os.getenv("ELEVENLABS_MODEL_ID", "eleven_v4"),
        elevenlabs_output_format=os.getenv("ELEVENLABS_OUTPUT_FORMAT", "mp3_44100_192"),
        elevenlabs_stability=float(os.getenv("ELEVENLABS_STABILITY", "0.45")),
        elevenlabs_similarity=float(os.getenv("ELEVENLABS_SIMILARITY", "0.82")),
        elevenlabs_clone_strength=float(os.getenv("ELEVENLABS_CLONE_STRENGTH", "0.0")),
        elevenlabs_language_code=os.getenv("ELEVENLABS_LANGUAGE_CODE", "id"),
        elevenlabs_style=float(os.getenv("ELEVENLABS_STYLE", "0.20")),
        elevenlabs_speaker_boost=os.getenv("ELEVENLABS_SPEAKER_BOOST", "true").lower() == "true",
        audio_gap_seconds=float(os.getenv("AUDIO_GAP_SECONDS", "0.35")),
        target_lufs=float(os.getenv("TARGET_LOUDNESS_LUFS", "-14")),
        true_peak_db=float(os.getenv("TRUE_PEAK_DB", "-1.5")),
        output_root=Path(os.getenv("FNVIDEO_OUTPUT_ROOT", "out")),
        chromium_executable=os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE") or None,
    )
