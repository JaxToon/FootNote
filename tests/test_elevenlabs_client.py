from __future__ import annotations

import base64
from pathlib import Path

from fnvideo.audio.elevenlabs import ElevenLabsClient


class FakeResponse:
    ok = True
    status_code = 200
    headers = {"request-id": "req_test"}

    def json(self):
        return {
            "audio_base64": base64.b64encode(b"fake-mp3").decode(),
            "alignment": {"characters": ["H"]},
        }


class FakeSession:
    def __init__(self):
        self.headers = {}
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return FakeResponse()


def test_multilingual_v2_uses_timestamped_tts_endpoint() -> None:
    client = ElevenLabsClient("test-key", "test-voice")
    fake = FakeSession()
    client.session = fake
    result = client.speech_with_timestamps(
        "Halo",
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
        voice_settings={"stability": 0.4},
    )
    assert result.audio == b"fake-mp3"
    assert result.alignment == {"characters": ["H"]}
    assert result.request_id == "req_test"
    method, url, kwargs = fake.calls[0]
    assert method == "POST"
    assert "/test-voice/with-timestamps" in url
    assert kwargs["json"]["text"] == "Halo"


def test_eleven_v4_uses_text_to_dialogue_with_timestamps() -> None:
    client = ElevenLabsClient("test-key", "test-voice")
    fake = FakeSession()
    client.session = fake
    client.speech_with_timestamps(
        "Halo NODI",
        model_id="eleven_v4",
        output_format="mp3_44100_192",
        voice_settings={"stability": 0.45, "similarity": 0.82, "clone_strength": 0.0},
        previous_text="Sebelumnya",
        next_text="Berikutnya",
        language_code="id",
        seed=7,
    )
    method, url, kwargs = fake.calls[0]
    assert method == "POST"
    assert url.endswith("/text-to-dialogue/with-timestamps")
    body = kwargs["json"]
    assert body["inputs"] == [{"text": "Halo NODI", "voice_id": "test-voice"}]
    assert body["model_id"] == "eleven_v4"
    assert body["language_code"] == "id"
    assert body["previous_text"] == "Sebelumnya"
    assert body["future_text"] == "Berikutnya"
    assert body["seed"] == 7


def test_eleven_v4_rejects_scene_over_2000_characters() -> None:
    client = ElevenLabsClient("test-key", "test-voice")
    try:
        client.speech_with_timestamps(
            "x" * 2001, model_id="eleven_v4", output_format="mp3_44100_192", voice_settings={}
        )
    except ValueError as exc:
        assert "2,000 characters" in str(exc)
    else:
        raise AssertionError("Long scene should be rejected before the provider call")


def test_instant_voice_clone_returns_verification_requirement(tmp_path: Path) -> None:
    sample = tmp_path / "owner-voice.mp3"
    sample.write_bytes(b"fake-audio")

    class CloneResponse(FakeResponse):
        def json(self):
            return {"voice_id": "my-own-voice", "requires_verification": True}

    class CloneSession(FakeSession):
        def request(self, method, url, **kwargs):
            self.calls.append((method, url, kwargs))
            return CloneResponse()

    client = ElevenLabsClient("test-key")
    fake = CloneSession()
    client.session = fake
    result = client.clone_instant_voice(name="Owner voice", sample_paths=[sample])

    assert result.voice_id == "my-own-voice"
    assert result.requires_verification is True
    method, url, kwargs = fake.calls[0]
    assert method == "POST"
    assert url.endswith("/voices/add")
    assert kwargs["data"]["name"] == "Owner voice"
