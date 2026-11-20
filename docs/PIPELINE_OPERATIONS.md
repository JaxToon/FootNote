# Pipeline Operations

## Typical repeatable production cycle

1. Create/copy an episode YAML spec.
2. Draft the narration and visuals; keep source notes and caveats.
3. Run `fnvideo validate` and inspect `fnvideo plan`.
4. Human approves the script: set `editorial_status: approved`.
5. Run `fnvideo tts`; keep the generated audio and timing cache.
6. Run `fnvideo preview`; inspect `contact.png`.
7. Run `fnvideo render`; review `final.mp4` and `qa_report.json`.
8. Make changes in YAML or template code, then rerender. Do not regenerate TTS unless narration or voice settings changed.
9. Publish manually only after editorial, voice, visual, and technical QA.

## Commands

```powershell
fnvideo doctor
fnvideo validate <spec.yaml>
fnvideo plan <spec.yaml>
fnvideo voice check-samples --profile ivc --samples private/voice_samples/*.mp3
fnvideo voice check-samples --profile pvc --samples private/voice_samples/pvc/*.mp3
fnvideo voice clone --name "My F/N Voice" --samples private/voice_samples/*.mp3 --i-own-this-voice
fnvideo voice preview --model eleven_v4 --output out/voice/voice-preview-v4.mp3
fnvideo voice preview --model eleven_multilingual_v2 --output out/voice/voice-preview-v2.mp3
fnvideo tts <spec.yaml>
fnvideo preview <spec.yaml>
fnvideo render <spec.yaml>
```

`--allow-draft` is a test-only override. It does not change the editorial status in YAML and must not be used as a publishing approval.

## Cache policy

Each scene MP3 has a local cache manifest with a SHA-256 hash of narration, adjacent context, voice ID, model, output format, and synthesis settings. `fnvideo tts` reuses a scene automatically when its hash is unchanged. A changed line or adjacent context invalidates only the affected scene(s). Use `fnvideo tts <spec> --force` to regenerate all scenes deliberately. `voice.wav`, `timing.json`, and SRT are rebuilt from the scene cache after each TTS pass. Keep `out/` private and git-ignored.

## Failure recovery

- API 429/5xx responses are retried with bounded exponential backoff.
- A failed scene render leaves no final `scene.mp4`; the temporary file is not promoted.
- Final export is written to `final.tmp.mp4` and renamed only after successful FFmpeg completion.
- If a generated MP3 exists but timing build failed, rerun `fnvideo tts`; unchanged scenes are restored from their hash-validated cache. Use `--force` only when an intentional re-generation is required.
- Do not edit files under `out/` manually; edit the YAML spec or source assets instead.
