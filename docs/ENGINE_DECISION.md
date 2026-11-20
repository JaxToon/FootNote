# Rendering Engine Decision

**Decision for the first production implementation:** Python orchestration + inline SVG/HTML scene templates + Playwright Chromium frame capture + FFmpeg encoding/assembly.

## Why this choice

- The source brief already describes a working browser-render prototype and a deterministic `render(t)` approach.
- It minimizes the number of new tools required to reach the first render.
- SVG is appropriate for crisp diagrams, captions, charts, and the first NODI puppet.
- Playwright provides deterministic frame capture under a fixed viewport.
- FFmpeg provides explicit encoding, scene concat, audio normalization, and export controls.
- Python keeps YAML validation, CLI, audio orchestration, timing, and QA in one local-first toolchain.

## Why not Remotion in M1

Remotion is a reasonable future alternative, but migrating the whole project to React/TypeScript before a generic renderer exists adds a second application toolchain and a migration cost. Re-evaluate only when there is evidence that the current engine cannot meet the animation, preview, or production needs.

## Determinism contract

- Frame rendering is driven by explicit frame index/time.
- No wall-clock timestamps, CSS animations, transitions, `requestAnimationFrame`, or unseeded random values.
- Any motion uses deterministic functions of `t`.
- Timing/audio manifests are immutable inputs to a render.
- Same code, spec, timing, assets, and tool versions should produce the same scene state. ElevenLabs synthesis itself is not guaranteed bit-deterministic; cache the generated audio and timing rather than regenerating it during rerenders.

## Renderer interface

The scene data model and template props must not depend on Playwright internals. A future renderer can consume the same normalized scene and timeline contracts.
