# Build Status

## Motion/visual pass — 2026-11-20

- Pilot short re-authored to 7 scenes (40.65 s) with beats; silent draft render passes
  technical QA and motion QA (mean 1.38, min 0.41; baseline was mean 0.28 with 25/33
  frozen seconds). `pytest`: 80 passed; ruff clean.
- New: beat/cue system (schema v2), secondary motion + grain, motion QA gate
  (`fnvideo motion`, run automatically after `render`), bundled OFL brand fonts, 9:16 type
  scale, original icon set, NODI as centred performer, minimal branding.
- Still draft: narration/editorial, no real voice yet, reference-video comparison pending.

## Verified locally — 2026-11-20 (Windows 11, Python 3.11.9, FFmpeg 9.0.2, Playwright Chromium)

- `pytest`: 47 passed (includes real-Chromium template/scene-isolation test).
- `ruff check .` and `ruff format --check .`: clean (E501 delegated to the formatter).
- `fnvideo doctor`: all render dependencies OK; ElevenLabs key/voice ID not configured (expected).
- Short, Long, and SQL JOIN specs validate.
- `fnvideo preview` for Short and Long: contact sheets inspected at full size.
- `fnvideo render <short> --allow-draft --silent`: 1080x1920 H.264/AAC, 969/969 frames,
  32.3 s, all technical QA checks pass. Silent placeholder audio, estimated caption timing;
  this is a motion/layout draft, not a deliverable.

Fixed in this pass: scene-to-scene `window.render` leak (captions used the previous scene's
timing), caption gaps, NODI/headline/card collisions, Short caption inside bottom 20%,
contact-sheet ordering, cumulative frame drift, mouth min-hold at track start, stale preview
timing, non-atomic FFmpeg intermediates.

Still not verified: real ElevenLabs TTS / voice likeness, loudness of real narration,
reference-video comparison, brand fonts (Space Grotesk / Inter / IBM Plex Mono are not yet
bundled, so Chromium falls back to Arial).

---

# Build Status — Starter v4 (historical)

This file records what was actually verified while assembling this greenfield starter. It is not a claim that the first episode is production-ready.

## Verified in the build environment

- Python package compiles successfully.
- `pytest`: 20 tests passed.
- CLI starts and reports version `0.1.0`.
- Short and Long `Korelasi Bukan Kausalitas` episode specs validate.
- SQL JOIN example spec validates.
- ElevenLabs v4 client test targets the official Text-to-Dialogue timestamped endpoint; multilingual v2 test targets timestamped Text-to-Speech. Tests use mocked HTTP and make no paid API calls.
- Instant Voice Clone response handling records the provider's `requires_verification` flag.
- IVC and PVC local audio sample checks use different duration profiles.

## Not verified in this environment

- Full Playwright render: the Playwright Chromium browser binary could not be downloaded in this environment due to DNS/network access. Install it locally using `playwright install chromium` (the Windows setup script does this).
- Ruff lint/format: Ruff is listed in the project's development dependencies but was not installed in this build environment.
- Real ElevenLabs voice cloning or TTS: no personal voice recordings, API key, or voice ID were supplied. No paid API request was made.
- Subjective owner voice likeness: must be reviewed by the owner using their own voice clone.
- Reference-video superiority: the original comparison MP4 was not present in the accessible files. Put it at `references/quality_benchmark/reference.mp4` before completing the benchmark.
- Full pilot delivery: the Short/Long scripts are drafts. The Long episode is an outline and is not yet an 8–12 minute finished script.

## Required local first-run checks

Run these from the repository root after setup:

```powershell
fnvideo doctor
pytest
ruff check .
ruff format --check .
fnvideo validate specs/fondasi-01-korelasi-bukan-kausalitas/short.yaml
fnvideo validate specs/fondasi-01-korelasi-bukan-kausalitas/long.yaml
fnvideo preview specs/fondasi-01-korelasi-bukan-kausalitas/short.yaml
fnvideo preview specs/fondasi-01-korelasi-bukan-kausalitas/long.yaml
```

Then create/audition the owner's clone, review the narration, approve the script, and render the Short. Do not run the Long as a finished deliverable until its script is expanded and approved.
