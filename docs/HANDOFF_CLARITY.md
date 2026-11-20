# Handoff → Claude Code: clarity pass on the korelasi pilot

**From:** Claude (claude.ai session with the owner, 2026-11-20)
**Branch:** `clarity/korelasi-pilot`
**Read first:** CLAUDE.md → "Clarity rules (storytelling)". This file explains why they exist and what is left for you.

## 1. Why this exists

The owner compared the latest pipeline render (commit `c0c513b`) with an earlier prototype and found the new one **harder to understand**, even though it was technically better (motion, fonts, icons, NODI rig). A review of the frames and `short.yaml` found that the problem is storytelling, not rendering:

| Problem in `c0c513b` | Effect on the viewer |
|---|---|
| Hook was abstract ("Dua hal sering terjadi bersamaan…") + conclusion title "KORELASI ≠ KAUSALITAS"; first ~10 s had no concrete example | Nothing to picture; the punchline was spoiled before the puzzle |
| Example was ice cream ↔ **sunburn** | Everyone already knows the sun causes sunburn → the "third factor" reveal is not a reveal |
| "Apakah es krim membuat kulit terbakar? **Tentu tidak.**" in one breath | No tension |
| The assumed link was never crossed out; the causal diagram's two arrows looked like one arc | The viewer must rebuild the before/after logic in their head |
| Captions summarised the narration ("Kulit terbakar matahari") instead of transcribing it | Reading ≠ hearing → double processing |
| Definitions were generic ("dua hal bergerak bersama") | The concept never connects back to the example |
| Content labels 25–30 px, grey text, chart without a conclusion | Unreadable on a phone; "so what?" missing |

## 2. What this branch already changes

**Spec:** `specs/fondasi-01-korelasi-bukan-kausalitas/short.yaml` rewritten (7 scenes, about 35 s):
1. `hook`: "FAKTA ANEH", NODI + ice cream / drowning icons with up arrows (`side_icons`)
2. `example`: paired trend with real series, a "Naik bareng!" conclusion and a computed `r`
3. `question`: NODI shrug, "ES KRIM → TENGGELAM?" (question only, no answer)
4. `hidden-factor`: assumed link drawn, crossed out on "Bukan", sun appears on "cuaca panas", one arrow per cause on "beli" / "berenang"
5. `name-it`: definition card "CONFOUNDER", tied to the example ("Di sini: cuaca panas")
6. `difference`: compare template, both definitions use the episode example
7. `close`: "CARI FAKTOR KETIGANYA", NODI explaining → cheer

**Code (reusable, not pilot hacks):**
- `title_question` → new prop `side_icons: [{icon, label?, trend: up?}]`, elements `side-0` and `side-1`. In 9:16 with NODI they flank NODI's head, and NODI steps down to scale 0.95 (`compute_layout(..., nodi_scale)`). Without NODI or in 16:9 they form a row under the headline.
- `causal_diagram` → new prop `false_link: true`, elements `false-link` (draw) and `false-x` (pop). The two arrows are now straight and leave from separate points.
- `paired_trend` → new props `conclusion` (pill, element `conclusion`) and `show_r` (Pearson r computed from `series` by `pearson_r()`, element `r`).
- New icon `assets/icons/swimmer.svg` (drowning / swimming).
- `audio/timing.py`: `word:` cues tolerate copied punctuation (`word:Bukan.` == `word:Bukan`).
- Tests: `tests/test_clarity_templates.py` (6 tests). `test_fonts.py` ≠ test no longer depends on spec copy. 88/88 passing, ruff clean.
- Docs: CLAUDE.md clarity rules, DECISION_LOG D-018 (proposed).

`fnvideo validate` passes with no warnings. `fnvideo preview` was checked visually. No audio was generated and nothing paid was called.

## 2b. Art direction pass (second commit)

The owner still found the paper render weaker than the prototype. A side-by-side comparison showed what was missing: no headline on explanation scenes, washed-out paper backgrounds, borderless captions, and empty space. The second commit adds:
- `CAPTION_BOX` (default on): captions in a dark rounded box, white text, highlighted words in Footnote Yellow. The box is sized from the text bbox in `render()`.
- A generic `headline` (+ `headline_accent: [words]`) for explanation templates (`TEMPLATE_HEADLINE_OK`), and accent words in `title_question` headlines.
- `definition_card.diagram` with Z → X, Z → Y nodes plus a dashed "korelasi palsu" link, labelled with the episode example.
- `paired_trend`: the conclusion and r pills now sit right-aligned beside the legend, so they never cover a line.
- Spec: dark saturated backgrounds per scene, headlines, 12-month seasonal data ("naik turun bareng" is more convincing than two lines that only rise).
- Verified with a full `--silent --allow-draft` render on top of `cb2de06`: motion QA passes (mean 1.77, min 0.37), `check-clarity` passes, and all 124 tests pass. `definition_card` now supports both `icon` (from `cb2de06`) and `diagram`; the pilot uses `diagram`.

## 2c. Small-detail pass (third commit)

The owner flagged the arrows at 0:19–0:22. A frame-by-frame audit (one frame per second, plus 0.6 s steps through the diagram) found these problems:
- The arrowheads were fixed downward chevrons on almost horizontal lines, so they looked broken. Fix: new `arrow_svg()`, a straight line whose chevron follows the line's angle. The head is excluded from the draw-on and fades in as the line arrives (`data-reveal`). `causal_diagram` and `definition_card.diagram` both use it.
- The arrows ran from the cause card's corners to the icons' bounding boxes. Fix: they now leave the card's bottom centre and end just above each effect icon. Effects sit lower (portrait) so the arrows have real length, and the cause card is narrower.
- Dashed links lost their dashes. The draw-on overwrote `stroke-dasharray` with the path length. Fix: paths with `data-dash="a b"` now draw on while keeping their pattern.
- "Bukan" is the first word, so `word:Bukan` resolved to t=0 and the ✕ popped before the link it crosses existed. Fix: the link draws in 0.45 s and the ✕ follows at 7% of the scene. **Rule:** never cue a dependent element on a word that comes before (or at the same time as) the element it depends on.
- Decor "+" and "○" marks drifted over content. Fix: they now live only in the side gutters (≤ ~60 px from the edge).
- The two riding icons at the end of the chart overlapped. Fix: they are smaller (2.9 × node size).
- name-it was restaged: X, Y and "korelasi palsu" appear first, Z on "tersembunyi", its arrows on "seperti", and the card with the term on "disebut confounder". Z idles with a pulse, and the diagram is larger.
- Tests: 127 pass. Motion QA passes (min 0.33). `check-clarity` passes.

## 3. Your tasks (in order)

1. **Pull and verify:** `pytest`, `ruff check .`, `ruff format --check .`, `fnvideo validate …/short.yaml`, `fnvideo preview …/short.yaml`. Open `contact.png` with the Read tool.
2. **Comprehension check (clarity rule 10):** for each scene write "what the viewer understands at this point" into `out/…/short/comprehension.md`. Fix any scene that fails before touching anything else.
3. **Make rule 10 a tool:** add `fnvideo check-clarity <spec>`, a lint that fails if:
   - (a) a caption is not a verbatim substring of its scene narration, ignoring case and punctuation
   - (b) the first scene has no concrete element (`side_icons`, icons, or a chart)
   - (c) a mascot-only scene (title_question without `side_icons`) lasts longer than 2 s, except the close
   - (d) an explanation template has no `word:` beat

   Wire it into `validate` as warnings and into the editorial gate as errors for `approved` specs.
4. **Align the long version:** `long.yaml` still uses the sunburn example and the abstract opening. Re-author it with the same example and the same rules. Keep its chapter structure (problem → intuition → mechanism → real-world example → common mistakes → recap).
5. **Text size audit:** grep every template for font sizes below 40 px on 9:16 (axis ticks, `pill` in `definition_card`, `label_card` labels, supporting text) and raise them through `TYPE_PORTRAIT`, not per call.
6. **Owner review:** render `--silent --allow-draft`, show the owner the contact sheet and a short clip. Do not mark D-018 confirmed yourself.

## 4. Do not

- Do not reintroduce the title-first hook or the sunburn example.
- Do not paraphrase captions. If a phrase is too long, split the caption or shorten the narration itself.
- Do not change NODI anatomy or brand tokens (see CLAUDE.md design rules).
- Do not call ElevenLabs without the owner explicitly starting an audio step.

## 5. Status (Claude Code, 2026-11-20)

1. **Verified** — 88/88 tests, ruff clean, both specs valid, preview inspected.
2. **Comprehension check** — `out/…/short/comprehension.md`. Three scenes failed and were
   fixed first: hook (NODI dominated the concrete icons → `NODI_SIDE_SCALE` 0.78, icons
   240 px), name-it (4-line definition in 3.6 s → one idea + `definition_card.icon` /
   `icon_label` "Di sini: cuaca panas"), difference (grey definitions → ink).
3. **`fnvideo check-clarity`** — `services/clarity.py`, rules (a)–(d); warnings in `validate`,
   errors for `approved` specs in `validate`, `render` and inside `generate_tts`.
4. **Long version** — 14 scenes, same example and rules, chapters kept; work example
   (training ↔ salary, confounder: seniority); clarity-clean. Still outline-level (~3 min),
   not the 8–12 min deliverable.
5. **Text size** — `MIN_PORTRAIT_TEXT = 40` via `TYPE_PORTRAIT` (`label` 40, new `tick`,
   `brand`), enforced by a test over all templates.
6. **Owner review** — silent draft rendered for review. D-018 stays *proposed*.
