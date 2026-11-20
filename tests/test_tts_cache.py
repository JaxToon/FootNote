from __future__ import annotations

from pathlib import Path

from fnvideo.audio import pipeline
from fnvideo.audio.elevenlabs import SpeechResult
from fnvideo.config import Settings
from fnvideo.services.spec_loader import load_episode_spec


class FakeClient:
    calls = 0

    def __init__(self, *args, **kwargs):
        pass

    def speech_with_timestamps(self, *args, **kwargs):
        type(self).calls += 1
        return SpeechResult(audio=b"fake-mp3", alignment=None, request_id=f"req-{self.calls}")


def test_tts_cache_reuses_unchanged_scene_and_force_regenerates(tmp_path: Path, monkeypatch) -> None:
    spec_path = Path("specs/fondasi-01-korelasi-bukan-kausalitas/short.yaml")
    spec = load_episode_spec(spec_path)
    settings = Settings(
        elevenlabs_api_key="test-key",
        elevenlabs_voice_id="test-voice",
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
        output_root=tmp_path / "out",
        chromium_executable=None,
    )
    monkeypatch.setattr(pipeline, "ElevenLabsClient", FakeClient)
    monkeypatch.setattr(pipeline, "probe_duration", lambda _path: 1.25)
    monkeypatch.setattr(pipeline, "build_rms_envelope", lambda _path, _fps: [0.0] * 5)

    def fake_run(command: list[str]) -> None:
        Path(command[-1]).write_bytes(b"fake-wav")

    monkeypatch.setattr(pipeline, "_run", fake_run)
    monkeypatch.setattr(pipeline, "write_srt", lambda _timing, output: output.write_text("", encoding="utf-8"))
    FakeClient.calls = 0

    output = tmp_path / "episode"
    pipeline.generate_tts(spec, output, settings, allow_draft=True)
    first_call_count = FakeClient.calls
    assert first_call_count == len(spec.scenes)

    pipeline.generate_tts(spec, output, settings, allow_draft=True)
    assert FakeClient.calls == first_call_count

    pipeline.generate_tts(spec, output, settings, allow_draft=True, force=True)
    assert FakeClient.calls == first_call_count * 2
