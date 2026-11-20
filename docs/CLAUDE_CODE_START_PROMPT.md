# Claude Code — Start Prompt

```text
We are starting a NEW GREENFIELD repository for F/N — FOOTNOTE Video Production Pipeline. This is a reusable system for all future F/N episodes, not a one-video script.

Read CLAUDE.md and all relevant docs before changing code. The repository includes a runnable local MVP implementation, not just a design scaffold. Your first task is to audit it, run its tests/lint/CLI checks, and identify implementation bugs before expanding scope.

Important owner requirements:
- The production narrator is the owner's own AI-cloned voice, not a stock voice. Prefer an owner-created Professional Voice Clone (PVC) for highest fidelity; Instant Voice Clone (IVC) is available for rapid auditioning. The implementation defaults to Eleven v4 through Text-to-Dialogue with timestamps; multilingual v2 is an A/B fallback through timestamped Text-to-Speech. Use the owner's own verified clone ID. PVC is preferred for final fidelity; IVC is an audition path. Do not call paid APIs unless .env credentials exist and the owner has asked to generate audio.
- Quality must be at least as good as, preferably better than, the pilot reference video in visual clarity, motion, typography, audio, and factual accuracy. Do not claim this comparison has been verified unless the reference MP4 is actually available in the repository.
- F/N needs a reusable pipeline for future series/episodes. The first episode “Korelasi Bukan Kausalitas” is only a pilot.
- NODI is the approved learning companion. Presenter avatar and NODI are separate optional character roles.
- Use the selected implementation: Python + inline SVG/HTML + Playwright + FFmpeg. Do not migrate to Remotion without a measured technical reason and owner approval.

Run:
1. `python -m pip install -e ".[dev]"`
2. `playwright install chromium`
3. `pytest`
4. `ruff check .`
5. `ruff format --check .`
6. `fnvideo doctor`
7. Validate both Short and Long pilot YAML specs.
8. Render preview contact sheets for both profiles and inspect them at full size.

Then fix all defects and create tests for:
- ElevenLabs timestamp parsing and retry behavior (mocked HTTP only; no paid API calls).
- caption alignment exact and estimated fallback labels.
- inter-scene audio timing and SRT generation.
- deterministic frame state and mouth-state minimum hold.
- all templates in both portrait and landscape profiles.
- FFmpeg atomic output behavior and QA metadata.

Before any paid TTS run, ensure the owner has created and verified their own voice clone and personally approved `fnvideo voice preview`. The current procedural NODI puppet is an initial vector rig and must be reviewed, not presented as a final illustrator-delivered asset.

Do not rewrite the repository from scratch. Make focused, reusable improvements. Keep all private voice samples, .env, and generated outputs out of Git. Finish with a concise audit, exact local commands, known limitations, and the next milestone.
```
