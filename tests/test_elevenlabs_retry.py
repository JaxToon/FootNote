from __future__ import annotations

import base64

import pytest
import requests

from fnvideo.audio import elevenlabs
from fnvideo.audio.elevenlabs import ElevenLabsClient, ElevenLabsError


class Resp:
    def __init__(self, status: int, payload: dict | None = None, headers: dict | None = None):
        self.status_code = status
        self.ok = status < 400
        self._payload = payload or {}
        self.headers = headers or {}
        self.text = f"status {status}"

    def json(self) -> dict:
        return self._payload


AUDIO = {"audio_base64": base64.b64encode(b"mp3").decode()}


class Session:
    def __init__(self, script: list):
        self.headers: dict = {}
        self.script = list(script)
        self.calls = 0

    def request(self, method, url, **kwargs):
        self.calls += 1
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture
def sleeps(monkeypatch) -> list[float]:
    calls: list[float] = []
    monkeypatch.setattr(elevenlabs.time, "sleep", calls.append)
    return calls


def _client(script: list) -> tuple[ElevenLabsClient, Session]:
    client = ElevenLabsClient("k", "voice")
    session = Session(script)
    client.session = session
    return client, session


def _speak(client: ElevenLabsClient):
    return client.speech_with_timestamps(
        "Halo", model_id="eleven_v4", output_format="mp3_44100_128", voice_settings={}
    )


def test_retries_429_and_5xx_then_succeeds(sleeps) -> None:
    client, session = _client([Resp(429), Resp(503), Resp(200, AUDIO)])
    assert _speak(client).audio == b"mp3"
    assert session.calls == 3
    assert sleeps == [1, 2]


def test_gives_up_after_five_server_errors(sleeps) -> None:
    client, session = _client([Resp(500)] * 5)
    with pytest.raises(ElevenLabsError, match="HTTP 500"):
        _speak(client)
    assert session.calls == 5


def test_client_error_is_not_retried(sleeps) -> None:
    client, session = _client([Resp(401)])
    with pytest.raises(ElevenLabsError, match="HTTP 401"):
        _speak(client)
    assert session.calls == 1 and sleeps == []


def test_network_errors_are_retried(sleeps) -> None:
    client, session = _client([requests.ConnectionError("dns"), Resp(200, AUDIO)])
    assert _speak(client).audio == b"mp3"
    assert session.calls == 2


def test_network_errors_exhaust_retries(sleeps) -> None:
    client, _ = _client([requests.Timeout("slow")] * 5)
    with pytest.raises(ElevenLabsError, match="after retries"):
        _speak(client)


def test_timestamp_parsing_prefers_alignment_and_falls_back_to_normalized(sleeps) -> None:
    norm = {
        "characters": ["H"],
        "character_start_times_seconds": [0.0],
        "character_end_times_seconds": [0.1],
    }
    client, _ = _client(
        [Resp(200, {**AUDIO, "normalized_alignment": norm}, {"x-request-id": "r1"})]
    )
    result = _speak(client)
    assert result.alignment == norm
    assert result.request_id == "r1"


def test_missing_audio_is_an_error(sleeps) -> None:
    client, _ = _client([Resp(200, {"alignment": {}})])
    with pytest.raises(ElevenLabsError, match="audio_base64"):
        _speak(client)
