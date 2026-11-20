# Episode Spec Contract v1

The YAML files in `specs/` are valid draft examples. This document describes the intended contract; Pydantic models are the executable contract and should evolve with explicit schema-version migrations.

## Top-level keys

- `schema_version`: integer; current starter version is `1`.
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

## Validation principles

- Unknown fields fail validation; schema changes must be versioned.
- IDs are stable and unique within an episode.
- Short uses portrait aspect ratio; Long uses landscape aspect ratio.
- Template props must be validated by the template registry, not accepted as arbitrary data forever.
- Estimated timing must carry provenance/confidence metadata.
- Human editorial approval must precede TTS/render in production commands.

## Future extensions

Add explicit `data`, `cues`, `assets`, `audio`, `timing`, `transitions`, and `output_profiles` fields when implementation requires them. Do not add speculative complexity without a tested use case.
