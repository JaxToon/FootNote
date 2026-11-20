# F/N Video Quality Bar

## Owner's release requirement

The new F/N video must be **better than the owner's prior reference video**, not merely technically valid. Every first-release candidate must pass the reference comparison gate below before it can be marked `publish_ready`.

The reference MP4 was not present in the files available during this repository build. Therefore no measured superiority claim is made yet. Place it at `references/quality_benchmark/reference.mp4` (or provide it during review) before scoring the candidate.

## Visual quality

- Short: 1080×1920; Long: 1920×1080; default 30 fps.
- Crisp, full-resolution vector diagrams and typography. No stretched screenshots or low-resolution illustrations.
- One visual idea per scene. Visuals must clarify the spoken point rather than decorate it.
- Clear hierarchy: F/N identity, section/title, diagram, phrase caption, and source/illustration note.
- Captions are phrase-sized, phone-readable, aligned to narration, and do not cover key diagrams or platform UI.
- Keep the bottom 20% of portrait content visually quiet.
- Motion must have a purpose: reveal, draw-on, highlight, transition, or reaction. No constant motion for its own sake.
- NODI appears as a companion at selected beats and never competes with the explanation.
- Avoid unlicensed stock music, icons, logos, illustrations, characters, and font files.

## Audio quality

- Use the owner's approved own-voice clone; prefer PVC fine-tuned for Eleven v4 for final production.
- Natural Indonesian pronunciation, consistent accent, clean consonants, believable pauses, and sentence endings. Preserve English technical terms where appropriate.
- No clipping, unexpected silence, abrupt edit, metallic artifacts, robotic cadence, or obvious discontinuity between scenes.
- Normalize toward -14 LUFS integrated and -1.5 dB true peak as a starting target. Listen to the complete narration after normalization.
- AAC 192 kbps, 48 kHz in final MP4. No background music until licensing and mixing rules are approved.

## Reference comparison gate

Use the same display size, playback device, and listening conditions for reference and candidate. Score both from 1–5 on these dimensions:

1. Hook clarity and first three seconds.
2. Script clarity and pacing.
3. Typography and caption legibility.
4. Visual hierarchy and composition.
5. Explanatory value of diagrams and analogies.
6. Animation timing and transitions.
7. Character identity and consistency.
8. Voice likeness and natural Indonesian delivery.
9. Audio cleanliness and mix.
10. Factual accuracy and sourcing.

**Pass criteria:**

- Candidate mean score must exceed the reference mean by at least 0.3 points.
- No candidate dimension may score below the reference.
- At least three core dimensions (hook, explanatory visuals, voice/delivery, pacing, or visual hierarchy) must improve by at least 1 point.
- Factual accuracy and sourcing may not regress.
- Any critical defect (wrong claim, unintelligible caption, obvious audio artifact, clipping, or broken visual) blocks publishing regardless of average score.

Use `references/quality_benchmark/scorecard_template.csv` to record results. If the reference MP4 is unavailable, mark the result `benchmark_pending`; do not claim the user's strict superiority requirement has passed.

## Technical QA

- H.264 / libx264, CRF 18, yuv420p, 30 fps.
- AAC, 192 kbps, 48 kHz stereo.
- `+faststart` for web playback.
- Output includes `captions.srt`, `timing.json`, contact sheet, scene renders, and `qa_report.json`.
- Check resolution, frame rate, duration, audio stream, loudness, peak, safe area, caption alignment, and phone-sized legibility.

## Human release gates

1. Editorial: facts, examples, limitations, figures, and sources reviewed.
2. Voice: listen to full narration and approve likeness, pronunciation, pacing, and scene joins.
3. Visual: inspect contact sheet and watch the complete MP4.
4. Technical: probe output and check phone-sized playback.
5. Benchmark: satisfy the strict reference comparison gate.
6. Publish: mark `publish_ready` only when every gate is approved.

A generated MP4 is only `rendered_needs_human_qa`. Passing automated checks does not certify the voice clone's likeness or a video's subjective quality.

## Current MVP limitations

- Procedural NODI vector art is an initial puppet rig, not final illustrator-delivered layered artwork.
- RMS mouth animation is amplitude-reactive, not phoneme-accurate lip sync.
- The renderer is a reusable template engine, not a full nonlinear editor.
- The Long pilot spec is an outline draft and must be expanded and editorially approved before calling it an 8–12 minute finished episode.
