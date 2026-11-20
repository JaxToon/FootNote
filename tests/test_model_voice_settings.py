from __future__ import annotations

from pathlib import Path

import pytest

from fnvideo.audio.pipeline import _voice_settings
from fnvideo.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        elevenlabs_api_key="key",
        elevenlabs_voice_id="voice",
        elevenlabs_model_id="eleven_v4",
        elevenlabs_output_format="mp3_44100_192",
        elevenlabs_stability=0.45,
        elevenlabs_similarity=0.82,
        elevenlabs_clone_strength=0.0,
        elevenlabs_language_code="id",
        elevenlabs_style=0.2,
        elevenlabs_speaker_boost=True,
        audio_gap_seconds=0.35,
        target_lufs=-14,
        true_peak_db=-1.5,
        output_root=Path("out"),
        chromium_executable=None,
    )


def test_eleven_v4_only_receives_supported_voice_controls(settings: Settings) -> None:
    assert _voice_settings(settings, "eleven_v4") == {
        "stability": 0.45,
        "similarity": 0.82,
        "clone_strength": 0.0,
    }


def test_multilingual_v2_receives_legacy_controls(settings: Settings) -> None:
    result = _voice_settings(settings, "eleven_multilingual_v2", 1.05)
    assert result["style"] == 0.2
    assert result["use_speaker_boost"] is True
    assert result["speed"] == 1.05


def test_eleven_v4_rejects_speed_override(settings: Settings) -> None:
    with pytest.raises(ValueError, match="does not support the speed control"):
        _voice_settings(settings, "eleven_v4", 1.1)
