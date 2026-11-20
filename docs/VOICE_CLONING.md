# Personal Voice Cloning — F/N Narration

## Non-negotiable decision

F/N narration uses an AI clone of the owner's **own voice**. Do not substitute a stock narrator, a generic AI voice, Piper, or someone else's voice for production. The owner supplies the recordings and creates/verifies the clone in their own ElevenLabs account. This repository stores only the resulting `voice_id` in the local `.env`; raw recordings stay under the git-ignored `private/voice_samples/` directory.

## Recommended quality path

**Final production: Professional Voice Clone (PVC), fine-tuned for Eleven v4.** This is the preferred route when voice identity and likeness matter most. ElevenLabs describes PVC as a dedicated model trained on a larger voice dataset and treats 30 minutes as a practical lower bound and recommends at least an hour, ideally close to three hours, of clean source audio. The current PVC quickstart lists Creator plan or higher for API creation; confirm the exact plan/availability in your account before recording a large dataset.

**Fast audition only: Instant Voice Clone (IVC).** Use around 1–2 minutes of clean audio to quickly test your mic, accent match, narration style, and the pipeline. IVC is a fast approximation rather than a custom-trained voice model. Do not assume that an IVC result is good enough for the final channel voice.

A useful staged approach is:

1. Record the 1–2 minute script in `assets/voice/voice_clone_recording_script_id.md`.
2. Run local validation and create an IVC with `fnvideo voice clone` for a fast audition.
3. Listen to `fnvideo voice preview` using the same test text. Reject the clone if it does not sound recognizably like the owner.
4. For final production, record a consistent PVC dataset (30 minutes as a practical lower bound; aim for at least 1 hour and ideally close to 3 hours) following `assets/voice/pvc_recording_plan.md`, create a PVC in the owner's ElevenLabs account, complete its identity verification, and fine-tune it for Eleven v4 when that option is available.
5. Put the final PVC `voice_id` in `.env`. No code changes are needed to switch from IVC to PVC.

## Recording protocol

- Record only the owner's own voice. The CLI requires `--i-own-this-voice` before creating an IVC.
- Use one quiet, acoustically controlled room. Avoid room echo, fan/traffic noise, keyboard noise, music, clipping, plosives, and multiple speakers.
- Keep the microphone, distance, input gain, room, and delivery style consistent across sessions.
- Use dry speech; do not bake in reverb, EQ, compression, aggressive noise reduction, or loudness normalization.
- Speak in the language and accent used by F/N: conversational Indonesian with familiar English technical terms.
- Record several 10–20 minute sessions rather than one exhausting marathon for PVC.
- Prefer high-quality and consistent source clips over simply maximizing the total duration.
- Keep a private backup of every original sample and note which files were used for each clone version.

## ElevenLabs model routing (important)

- Default: `eleven_v4` for quality-first educational narration. Current ElevenLabs documentation routes v4 through **Text-to-Dialogue**, including its `with-timestamps` endpoint. The adapter sends one dialogue input with the owner's `voice_id` per scene.
- Fallback/A-B: `eleven_multilingual_v2` uses the timestamped **Text-to-Speech** endpoint. Compare both with the same cloned voice and audition text if Indonesian pronunciation, cadence, stability, or output quality needs tuning.
- Indonesian language code is `id` for Eleven v4.
- Keep each Eleven v4 scene narration at or below 2,000 characters per request. Split long narration into separate scenes rather than sending one oversized request.
- For an Eleven v4 PVC fine-tuned on v4, `clone_strength` controls closeness to training samples. Provider guidance recommends starting at `0`; only audition higher values (for example `0.5`) when the owner's accent or unique voice traits are not preserved adequately. The pipeline exposes this as `ELEVENLABS_CLONE_STRENGTH`.
- ElevenLabs generation is nondeterministic. The pipeline caches audio and alignment so visual-only rerenders never regenerate narration. A seed is passed as a best-effort consistency hint, not a determinism guarantee.

## Configure and audition

Set these values in the local `.env` after creating the clone:

```dotenv
ELEVENLABS_API_KEY=your_private_key
ELEVENLABS_VOICE_ID=your_own_verified_voice_id
ELEVENLABS_MODEL_ID=eleven_v4
ELEVENLABS_LANGUAGE_CODE=id
ELEVENLABS_CLONE_STRENGTH=0.0
```

For a fast IVC audition:

```powershell
fnvideo voice check-samples --profile ivc --samples private/voice_samples/*.mp3
fnvideo voice clone --name "Firgy - F/N Narration IVC" --samples private/voice_samples/*.mp3 --i-own-this-voice
fnvideo voice preview --output out/voice/owner-voice-preview.mp3
```

For a PVC, first preflight a separate long-form dataset with `fnvideo voice check-samples --profile pvc --samples private/voice_samples/pvc/*.mp3`. Create and verify it in the owner's ElevenLabs account, fine-tune for Eleven v4 if available, and paste the resulting `voice_id` into `.env`. The CLI does not bypass provider identity verification. The `voice clone` CLI command creates IVC only; it does not create PVC.

Audition the same text on `eleven_v4` and `eleven_multilingual_v2`:

```powershell
fnvideo voice preview --model eleven_v4 --output out/voice/audition-v4.mp3
fnvideo voice preview --model eleven_multilingual_v2 --output out/voice/audition-multilingual-v2.mp3
```

Owner review must cover voice likeness, Indonesian accent, consonants, English technical terms, sentence endings, pacing, breaths, emotional range, and scene-to-scene consistency. A technically valid file is not proof that the clone sounds like the owner.

## Privacy, rights, and publishing

- Never commit `.env`, API keys, original voice recordings, generated private audio, or voice clone credentials.
- Never upload third-party voice recordings without the required rights and authorization.
- The clone remains in the owner's provider account. This repository stores only its ID.
- Check the current subscription, plan, and commercial-use terms before monetization. Provider documentation distinguishes commercial usage rights by plan.
- Manual listening approval is mandatory before production render or publishing.

## Official provider references

- Voice cloning overview: https://elevenlabs.io/docs/eleven-creative/voices/voice-cloning
- Professional Voice Clone API quickstart: https://elevenlabs.io/docs/eleven-api/guides/how-to/voices/professional-voice-cloning
- Text-to-Dialogue with timestamps: https://elevenlabs.io/docs/api-reference/text-to-dialogue/convert-with-timestamps
- Timestamped Text-to-Speech (Multilingual v2): https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps
- ElevenLabs model overview: https://elevenlabs.io/docs/overview/models
