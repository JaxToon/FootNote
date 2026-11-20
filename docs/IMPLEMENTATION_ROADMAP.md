# Implementation Roadmap

## M1 — Local production MVP (current code baseline)

- [x] Greenfield repo and strict YAML schema.
- [x] CLI foundation and environment doctor.
- [x] ElevenLabs personal voice clone creation path (IVC), PVC account workflow, and model-correct timestamped adapters (v4 Text-to-Dialogue; multilingual v2 Text-to-Speech).
- [x] Per-scene voice cache, timing manifest, approximate NODI mouth envelope, SRT.
- [x] SVG template renderer with Playwright/FFmpeg output path.
- [x] Contact sheet, loudness normalization, H.264/AAC mux, technical QA JSON.
- [ ] Run all checks on the owner's Windows laptop.
- [ ] Review generated contact sheets and fix visual collisions.
- [ ] Create and audition owner's voice clone.
- [ ] Render and watch first Short end-to-end.

## M2 — Quality hardening

- [x] Resumable per-scene TTS cache with hash-based invalidation and explicit force-regeneration.
- [ ] True line/word timing verification and caption collision tests.
- [ ] More varied deterministic motion: draw-on charts, node/arrow sequencing, emphasis transitions.
- [ ] Phone-size legibility review, subtitle contrast and safe-area checks.
- [ ] Measure against actual reference MP4 when owner supplies it.

## M3 — NODI production rig

- [ ] Replace/upgrade procedural mascot with approved, layered vector artwork.
- [ ] Rig face, eyes, brows, mouth, arms, and poses as separate SVG layers.
- [ ] Outfit variants must not change anatomy/silhouette.
- [ ] Owner approval of master character, expression sheet, and motion tests.

## M4 — Editorial and content system

- [ ] Source-aware script brief and reference capture.
- [ ] Add more generic templates: code, table, formulas, flow, comparison, bars, distribution, roadmap.
- [ ] Expand Long scripts to the 8–12 minute requirement.
- [ ] Add metadata and thumbnail generator.

## M5 — Publishing and scale

- [ ] Optional YouTube private upload.
- [ ] Optional cloud render/storage only after local workflow is reliable.
- [ ] Production analytics and sustainable batch workflow.
