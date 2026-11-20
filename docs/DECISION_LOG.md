# Decision Log

Status: **Confirmed** = owner-approved; **Working default** = recommended implementation choice; **Open** = needs owner input before the affected feature is finalized.

## Confirmed

### D-001 — Brand
F/N — FOOTNOTE. Tagline: **Beyond the obvious.** Independent educational publication about data, science, and technology.

### D-002 — NODI mascot direction
NODI is the F/N learning companion. Balanced proportions; hybrid expressions; editorial × graphic cartoon; modular outfits. Navy folded-paper-inspired hood/head, cream face, dark eyes, signature yellow folded corner. Approved as a design direction / final candidate, not yet an illustrator-delivered production vector rig.

### D-003 — Reusable multi-episode pipeline
This is a greenfield repository for all future F/N videos and series. The correlation episode is the first pilot only.

### D-004 — Audience and language
Students, university learners, fresh graduates, early-career professionals, and career switchers. Default narration: natural Bahasa Indonesia with common English technical terms.

### D-005 — Owner voice clone
Production narration must use an AI clone of the owner's own voice. ElevenLabs is the initial provider. PVC is the preferred high-fidelity path when eligible; IVC is supported for fast auditioning. Stock narration is not the production default.

### D-006 — Rendering engine
Python + HTML/SVG + Playwright Chromium + FFmpeg is the selected initial engine. Do not migrate without evidence and owner approval.

## Working defaults

### D-007 — Local-first stack
Python 3.11+, Pydantic v2, YAML, pytest, Ruff. Windows support required. Cloud, automated social publishing, and GUI editor are deferred.

### D-008 — Episode formats
Short: 1080×1920, 30fps, target 30–60s. Long: 1920×1080, 30fps, target 8–12min. Durations are creative targets, not hard schema limits.

### D-009 — Voice synthesis model
Default `eleven_v4` for high-quality narration. A/B test against `eleven_multilingual_v2` using the same text and cloned voice if pronunciation, character alignment, cost, plan compatibility, or consistency is better with the fallback. Do not assume one preset sounds best for every voice.

### D-010 — Audio mix
Start with -14 LUFS integrated and -1.5 dBTP as an initial delivery target; no background music until licensed sources and ducking policy are selected.

### D-011 — Visual system
Use F/N brand colors and Space Grotesk / Inter / IBM Plex Mono direction, but preserve the ability to use scene-specific backgrounds and hierarchy. Fonts are loaded locally; do not redistribute font binaries without checking their licenses.

## Open — owner review required when the feature becomes relevant

### D-012 — Pilot character arrangement
NODI and the original presenter avatar are separate roles. The current pilot uses NODI as the optional companion and leaves the presenter off. Owner can revise the scene spec before production approval.

### D-013 — NODI production artwork
Current concept board is reference artwork only. Before large-scale animation rollout, create or approve a clean layered SVG master and rig map.

### D-014 — Music/SFX library
Choose original or licensed music/SFX and record source/license. Keep disabled until chosen.

### D-015 — Series after Fondasi
Choose Data Analyst or Data Scientist roadmap later; the pipeline remains series-agnostic.

### D-016 — Reference quality benchmark
The actual prior reference MP4 must be placed in `references/quality_benchmark/` or supplied to the owner/agent before any claim of verified visual/audio superiority. Until then, the project uses `docs/QUALITY_BAR.md` as its target and reports only measured technical QA.

### D-011a — Brand fonts bundled (2026-11-20, working default)
Space Grotesk (display), Inter (body/captions), IBM Plex Mono (labels): unmodified OFL files in
`src/fnvideo/render/assets/fonts/`, embedded as data URIs in scene pages (`file://` URLs are
blocked for `set_content` pages). Not subset/renamed because IBM Plex has the Reserved Font
Name "Plex". Symbols the display font renders poorly (currently `≠`) are drawn as SVG.

## Change procedure

Add dated entries or supersede a decision with rationale. Never erase history. A recommendation is not approval.
