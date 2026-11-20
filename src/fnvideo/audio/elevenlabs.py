from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

API_BASE = "https://api.elevenlabs.io/v1"


class ElevenLabsError(RuntimeError):
    pass


@dataclass(frozen=True)
class SpeechResult:
    audio: bytes
    alignment: dict[str, Any] | None
    request_id: str | None


@dataclass(frozen=True)
class VoiceCloneResult:
    voice_id: str
    requires_verification: bool


class ElevenLabsClient:
    """Small HTTP client for authorized personal voice cloning and timestamped TTS."""

    def __init__(self, api_key: str, voice_id: str | None = None, timeout: int = 180) -> None:
        if not api_key:
            raise ValueError("ELEVENLABS_API_KEY is required")
        self.api_key = api_key
        self.voice_id = voice_id
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"xi-api-key": api_key})

    def clone_instant_voice(
        self,
        *,
        name: str,
        sample_paths: list[Path],
        description: str = "Owner-authorized F/N — FOOTNOTE narration voice",
    ) -> VoiceCloneResult:
        if not sample_paths:
            raise ValueError("At least one voice sample is required")
        files: list[tuple[str, tuple[str, Any, str]]] = []
        handles = []
        try:
            for path in sample_paths:
                if not path.is_file():
                    raise FileNotFoundError(path)
                handle = path.open("rb")
                handles.append(handle)
                mime_by_suffix = {
                    ".mp3": "audio/mpeg",
                    ".wav": "audio/wav",
                    ".m4a": "audio/mp4",
                    ".aac": "audio/aac",
                    ".flac": "audio/flac",
                    ".ogg": "audio/ogg",
                }
                mime = mime_by_suffix.get(path.suffix.lower())
                if mime is None:
                    raise ValueError(f"Unsupported voice sample format: {path.suffix}")
                files.append(("files[]", (path.name, handle, mime)))
            response = self._request(
                "POST",
                f"{API_BASE}/voices/add",
                data={"name": name, "description": description},
                files=files,
            )
            payload = response.json()
            voice_id = payload.get("voice_id")
            if not voice_id:
                raise ElevenLabsError(f"Clone endpoint returned no voice_id: {payload}")
            return VoiceCloneResult(
                voice_id=str(voice_id),
                requires_verification=bool(payload.get("requires_verification", False)),
            )
        finally:
            for handle in handles:
                handle.close()

    def speech_with_timestamps(
        self,
        text: str,
        *,
        model_id: str,
        output_format: str,
        voice_settings: dict[str, Any],
        previous_text: str | None = None,
        next_text: str | None = None,
        seed: int | None = None,
        language_code: str | None = None,
    ) -> SpeechResult:
        """Generate speech with character alignment using the model-appropriate API.

        Eleven v4 is served through Text-to-Dialogue, even for a single narrator.
        Multilingual v2 uses the timestamped Text-to-Speech endpoint.
        """
        if not self.voice_id:
            raise ValueError("ELEVENLABS_VOICE_ID is required")
        if not text.strip():
            raise ValueError("Narration text cannot be empty")

        if model_id == "eleven_v4":
            if len(text) > 2000:
                raise ValueError(
                    "Eleven v4 Text-to-Dialogue requests should stay at or below 2,000 characters per scene. "
                    "Split the narration into shorter scenes."
                )
            body: dict[str, Any] = {
                "inputs": [{"text": text, "voice_id": self.voice_id}],
                "model_id": model_id,
                "settings": voice_settings,
            }
            if language_code:
                body["language_code"] = language_code
            if previous_text:
                body["previous_text"] = previous_text[-100:]
            if next_text:
                body["future_text"] = next_text[:100]
            endpoint = f"{API_BASE}/text-to-dialogue/with-timestamps"
        else:
            body = {
                "text": text,
                "model_id": model_id,
                "voice_settings": voice_settings,
            }
            if previous_text:
                body["previous_text"] = previous_text[-500:]
            if next_text:
                body["next_text"] = next_text[:500]
            endpoint = f"{API_BASE}/text-to-speech/{self.voice_id}/with-timestamps"

        if seed is not None:
            body["seed"] = seed
        response = self._request(
            "POST",
            endpoint,
            params={"output_format": output_format},
            json=body,
        )
        payload = response.json()
        audio_b64 = payload.get("audio_base64")
        if not audio_b64:
            raise ElevenLabsError("Timestamped speech response did not contain audio_base64")
        return SpeechResult(
            audio=base64.b64decode(audio_b64),
            alignment=payload.get("alignment") or payload.get("normalized_alignment"),
            request_id=response.headers.get("request-id") or response.headers.get("x-request-id"),
        )

    def _request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        last_error: Exception | None = None
        for attempt in range(5):
            try:
                response = self.session.request(method, url, timeout=self.timeout, **kwargs)
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < 4:
                        time.sleep(min(2**attempt, 12))
                        continue
                if not response.ok:
                    detail = response.text[:1200]
                    raise ElevenLabsError(
                        f"ElevenLabs API returned HTTP {response.status_code}: {detail}"
                    )
                return response
            except requests.RequestException as exc:
                last_error = exc
                if attempt < 4:
                    time.sleep(min(2**attempt, 12))
        raise ElevenLabsError(f"ElevenLabs request failed after retries: {last_error}")
