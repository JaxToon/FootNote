# Build Status — Starter v4

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
