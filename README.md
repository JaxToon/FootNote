# F/N — FOOTNOTE Video Production Pipeline

Local-first, reusable video production system for educational episodes. Built for **many future videos**, not a one-off pilot. The first episode is `Fondasi 01 — Korelasi Bukan Kausalitas`; the pipeline is episode-spec driven.

## What is implemented

- Pydantic-validated YAML episode specs (Short and Long profiles).
- Authorized personal voice cloning: Instant Voice Clone (IVC) for auditioning; Professional Voice Clone (PVC) is preferred for final narration and is configured in the owner’s ElevenLabs account.
- ElevenLabs timestamped narration per scene: Eleven v4 via Text-to-Dialogue; Multilingual v2 via timestamped Text-to-Speech.
- Character-alignment-driven caption timing, plus explicitly marked estimated fallback.
- RMS-driven NODI mouth-shape track (approximate amplitude lip-sync, not phoneme-perfect lip-sync).
- Deterministic SVG scene templates rendered by Playwright/Chromium.
- FFmpeg scene encoding, concat, audio normalization, AAC mux, SRT, contact sheet, and QA report.
- Preview can be generated before voice credentials are configured.

Build verification and known limitations are recorded in `docs/BUILD_STATUS.md`.

## 1. Prerequisites (Windows)

- Python 3.11 or 3.12 recommended.
- FFmpeg + FFprobe installed and available on PATH.
- Node is not required.
- ElevenLabs account and API key. Create a clone of **your own voice**; see `docs/VOICE_CLONING.md`.

## 2. Install

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
playwright install chromium
Copy-Item .env.example .env
```

Add `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID` to `.env`. Never commit `.env` or voice samples.

## 3. First-run checks

```powershell
fnvideo doctor
fnvideo validate specs/fondasi-01-korelasi-bukan-kausalitas/short.yaml
fnvideo preview specs/fondasi-01-korelasi-bukan-kausalitas/short.yaml
```

`preview` produces `out/<episode-family>/short/contact.png` without requiring a voice clone.

## 4. Create your own voice clone

Record clean samples and put them under `private/voice_samples/`. Then run:  

```powershell
fnvideo voice clone --name "Firgy - F/N Narration" --samples private/voice_samples/*.mp3 --i-own-this-voice
```

Copy the printed IVC voice ID into `.env` for a first audition. For final videos, create and verify a Professional Voice Clone (PVC) of your own voice in your ElevenLabs account, fine-tune it for Eleven v4 when available, then replace `ELEVENLABS_VOICE_ID` with that PVC ID. Preflight a long-form recording set with `fnvideo voice check-samples --profile pvc --samples private/voice_samples/pvc/*.mp3`. The `voice clone` CLI command creates IVC only; PVC creation/identity verification remains in the provider account. See `docs/VOICE_CLONING.md`.

Generate a short voice check before the whole episode:

```powershell
fnvideo voice preview --output out/voice/voice-preview.mp3
```

Listen critically to accent, pronunciation, pacing, and emotional range. Tune `ELEVENLABS_STABILITY`, `ELEVENLABS_SIMILARITY`, and (for a v4 PVC) `ELEVENLABS_CLONE_STRENGTH` in `.env`. The default clone strength is 0 as recommended by the provider; audition alternatives only if the clone is not retaining your voice traits.

## 5. Produce the first Short

1. Review/fact-check the YAML, narration, on-screen claims, and sources.
2. Set `editorial_status: approved` in the spec only after review.
3. Generate voice and timing: `fnvideo tts <spec>`.
4. Review stills: `fnvideo preview <spec>`.
5. Render: `fnvideo render <spec>`.

For a test before editorial approval, `--allow-draft` is available but must not be used for publishing.

```powershell
fnvideo tts specs/fondasi-01-korelasi-bukan-kausalitas/short.yaml
fnvideo preview specs/fondasi-01-korelasi-bukan-kausalitas/short.yaml
fnvideo render specs/fondasi-01-korelasi-bukan-kausalitas/short.yaml
```

Outputs: `out/fondasi-01-korelasi-bukan-kausalitas/short/` including `final.mp4`, `contact.png`, `captions.srt`, `timing.json`, scene MP4s, and `qa_report.json`.

## 6. New episodes

Copy an existing spec, update its `meta.id`, script, source notes, captions, template, and props. Do not write new renderer code unless creating a reusable template not already in the registry. Use `docs/EPISODE_SPEC_CONTRACT.md` and `docs/EDITORIAL_SYSTEM.md`.

## 7. Quality and limitations

The renderer targets 1080×1920 or 1920×1080 at 30 fps, H.264 CRF 18, AAC 192 kbps, and approximately -14 LUFS with a -1.5 dB true-peak target. These are technical baselines, not a guarantee of subjective quality. Every episode still requires contact-sheet review, full playback, audio review, and factual review.

NODI's included vector puppet is an initial procedural rig derived from the approved concept direction. It is not a final illustrator-delivered layered asset. Review and refine it before brand-wide rollout. RMS lip-sync is amplitude-driven and does not identify phonemes.

See `docs/QUALITY_BAR.md` before calling any output publish-ready. The actual previous reference MP4 is not part of this starter; place it in `references/quality_benchmark/reference.mp4` to run the required side-by-side superiority benchmark.
