# Rendering and QA Contract

## Selected engine

Python orchestration + inline SVG/HTML scene templates + Playwright Chromium frame capture + FFmpeg encoding and assembly. This is the production implementation for the first local release. Do not migrate to Remotion unless a benchmark shows the selected engine cannot meet a concrete requirement and the owner approves the migration.

## Deterministic render rules

- Frame state is a pure function of frame time/index, episode spec, timing manifest, and versioned assets.
- Default 30 fps; output dimensions are taken from the Short/Long profile.
- No wall-clock animation, CSS animation/transition, requestAnimationFrame, or unseeded randomness.
- Render frames directly at target size; do not upscale a low-resolution composition.
- Use a temporary output and atomically rename only after successful FFmpeg exit.
- Store engine/tool versions, spec hash, template version, asset hashes, and render settings in the QA/manifest output.

## Export baseline

- Video: H.264 / libx264, CRF 18, yuv420p, 30 fps, `+faststart`.
- Audio: AAC 192 kbps, 48 kHz stereo.
- Loudness: target around -14 LUFS integrated, true peak no higher than -1.5 dBTP unless a platform-specific mix says otherwise.
- Short: 1080×1920. Long: 1920×1080.
- Sidecar outputs: `final.mp4`, `contact.png`, `captions.srt`, `timing.json`, scene MP4s, and `qa_report.json`.

## Automated QA

- Resolution, frame rate, H.264 codec, AAC stream, sample rate, and duration.
- No missing scene assets/fonts, empty scenes, or zero-duration output.
- Caption layout and scene-safe-area review.
- Audio stream exists, loudness normalization completes, no accidental truncation.
- Chart/diagram labels match spec values. Synthetic/illustrative data must carry a visible `ILUSTRASI` label.
- Source notes and editorial caveats are present in the episode spec.

## Human QA — required before publish

- Watch the entire MP4 at normal speed and on a phone-sized display.
- Listen to the full narration with headphones; verify voice likeness, Indonesian accent, technical-term pronunciation, pacing, pauses, breath/noise artifacts, and scene-to-scene continuity.
- Inspect the contact sheet and at least one key frame per scene at full resolution.
- Check NODI's silhouette, outfit, expressions, placement, and consistency. The procedural rig is a first production asset, not a replacement for an illustrator-approved layered master.
- Fact-check every factual claim and inspect all cited sources.

## Status model

Draft → Validated → Audio-reviewed → Rendered → QA-passed → Publish-ready. Rendering success alone never implies publish-ready.
