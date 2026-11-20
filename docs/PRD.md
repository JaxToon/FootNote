# PRD — F/N FOOTNOTE Video Production Pipeline

**Status:** Runnable local MVP starter with implemented audio/render pipeline; visual and audio QA still required.  
**Owner:** F/N — FOOTNOTE  
**Primary implementation agent:** Claude Code

## 1. Product vision

Build a repeatable, local-first production system that turns a reviewed episode spec into educational videos across F/N's editorial series. A topic may have a Short and a Long video, each with its own script and pacing. The pipeline is not designed around a single pilot; templates and specs must generalize.

## 2. Audience and editorial scope

Students, university learners, fresh graduates, early-career professionals, and career switchers learning data, science, and technology. The default language is natural Bahasa Indonesia with familiar English technical terms.

Supported editorial identities include EXPLAINED, PATHWAYS, DEEP DIVE, PAPER TRAIL, BUILT, CAREER NOTES, Fondasi, and future series. Series must remain data-driven metadata.

## 3. Output profiles

| Format | Platform | Canvas | FPS | Target duration |
|---|---|---:|---:|---:|
| Short | Shorts, TikTok, Reels | 1080×1920 | 30 | 30–60 sec |
| Long | YouTube | 1920×1080 | 30 | 8–12 min |

Profiles must be configurable. Separate short/long specs allow pacing and scene structures to differ while sharing topic identity.

## 4. Production pipeline

1. Topic brief and primary source collection.
2. Outline and script drafts.
3. Episode specs (YAML) for each format.
4. Human editorial approval.
5. Owner's voice clone TTS through ElevenLabs with character timestamps.
6. Build scene/caption/audio timing and approximate mouth-motion envelope.
7. Deterministic frame render using reusable SVG scene templates and Playwright.
8. FFmpeg scene encoding, concat, loudness normalization, audio mux, MP4 export.
9. Contact sheet, subtitles, and technical QA report.
10. Human playback, factual review, and manual publishing.

## 5. Voice: owner's own cloned voice

- Production narration must use an AI clone of the owner's own voice. Stock or third-party voices are not production defaults.
- ElevenLabs is the initial provider. IVC is supported by the CLI for fast auditions; PVC can be created through the provider dashboard and consumed by setting the voice ID in `.env`. PVC is preferred for final narration when eligible and when the owner can provide sufficient clean training material. IVC is for rapid auditioning. The owner must complete the provider's own-voice verification flow where required.
- Route `eleven_v4` through Text-to-Dialogue with timestamps (`/v1/text-to-dialogue/with-timestamps`); route `eleven_multilingual_v2` through timestamped Text-to-Speech (`/v1/text-to-speech/{voice_id}/with-timestamps`). Generate one cached request per scene and pass adjacent narration as continuity context.
- Do not substitute stock voices as the production default.
- Do not commit samples, voice IDs if treated as confidential, API keys, `.env`, or generated private speech assets.
- Voice clone quality requires a human listening test before generating the entire episode.

## 6. Brand and visual identity

Primary F/N palette: Ink Navy `#111D38`, Footnote Yellow `#F3D65B`, Paper `#F4F1E8`, Signal Coral `#E56B50`, Deep Blue `#243D57`, Teal `#245F59`, Purple `#5142A0`.

Typography direction: Space Grotesk for display, Inter for body/captions, IBM Plex Mono for technical labels. Fonts are expected from local installation; do not redistribute font binaries unless their licenses and bundling permissions have been confirmed.

NODI is the approved learning companion: balanced proportions, expressive hybrid face, editorial × graphic cartoon style, modular outfit, navy head/hood, cream face, dark eyes, signature yellow folded corner. `assets/mascot/nodi-concept-board.png` is reference art only. The generated SVG puppet is a first production approximation and must be reviewed.

Presenter avatar and NODI remain separate optional character roles.

## 7. Implemented scene templates

`title_question`, `chapter_title`, `definition_card`, `paired_trend`, `line_chart`, `scatter_regression`, `causal_diagram`, `question_link`, `takeaway`, `follow_cta`.

Each template supports portrait and landscape layout through canvas-aware geometry. New templates must be generic and prop-driven.

## 8. Audio and timing

- ElevenLabs `eleven_v4` is the default quality-first candidate and uses Text-to-Dialogue with timestamps. `eleven_multilingual_v2` remains a configurable fallback and uses timestamped Text-to-Speech. Both must be auditioned with the owner's exact clone and Indonesian script before full episode generation.
- Character-level alignment is used to time captions when the phrase matches the narration; estimated fallback timing must be explicitly labeled.
- Caption timing falls back to proportional estimate when exact phrase alignment is unavailable; this is labeled `estimated` in timing.json.
- Combined WAV with configured inter-scene gaps; RMS envelope at 30 fps maps to five approximate mouth states with a 2-frame minimum hold.
- Mouth mapping is not phoneme-accurate lip-sync. Do not label it as such.
- Final audio target around -14 LUFS integrated and -1.5 dB true peak; verify by listening.
- Music is disabled by default until licensed source and ducking requirements are selected.

## 9. Rendering and export

Initial engine: Python orchestration + HTML/SVG + Playwright Chromium + FFmpeg. Frame state must be deterministic from explicit time, spec, timing, and assets. No wall-clock animation, CSS keyframes/transitions, requestAnimationFrame, or unseeded randomness.

- Short: 1080×1920; Long: 1920×1080; default 30fps.
- Scene MP4: H.264, CRF 18, yuv420p; concat through FFmpeg.
- Final audio: AAC 192 kbps, 48 kHz; video stream copied where possible.
- Atomic temp output and rename after successful FFmpeg exit.
- Contact sheet, SRT, timing manifest, and QA JSON accompany the final MP4.
- Portrait captions and key visuals must respect platform safe areas.

## 10. CLI contract

```text
fnvideo doctor
fnvideo validate <spec.yaml>
fnvideo plan <spec.yaml>
fnvideo voice clone --name <name> --samples <files...> --i-own-this-voice
fnvideo voice preview [--text <text>] [--output <path>]
fnvideo tts <spec.yaml> [--allow-draft]
fnvideo preview <spec.yaml>
fnvideo render <spec.yaml> [--allow-draft]
fnvideo build <spec.yaml> [--allow-draft]
```

`--allow-draft` is only a test bypass; it does not promote the episode to approved or publish-ready.

## 11. Quality requirements

- Full HD output at profile dimensions and 30 fps.
- Crisp vector elements and readable phrase captions.
- Voice likeness, Indonesian pronunciation, pacing, and transitions approved by owner.
- No clipping or missing audio; loudness checked.
- All claims and displayed data traceable.
- Full MP4 playback and contact sheet reviewed before publication.
- The target is to exceed the supplied pilot reference in visual clarity, motion design, narration quality, and editorial accuracy. The exact reference video must be present for a measured side-by-side comparison; do not claim a verified improvement without it.

## 12. Definition of done

- `draft`: editable YAML exists and validates.
- `audio_ready`: voice.wav and timing.json exist; narration has been auditioned.
- `rendered_needs_human_qa`: final.mp4 and QA artifacts exist.
- `qa_passed`: owner has reviewed the full video and approved factual, visual, and audio quality.
- `publish_ready`: metadata, rights, platform disclosures, and all review gates are complete.

A successful FFmpeg render alone never means publish-ready.
