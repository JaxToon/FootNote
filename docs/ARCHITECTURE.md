# Architecture — F/N Video Pipeline

## Runtime flow

```text
YAML episode spec
  ├─ Pydantic validation
  ├─ human editorial approval gate
  └─ per-scene narration
       └─ ElevenLabs timestamped narration using owner's voice clone (v4 Text-to-Dialogue; multilingual v2 TTS fallback)
            ├─ scene MP3 cache
            ├─ merged voice.wav with inter-scene gaps
            ├─ timing.json (scene, captions, RMS, mouth shapes)
            └─ captions.srt
                 └─ SVG template renderer (Playwright, fixed viewport, explicit t)
                      ├─ scene MP4s (H.264)
                      ├─ contact sheet
                      └─ FFmpeg concat + loudness normalization + AAC mux
                           └─ final.mp4 + qa_report.json
```

## Package layout

```text
src/fnvideo/
  audio/
    elevenlabs.py     # authorized personal voice clone + timestamped TTS HTTP client
    pipeline.py       # per-scene synthesis, gap assembly, timing manifest
    timing.py         # caption alignment, RMS envelope, mouth states, SRT
  models/episode.py   # strict Pydantic spec contract
  render/
    svg_scene.py      # reusable, canvas-aware SVG scene templates and NODI puppet
    engine.py         # Playwright frame stepping, FFmpeg encode/concat/mux, QA artifacts
  services/
    doctor.py
    spec_loader.py
  config.py
  cli.py
```

## Important boundaries

- Episode content, scene data, and template props live in YAML.
- Renderer code contains generic reusable template logic, never pilot-specific narration.
- Audio is generated once and cached; visual-only rerenders reuse the same audio and timing.
- Provider alignment is kept out of the final public timing file after it is converted into captions/word windows.
- No API call occurs during `doctor`, `validate`, `plan`, or `preview`.
- Clone creation and TTS generation are explicit paid/credentialed commands.
- NODI is a separate role from the optional presenter avatar.

## Timeline model

Each scene has a local duration, global start/end, caption intervals, and cached source audio. Scene intervals include an inter-scene silence tail. The final voice WAV and concatenated visual sequence use the same scene durations. Each visual frame receives a fixed local `t` and mouth state based on the global audio envelope.

## Error recovery

- API calls retry bounded 429/5xx and transport failures.
- Per-scene MP3 files remain as intermediate assets.
- Scene renders go to `*.tmp.mp4` and are promoted only on success.
- Final render goes to `final.tmp.mp4` and is renamed on success.
- `qa_report.json` status remains `rendered_needs_human_qa` until a human review is completed.
