from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from fnvideo.audio.elevenlabs import ElevenLabsClient
from fnvideo.audio.timing import (
    build_rms_envelope,
    caption_timings,
    map_mouth_shapes,
    probe_duration,
    resolve_beats,
    write_srt,
)
from fnvideo.config import Settings
from fnvideo.models.episode import EpisodeSpec
from fnvideo.services.clarity import editorial_gate


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr[-3000:]}")


def _voice_settings(settings: Settings, model_id: str, speed: float = 1.0) -> dict[str, Any]:
    if model_id == "eleven_v4":
        if speed != 1.0:
            raise ValueError(
                "Eleven v4 does not support the speed control; set voice.speed to 1.0 in the episode spec."
            )
        # Eleven v4 uses Stability and Similarity. Older-model controls such as
        # Style, Speaker Boost and Speed are intentionally omitted.
        return {
            "stability": settings.elevenlabs_stability,
            "similarity": settings.elevenlabs_similarity,
            "clone_strength": settings.elevenlabs_clone_strength,
        }
    return {
        "stability": settings.elevenlabs_stability,
        "similarity_boost": settings.elevenlabs_similarity,
        "style": settings.elevenlabs_style,
        "use_speaker_boost": settings.elevenlabs_speaker_boost,
        "speed": speed,
    }


def generate_tts(
    spec: EpisodeSpec,
    output_dir: Path,
    settings: Settings,
    *,
    allow_draft: bool = False,
    force: bool = False,
) -> Path:
    if spec.editorial_status != "approved" and not allow_draft:
        raise RuntimeError(
            "Human editorial approval is required before TTS. Set editorial_status: approved "
            "after fact-checking, or pass --allow-draft for a clearly marked test render."
        )
    # Approved specs must pass the clarity rules before any (paid) narration is generated.
    editorial_gate(spec)
    if not settings.elevenlabs_api_key or not settings.elevenlabs_voice_id:
        raise RuntimeError(
            "Voice clone is not configured. Set ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID in .env. "
            "Create your own voice clone with `fnvideo voice clone` first."
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_dir = output_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    client = ElevenLabsClient(settings.elevenlabs_api_key, settings.elevenlabs_voice_id)
    speech_files: list[Path] = []
    scene_records: list[dict[str, Any]] = []
    previous_text: str | None = None

    for index, scene in enumerate(spec.scenes):
        next_text = spec.scenes[index + 1].narration if index + 1 < len(spec.scenes) else None
        voice_settings = _voice_settings(settings, settings.elevenlabs_model_id, spec.voice.speed)
        seed_material = f"{spec.meta.id}:{scene.id}:{settings.elevenlabs_model_id}".encode()
        seed = int(hashlib.sha256(seed_material).hexdigest()[:8], 16)
        cache_input = {
            "narration": scene.narration,
            "model_id": settings.elevenlabs_model_id,
            "voice_id": settings.elevenlabs_voice_id,
            "output_format": settings.elevenlabs_output_format,
            "voice_settings": voice_settings,
            "previous_text": previous_text,
            "next_text": next_text,
            "seed": seed,
            "language_code": settings.elevenlabs_language_code
            if settings.elevenlabs_model_id == "eleven_v4"
            else None,
            "provider_route": "text-to-dialogue/with-timestamps"
            if settings.elevenlabs_model_id == "eleven_v4"
            else "text-to-speech/with-timestamps",
        }
        cache_hash = hashlib.sha256(
            json.dumps(
                cache_input, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest()
        mp3_path = audio_dir / f"{scene.id}.mp3"
        cache_path = audio_dir / f"{scene.id}.cache.json"
        cached: dict[str, Any] | None = None
        if not force and mp3_path.is_file() and cache_path.is_file():
            try:
                candidate = json.loads(cache_path.read_text(encoding="utf-8"))
                if candidate.get("input_hash") == cache_hash:
                    cached = candidate
            except (OSError, json.JSONDecodeError):
                cached = None

        if cached is not None:
            alignment = cached.get("alignment")
            request_id = cached.get("request_id")
            duration = float(cached.get("duration_seconds") or probe_duration(mp3_path))
            print(f"[TTS CACHE] {scene.id}: {duration:.2f}s")
        else:
            result = client.speech_with_timestamps(
                scene.narration,
                model_id=settings.elevenlabs_model_id,
                output_format=settings.elevenlabs_output_format,
                voice_settings=voice_settings,
                previous_text=previous_text,
                next_text=next_text,
                seed=seed,
                language_code=settings.elevenlabs_language_code
                if settings.elevenlabs_model_id == "eleven_v4"
                else None,
            )
            tmp_mp3 = mp3_path.with_suffix(".tmp.mp3")
            tmp_mp3.write_bytes(result.audio)
            tmp_mp3.replace(mp3_path)
            duration = probe_duration(mp3_path)
            alignment = result.alignment
            request_id = result.request_id
            cache_payload = {
                "input_hash": cache_hash,
                "duration_seconds": duration,
                "alignment": alignment,
                "request_id": request_id,
            }
            cache_path.write_text(
                json.dumps(cache_payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"[TTS] {scene.id}: {duration:.2f}s")

        speech_files.append(mp3_path)
        pad = settings.audio_gap_seconds if index < len(spec.scenes) - 1 else 0.25
        scene_records.append(
            {
                "id": scene.id,
                "title": scene.title,
                "audio_file": str(mp3_path.relative_to(output_dir)),
                "speech_duration_seconds": duration,
                "duration_seconds": duration + pad,
                "alignment": alignment,
                "captions": (captions := caption_timings(scene, duration, alignment)),
                "beats": resolve_beats(scene, duration, duration + pad, captions, alignment),
                "request_id": request_id,
            }
        )
        previous_text = scene.narration

    # Concat speech with intentional inter-scene pauses. Use a filter graph to avoid MP3 concat quirks.
    inputs: list[str] = []
    filters: list[str] = []
    concat_labels: list[str] = []
    input_index = 0
    for i, path in enumerate(speech_files):
        inputs.extend(["-i", str(path)])
        filters.append(
            f"[{input_index}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[a{input_index}]"
        )
        concat_labels.append(f"[a{input_index}]")
        input_index += 1
        gap = settings.audio_gap_seconds if i < len(speech_files) - 1 else 0.25
        if gap > 0:
            inputs.extend(
                [
                    "-f",
                    "lavfi",
                    "-t",
                    f"{gap:.3f}",
                    "-i",
                    "anullsrc=channel_layout=stereo:sample_rate=44100",
                ]
            )
            filters.append(
                f"[{input_index}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[g{input_index}]"
            )
            concat_labels.append(f"[g{input_index}]")
            input_index += 1
    filters.append("".join(concat_labels) + f"concat=n={len(concat_labels)}:v=0:a=1[outa]")
    voice_wav = output_dir / "voice.wav"
    _run(
        [
            "ffmpeg",
            "-y",
            *inputs,
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[outa]",
            "-ar",
            "44100",
            "-ac",
            "2",
            str(voice_wav),
        ]
    )

    cursor = 0.0
    for scene in scene_records:
        scene["start_seconds"] = cursor
        scene["end_seconds"] = cursor + scene["duration_seconds"]
        cursor = scene["end_seconds"]
        scene.pop(
            "alignment", None
        )  # Do not keep full alignment payload in public timing manifest.
    envelope = build_rms_envelope(voice_wav, spec.meta.fps)
    timing = {
        "episode_id": spec.meta.id,
        "fps": spec.meta.fps,
        "audio_duration_seconds": probe_duration(voice_wav),
        "scene_duration_seconds": cursor,
        "gap_seconds": settings.audio_gap_seconds,
        "timing_source": "ElevenLabs character alignment; caption fallback explicitly marked estimated",
        "scenes": scene_records,
        "rms_envelope": envelope,
        "mouth_shapes": map_mouth_shapes(envelope),
    }
    timing_path = output_dir / "timing.json"
    timing_path.write_text(json.dumps(timing, ensure_ascii=False, indent=2), encoding="utf-8")
    write_srt(timing, output_dir / "captions.srt")
    print(f"[AUDIO] Wrote {voice_wav}, {timing_path}, captions.srt")
    return timing_path


def preview_voice(settings: Settings, text: str, output: Path, model_id: str | None = None) -> Path:
    if not settings.elevenlabs_api_key or not settings.elevenlabs_voice_id:
        raise RuntimeError("Set ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID in .env first")
    client = ElevenLabsClient(settings.elevenlabs_api_key, settings.elevenlabs_voice_id)
    selected_model = model_id or settings.elevenlabs_model_id
    result = client.speech_with_timestamps(
        text,
        model_id=selected_model,
        output_format=settings.elevenlabs_output_format,
        voice_settings=_voice_settings(settings, selected_model, 1.0),
        seed=20261119,
        language_code=settings.elevenlabs_language_code if selected_model == "eleven_v4" else None,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(result.audio)
    return output
