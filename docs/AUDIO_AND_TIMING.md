# Audio and Timing — Owner Voice Clone

## Production voice

- Production narration uses an AI clone of the owner's own voice.
- Prefer a Professional Voice Clone (PVC), fine-tuned for Eleven v4 when available, for final channel narration.
- Use Instant Voice Clone (IVC) for fast auditioning only; the pipeline can create IVCs from the owner's own samples.
- Default model `eleven_v4` is routed through `POST /v1/text-to-dialogue/with-timestamps` with one voice per scene.
- Fallback `eleven_multilingual_v2` is routed through `POST /v1/text-to-speech/{voice_id}/with-timestamps`.
- Never replace the owner's clone with a generic stock voice for production.

## TTS alignment

ElevenLabs returns character alignment with audio for both timestamped routes. The timing layer maps character alignment to phrase captions. If alignment is missing or cannot be matched to the authored caption, the fallback is proportional estimation and must be marked `estimated` in `timing.json`. Estimated alignment must never be described as exact.

For Eleven v4, keep each scene narration at or below 2,000 characters. `previous_text` and `future_text` are limited to 100 characters for the Text-to-Dialogue route.

## Voice sample quality

- IVC audition: target 1–2 minutes of clean, consistent speech.
- PVC production: treat 30 minutes as a practical lower bound; provider guidance recommends at least 1 hour and ideally close to 3 hours of clean, consistent speech. Run `fnvideo voice check-samples --profile pvc` for a local duration preflight. Record in consistent sessions and never pad duration with lower-quality audio.
- Record in natural Bahasa Indonesia with the English technical vocabulary used in F/N videos.
- Prioritize same mic, distance, gain, room, and speaking style. Avoid reverberation, music, noise, clipping, multiple speakers, and aggressive processing.
- Keep raw recordings private; never add them to Git.

## Per-scene generation and cache

- Generate one audio segment per scene; pass adjacent script text for continuity.
- Cache each scene's audio, provider request ID, and alignment using a hash of narration, voice ID, model, settings, language, and continuity context.
- Do not regenerate audio during visual-only rerenders. Use the cached `voice.wav` and `timing.json`.
- Default inter-scene gap is 0.35 seconds and the final tail is 0.25 seconds. Tune after listening; do not remove natural pauses mechanically.

## Mix defaults

- Working master: WAV, 44.1 kHz stereo.
- Final video audio: AAC, 192 kbps, 48 kHz stereo.
- Initial loudness target: -14 LUFS integrated and -1.5 dB true peak. Treat this as a delivery starting point, not a substitute for listening.
- No background music until a licensed source and ducking policy are selected.

## Lip sync

The current procedural NODI rig uses an RMS envelope to choose mouth shapes and enforces a minimum two-frame hold. This is amplitude-reactive mouth animation, not phoneme-accurate lip sync. The alignment manifest allows a later viseme/phoneme upgrade without changing episode specs.
