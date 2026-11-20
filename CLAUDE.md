# CLAUDE.md — F/N FOOTNOTE Video Production Pipeline

You are implementing a reusable, local-first production pipeline for F/N — FOOTNOTE. This is a greenfield code repository. It must support many future episodes and series; the first episode is only a pilot.

## Product identity

- Brand: **F/N — FOOTNOTE**
- Tagline: **Beyond the obvious.**
- Audience: students, university learners, fresh graduates, early-career professionals, and career switchers learning data, science, and technology.
- Language default: natural Bahasa Indonesia with familiar English technical terms.
- Editorial series are metadata, not hard-coded logic: EXPLAINED, PATHWAYS, DEEP DIVE, PAPER TRAIL, BUILT, CAREER NOTES, and future series.
- NODI is the approved F/N learning companion. NODI is not a teacher and should not dominate the explanation.

## Main product requirement

Build once, produce many episodes. New episodes should be authored through YAML specs and reusable templates, not new renderer code. Support short 9:16 and long 16:9 profiles with independently paced scripts.

## Canonical starting point

Read `README.md`, `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/EPISODE_SPEC_CONTRACT.md`, `docs/EDITORIAL_SYSTEM.md`, `docs/VOICE_CLONING.md`, `docs/QUALITY_BAR.md`, `docs/ENGINE_DECISION.md`, and `docs/PIPELINE_OPERATIONS.md` before making changes.

The original owner handoff docs are preserved under `references/original_briefs/`. `docs/BUILD_STATUS.md` records what is and is not verified in the starter build environment; do not overstate it.

## Current implementation

Python package: `src/fnvideo/`

- Pydantic episode models and YAML loader.
- CLI: `doctor`, `validate`, `plan`, `voice check-samples`, `voice clone` (IVC), `voice check-samples --profile ivc|pvc`, `voice preview` (model A/B), `tts`, `preview`, `render`, `build`.
- ElevenLabs client: authorized IVC creation from owner-provided samples and timestamped narration using the owner-configured voice ID. `eleven_v4` MUST route through Text-to-Dialogue with timestamps (one voice input per scene); `eleven_multilingual_v2` uses timestamped Text-to-Speech. PVC is preferred for final voice likeness; IVC is an audition path.
- Audio pipeline: per-scene TTS, inter-scene gaps, voice.wav, provider-aligned captions (estimated fallback is marked), RMS envelope, approximate NODI mouth shapes, SRT.
- Renderer: reusable SVG scene templates via Playwright/Chromium, deterministic frame stepping, JPEG frame pipe to FFmpeg, H.264 scene MP4s, concat, loudness normalization, AAC mux, contact sheet, QA JSON.

Run `pytest`, `ruff check .`, `ruff format --check .`, `fnvideo doctor`, and validate both pilot specs before changing the implementation.

## Voice policy — important

Production narration must use the owner's own authorized voice clone. Do not substitute a stock/third-party voice. Prefer a Professional Voice Clone (PVC), fine-tuned for Eleven v4, for final voice likeness; Instant Voice Clone (IVC) can be created with `fnvideo voice clone` for fast auditions only. PVC is created and identity-verified in the owner's provider account; put its voice ID in `.env`. Default v4 adapter uses `/v1/text-to-dialogue/with-timestamps`, not the standard TTS route. Never commit voice samples, API keys, `.env`, or generated private audio. Keep `private/voice_samples/` and `out/` git-ignored.

ElevenLabs is nondeterministic. Never regenerate speech during a visual-only rerender. Use cached per-scene MP3s, `voice.wav`, and `timing.json` until narration or voice settings change.

## Rendering engine decision

The initial engine is Python + HTML/SVG + Playwright Chromium + FFmpeg. Do not migrate to Remotion unless the owner explicitly requests or a tested limitation justifies it. The engine renders at output resolution, 30 fps by default, via deterministic `render(t, mouth)` state. No wall-clock animation, CSS keyframes/transitions, `requestAnimationFrame`, or unseeded random.

## Design rules

- F/N brand palette: Ink Navy `#111D38`, Footnote Yellow `#F3D65B`, Paper `#F4F1E8`, Signal Coral `#E56B50`, Deep Blue `#243D57`, Teal `#245F59`, Purple `#5142A0`.
- NODI: balanced proportions, hybrid expressions (subtle by default, expressive at story beats), editorial × graphic cartoon, modular outfits. Navy hood silhouette, cream face, dark eyes, signature yellow folded corner.
- The included NODI concept board is reference art, not a production-ready layered rig. The current SVG puppet is an initial procedural rig and must remain easy to replace with illustrator-delivered SVG layers. The user requires the new video to outperform a prior reference; do not claim this until the actual MP4 is present and the `docs/QUALITY_BAR.md` scorecard passes.
- Presenter avatar and NODI are independent roles. Do not conflate them. The pilot currently shows NODI selectively and keeps the presenter off.
- Captions must remain above the bottom 20% UI safe region in portrait videos.
- Do not add unlicensed music, stock art, logos, icons, or fonts. Music stays off by default.

## Editorial and safety gates

- AI-generated content is draft only. Human fact-check and script approval are mandatory before TTS/render for publication.
- Every displayed statistic must be computed from shown data or sourced. Label synthetic data as illustration.
- Never fabricate research references or claim a correlation establishes causality.
- `--allow-draft` is for local testing only; it is not an approval.
- Output statuses are distinct: draft, rendered_needs_human_qa, QA-passed, publish-ready.

## Code conventions

- Python 3.11+; type hints; Pydantic v2; ruff + pytest.
- Small, testable modules. No secrets in code or committed files.
- Use atomic temp-file then rename for final outputs.
- Preserve the episode-spec contract unless a versioned migration is added.
- Before changing visual tokens or NODI anatomy, explain the reason and show a preview/contact sheet to the owner.

## First tasks for Claude Code

1. Audit current code and compare it to `docs/PRD.md` and this instruction file.
2. Run tests and lint; report missing prerequisites honestly.
3. Fix defects before adding features.
4. Render pilot contact sheets and inspect text collisions, safe areas, and visual hierarchy.
5. Implement improvements as reusable template/engine changes, not pilot-only hacks.
6. Test both Short and Long profiles. The Long pilot script is currently an outline and must be expanded before claiming an 8–12 minute deliverable.
7. Do not call paid APIs unless the owner has supplied `.env` credentials and explicitly starts an audio generation step.
