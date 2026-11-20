# NODI rig — layered SVG puppet

Source: `src/fnvideo/render/assets/nodi_rig.js` (embedded into each scene page by `svg_scene.py` when `character.mascot: on`).
Drawn from `assets/mascot/nodi-concept-board.png` (front view) and compared side by side with the board during authoring.

## Artwork box
- Local coordinates `0..510 × 0..770`, feet at y≈735, body centre x≈255 (`NODI_W, NODI_H = 510, 770`).
- Layer order (back → front): ground shadow, backpack, legs/sneakers, resting arms, hoodie torso + straps + drawstrings, raised arms, head (hood, face mask, yellow folded corner, brows, eyes, mouth, fx), arms that pass in front of the head (`think`, `cheer`).

## API (deterministic: call every frame)
```js
const nodi = NODI.mount(svgGroup);
nodi.update({
  t,                 // scene time in seconds
  pose,              // rest | wave | point | explain | shrug | think | cheer
  poseT,             // seconds since this pose started (0.32 s eased transition)
  expression,        // neutral | curious | happy | surprised | skeptical | thinking | excited
  mouth,             // lip-sync shape: none | small | mid | wide | o  (null → expression's idle mouth)
  blink,             // 0..1
  talkEnergy,        // 0..1, drives head bob/tilt
  headTilt, lookX,   // optional extra tilt (deg) / eye offset (px)
  breathe,           // 0..1 amplitude, default 1
  fx,                // false to hide the expression's effect (?, …, sparks, !!)
  activity,          // 0..1 smoothed "is speaking" — drives hand gestures
  gesture,           // 'auto' (default) | 'none'
  gestureSeed,       // number; different seeds give different gesture schedules
});
```
No timers, no randomness: identical state → identical frame.

## Hand gestures while talking
- While `activity > 0`, the arms move on their own:
  - **Auto gestures** (`GESTURES`: `both`, `palm`, `present`, `count`, `wide`, `leftpalm`) cycle every 1.6–2.5 s with a 0.38 s eased blend. The order and segment lengths come from a seeded hash of the segment index, so the result is deterministic. Weight: full for pose `explain` (spec `explaining`/`talk`/`gesture`), 0.6 for `rest`, 0 for authored poses (`wave`, `point`, `think`, `shrug`, `cheer`) so those stay readable.
  - **Beat motion**: forearm bounce + upper-arm sway + wrist rotation (±12°) scaled by `activity`.
  - **Idle sway**: a ±1.5° drift even when silent, so arms never freeze.
- `svg_scene.py` computes `activity` from the scene's caption windows (0.3 s ramps) and passes the scene index as `gestureSeed`.
- Add a gesture: put a new entry in `GESTURES` (same format as `POSES`); it joins the cycle automatically.

## Spec mapping (`svg_scene.py`)
- `character.mascot_pose` → `NODI_POSE_MAP` (e.g. `explaining`/`talk`/`gesture` → `explain`, `curious → rest`).
- `character.expression` → `NODI_EXPRESSION_MAP` (e.g. `thoughtful → thinking`).
- Audio mouth `smile` (silence) → `none` (NODI has no mouth when quiet, as on the board).
- Dark backgrounds (`navy`, `navy_dark`, `deep_blue`) get the `#nodiRim` paper sticker outline so the navy hood stays readable.

## Extending
- New pose: add to `POSES` (`L`/`R` = `[upperArmDeg, forearmDeg]`, 0 = straight down, + = outward; negative upper-arm angle crosses the chest), pick hand shapes (`mitten | open | point | fist`), set `overHead: true` if the hand must pass in front of the face.
- New expression: add an `EYES`/`BROWS` drawer if needed, then an entry in `EXPRESSIONS`.
- Outfits: the torso is built in `buildTorso`; add variants there (classic is implemented).

## Replacing with illustrator art
Keep the same part names and pivots: shoulders `(146,372)` / `(364,372)`, upper arm 78, forearm 74, head pivot `(255,340)`, eye anchors `(205,232)` / `(300,226)`, mouth anchor `(252,272)`. Deliver each part as a separate SVG group in the 510×770 box and swap the `build*` functions to inline them.

## Known simplifications vs. the board
Front view only (no ¾ head turn), flat shading (no fabric folds), single outfit (classic), no props yet (book, laptop, magnifier).
