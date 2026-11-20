# Episode Spec Contract v2

The YAML files in `specs/` are valid draft examples. This document describes the intended contract; Pydantic models are the executable contract and should evolve with explicit schema-version migrations.

## Top-level keys

- `schema_version`: integer; current version is `2`. v1 files are migrated on load (`services/spec_loader.migrate_spec`); v2 only adds the optional scene keys `beats` and `holds`.
- `meta`: stable identity, title, series, episode, format, language, fps, dimensions, paired deliverable, status.
- `voice`: provider (`elevenlabs`, `recorded`, `none`), optional voice ID, speed. Production defaults to the owner's ElevenLabs clone; never put secrets here. With the default `eleven_v4` model, keep `speed: 1.0` because the v4 model path does not use the legacy speed control.
- `editorial_status`: `draft`, `needs_review`, or `approved`.
- `sources`: source references; richer source objects can be added through a schema migration.
- `scenes`: ordered scene list.

## Scene keys

- `id`, `title`, `purpose`, `narration`.
- `captions`: phrase chunks and optional highlight tokens.
- `character`: presenter and mascot visibility are independent; optional poses, NODI outfit and expression.
- `background`: token name or approved color.
- `template`: registered template ID.
- `props`: template-specific object validated by that template's schema.
- `duration_hint_seconds`: optional editorial hint, not authoritative when audio timing exists.
- `source_notes`: factual caveats, illustration notes, or claim references.
- `beats` (v2, optional): cues that animate one element at a moment in the narration.
  - `at`: `caption:<index>` (that caption's start), `word:<word>` (first whole-word
    occurrence; provider word timestamps when available, otherwise estimated), or a number
    `0..1` (fraction of the scene duration).
  - `target`: an element `data-id` of the scene template (e.g. `headline`, `rule`,
    `chart-0`, `node-1`, `arrow-2`, `item-0`, `link-0`, `point-1`, `label`) or `nodi`.
    An unknown target fails the build and lists the template's element IDs.
  - `action`: `pop` | `slide` | `draw` | `count` | `highlight` | `exit`; for `nodi`,
    `pose:<pose>` or `expr:<expression>`.
  - `duration`: optional seconds (defaults: pop .35, slide .45, draw .8, count .9,
    highlight .5, exit .3). Elements without an enter beat stagger in by 0.15 s.
- `holds` (v2, optional): intentional visual holds `{start, end, reason}` (fractions of the
  scene) that the motion QA excuses.

Template props added for icons: `causal_diagram.nodes[].icon`, `question_link.labels[]`
as `{label, icon}`, `paired_trend.icons` and optional `paired_trend.x_labels`. Icon names
are the files in `src/fnvideo/render/assets/icons/`.

Clarity lint (`fnvideo check-clarity <spec>`, also run by `validate`): (a) captions are
verbatim narration (case/punctuation ignored), (b) the first scene shows something concrete
(`side_icons`, icons or a chart), (c) NODI-only scenes (title_question without `side_icons`)
last ≤ 2 s except the close, (d) explanation scenes have a `word:` beat. Warnings for drafts;
errors that block `validate`, `tts` and `render` once `editorial_status: approved`.

Beat-order warnings (also from `check-clarity` and `validate`; they never block): a dependent
element must not be cued before or at the same time as what it depends on: `false-x` after
`false-link`, `arrow-1/2` after `node-0`, `arrow-zx/zy` after `z` (and `x`/`y`), `xy` after
`x` and `y`, `link-k` after `item-k`, `trend` after `chart`, and a chart's `conclusion`/`r` after
its lines. A `word:` cue on the narration's first word resolves to t=0. A `card` must not
stand empty for more than 1 s before its `term`/`definition`. Timing is estimated from the
duration hints; re-check once real narration timing exists.

Authoring lint (`fnvideo validate`): portrait captions ≤ 5 words and one line; NODI off in
explanation templates; avoid navy backgrounds behind NODI.

## Validation principles

- Unknown fields fail validation; schema changes must be versioned.
- IDs are stable and unique within an episode.
- Short uses portrait aspect ratio; Long uses landscape aspect ratio.
- Template props must be validated by the template registry, not accepted as arbitrary data forever.
- Estimated timing must carry provenance/confidence metadata.
- Human editorial approval must precede TTS/render in production commands.

## Future extensions

Add explicit `data`, `assets`, `audio`, `timing`, `transitions`, and `output_profiles` fields when implementation requires them. Do not add speculative complexity without a tested use case.
