/* NODI rig — layered SVG puppet for F/N FOOTNOTE.
 *
 * Drawn to match assets/mascot/nodi-concept-board.png (front view).
 * Local coordinate box: 0..510 x 0..770, feet on y≈735, body centre x≈255.
 *
 * Usage (deterministic, call every frame):
 *   const nodi = NODI.mount(parentSvgGroup);
 *   nodi.update({ pose:'wave', expression:'curious', mouth:'mid', blink:0, t });
 *
 * All motion is a pure function of the state you pass — no timers, no randomness.
 */
(function (global) {
  const NS = 'http://www.w3.org/2000/svg';
  const C = {
    outline: '#0A0F24', navy: '#1D2450', navyDark: '#121835', navyLight: '#2E3A72',
    face: '#F7F4EC', faceShade: '#E4DDCC', eye: '#151B3A',
    yellow: '#F3C64B', yellowDark: '#D9A22C', strap: '#E9A93B', strapDark: '#C98A22',
    tongue: '#E56B50', mouth: '#2A1A2E', white: '#F7F4EC', lace: '#C9C3B4',
  };
  const OW = 7; // outline width

  function el(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  const line = { stroke: C.outline, 'stroke-width': OW, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' };
  const L = (o) => Object.assign({}, line, o);

  /* ---------------- static artwork ---------------- */
  function buildLegs(g) {
    // pants
    el('path', L({ d: 'M150 528 L146 650 L242 652 L250 560 L262 560 L272 652 L366 650 L360 528 Z', fill: C.navy }), g);
    el('path', { d: 'M255 560 L256 640', stroke: C.navyDark, 'stroke-width': 5, 'stroke-linecap': 'round' }, g);
    // rolled cuffs
    el('path', L({ d: 'M142 628 L246 630 L244 662 L140 660 Z', fill: C.navyLight }), g);
    el('path', L({ d: 'M268 630 L370 628 L372 660 L270 662 Z', fill: C.navyLight }), g);
    // sneakers
    const shoe = (dx, flip) => {
      const s = el('g', { transform: `translate(${dx} 0) ${flip ? 'translate(510 0) scale(-1 1)' : ''}` }, g);
      el('path', L({ d: 'M112 690 C112 662 140 652 176 652 L238 652 C250 668 252 690 250 712 L250 728 L104 728 C96 718 100 700 112 690 Z', fill: C.navy }), s);
      el('path', L({ d: 'M98 712 L252 712 L252 734 C200 742 140 742 100 736 C94 728 94 718 98 712 Z', fill: C.white }), s);
      el('path', { d: 'M120 722 L232 722', stroke: C.yellow, 'stroke-width': 6, 'stroke-linecap': 'round' }, s);
      el('path', { d: 'M168 664 L214 664 M164 678 L216 678', stroke: C.lace, 'stroke-width': 6, 'stroke-linecap': 'round' }, s);
      el('path', L({ d: 'M112 690 C120 676 140 668 160 668 L156 704 L106 704 Z', fill: C.white, 'stroke-width': 5 }), s);
    };
    shoe(0, false);
    shoe(0, true);
  }

  function buildBackpack(g) {
    // pack sides peeking behind the torso
    el('path', L({ d: 'M108 372 C88 400 88 470 104 500 L140 500 L140 372 Z', fill: C.strap }), g);
    el('path', L({ d: 'M402 372 C422 400 422 470 406 500 L370 500 L370 372 Z', fill: C.strap }), g);
    el('path', { d: 'M100 420 L132 420 M410 420 L378 420', stroke: C.strapDark, 'stroke-width': 5, 'stroke-linecap': 'round' }, g);
  }

  function buildTorso(g) {
    // hoodie body
    el('path', L({ d: 'M150 344 C120 352 112 380 112 420 L118 520 C150 540 360 540 392 520 L398 420 C398 380 390 352 360 344 Z', fill: C.navy }), g);
    // hem band
    el('path', L({ d: 'M120 506 C160 524 350 524 390 506 L392 532 C350 550 160 550 118 532 Z', fill: C.navyDark }), g);
    // zipper + pocket
    el('path', { d: 'M255 352 L255 510', stroke: C.navyDark, 'stroke-width': 5, 'stroke-linecap': 'round' }, g);
    el('path', L({ d: 'M168 448 L342 448 L352 506 L158 506 Z', fill: 'none', 'stroke-width': 5, stroke: C.navyDark }), g);
    el('path', { d: 'M176 458 L166 498 M334 458 L344 498', stroke: C.yellow, 'stroke-width': 6, 'stroke-linecap': 'round' }, g);
    // backpack straps over shoulders
    el('path', L({ d: 'M158 346 L180 346 L176 450 L156 450 Z', fill: C.strap, 'stroke-width': 5 }), g);
    el('path', L({ d: 'M330 346 L352 346 L354 450 L334 450 Z', fill: C.strap, 'stroke-width': 5 }), g);
    // F/N chest mark
    const t = el('text', { x: 296, y: 402, 'font-family': 'Space Grotesk, Poppins, sans-serif', 'font-weight': 800, 'font-size': 20, fill: C.yellow }, g);
    t.textContent = 'F/N';
    // hood collar around neck (drawn on torso so head sits above it)
    el('path', L({ d: 'M176 334 C190 362 222 372 255 372 C288 372 320 362 334 334 C320 346 290 352 255 352 C220 352 190 346 176 334 Z', fill: C.navyDark }), g);
    // drawstrings
    el('path', { d: 'M232 362 L228 410', stroke: C.white, 'stroke-width': 5, 'stroke-linecap': 'round' }, g);
    el('path', { d: 'M278 362 L282 410', stroke: C.white, 'stroke-width': 5, 'stroke-linecap': 'round' }, g);
    el('circle', { cx: 228, cy: 413, r: 4.5, fill: C.white }, g);
    el('circle', { cx: 282, cy: 413, r: 4.5, fill: C.white }, g);
  }

  function buildHead(g) {
    // hood silhouette: rounded left "ear", slanted ridge rising to a peak at top-right
    el('path', L({
      d: 'M168 334 C130 322 104 300 90 262 L50 200 C46 190 52 180 60 174 L92 134 C96 128 102 124 110 120 ' +
         'L296 34 C312 28 328 30 340 40 L438 112 C448 120 454 132 456 146 L460 214 ' +
         'C460 252 446 282 420 302 C390 326 344 340 296 342 C250 344 204 344 168 334 Z',
      fill: C.navy, 'stroke-width': OW + 1,
    }), g);
    // light facet on the ridge
    el('path', { d: 'M100 136 L296 44 C268 72 190 112 112 156 Z', fill: C.navyLight, opacity: 0.85 }, g);
    el('path', { d: 'M60 182 L92 140 L104 160 L72 200 Z', fill: C.navyLight, opacity: 0.6 }, g);
    // hood opening (inner rim, darker)
    el('path', {
      d: 'M110 168 C150 140 250 128 352 132 C392 134 418 158 420 196 C424 246 404 294 360 314 ' +
         'C320 330 220 334 168 318 C126 304 104 270 102 226 C100 200 102 180 110 168 Z',
      fill: C.navyDark,
    }, g);
    // face mask: wide rounded rectangle with soft chamfers
    el('path', L({
      d: 'M126 182 C150 162 250 152 346 154 C380 156 400 176 402 206 C404 244 392 280 356 296 ' +
         'C316 312 226 314 176 302 C140 292 120 264 118 228 C117 206 118 192 126 182 Z',
      fill: C.face, 'stroke-width': 5,
    }), g);
    // face shade along the lower-right edge
    el('path', { d: 'M392 230 C390 262 376 284 352 294 C312 308 230 310 180 300 C240 300 320 292 356 274 C378 262 388 248 392 230 Z', fill: C.faceShade }, g);
    // yellow folded corner at the peak
    const corner = el('g', { id: 'nodi-corner' }, g);
    el('path', L({ d: 'M300 36 L424 112 L338 168 Z', fill: C.yellow, 'stroke-width': OW }), corner);
    el('path', { d: 'M338 168 L380 140 L424 112 L372 132 Z', fill: C.yellowDark }, corner);
    el('path', { d: 'M318 66 L392 112', stroke: '#FFE08A', 'stroke-width': 5, 'stroke-linecap': 'round', opacity: 0.8 }, corner);
    // feature layers (filled by update)
    el('g', { id: 'nodi-brows' }, g);
    el('g', { id: 'nodi-eyes' }, g);
    el('g', { id: 'nodi-mouth' }, g);
    el('g', { id: 'nodi-fx' }, g);
  }

  /* ---------------- features ---------------- */
  const EYE_L = [205, 232], EYE_R = [300, 226];
  function capsule(p, cx, cy, h, w = 24, fill = C.eye) {
    el('rect', { x: cx - w / 2, y: cy - h / 2, width: w, height: h, rx: w / 2, fill }, p);
  }
  function arc(p, d, w = 9) { el('path', { d, stroke: C.eye, 'stroke-width': w, fill: 'none', 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, p); }

  const EYES = {
    capsule(p, blink, look) {
      const h = Math.max(6, 58 * (1 - blink));
      if (h <= 8) { arc(p, `M${EYE_L[0] - 16 + look} ${EYE_L[1]} h32`); arc(p, `M${EYE_R[0] - 16 + look} ${EYE_R[1]} h32`); return; }
      capsule(p, EYE_L[0] + look, EYE_L[1], h); capsule(p, EYE_R[0] + look, EYE_R[1], h);
    },
    happy(p) { arc(p, `M${EYE_L[0] - 24} ${EYE_L[1] + 8} Q${EYE_L[0]} ${EYE_L[1] - 22} ${EYE_L[0] + 24} ${EYE_L[1] + 8}`); arc(p, `M${EYE_R[0] - 24} ${EYE_R[1] + 8} Q${EYE_R[0]} ${EYE_R[1] - 22} ${EYE_R[0] + 24} ${EYE_R[1] + 8}`); },
    surprised(p) { [EYE_L, EYE_R].forEach(([x, y]) => el('ellipse', { cx: x, cy: y, rx: 15, ry: 26, fill: 'none', stroke: C.eye, 'stroke-width': 8 }, p)); },
    skeptical(p) {
      [EYE_L, EYE_R].forEach(([x, y]) => { el('path', { d: `M${x - 20} ${y - 4} h40 v12 a20 14 0 0 1 -40 0 Z`, fill: C.eye }, p); });
    },
    excited(p) {
      arc(p, `M${EYE_L[0] - 20} ${EYE_L[1] - 16} L${EYE_L[0] + 16} ${EYE_L[1]} L${EYE_L[0] - 20} ${EYE_L[1] + 16}`);
      arc(p, `M${EYE_R[0] + 20} ${EYE_R[1] - 16} L${EYE_R[0] - 16} ${EYE_R[1]} L${EYE_R[0] + 20} ${EYE_R[1] + 16}`);
    },
    thinking(p, blink) {
      arc(p, `M${EYE_L[0] - 20} ${EYE_L[1] + 4} Q${EYE_L[0]} ${EYE_L[1] - 6} ${EYE_L[0] + 20} ${EYE_L[1] + 4}`);
      capsule(p, EYE_R[0], EYE_R[1] + 4, Math.max(6, 46 * (1 - blink)));
    },
  };
  const BROWS = {
    none() {},
    skeptical(p) { arc(p, `M${EYE_L[0] - 26} ${EYE_L[1] - 22} L${EYE_L[0] + 22} ${EYE_L[1] - 18}`, 8); arc(p, `M${EYE_R[0] - 22} ${EYE_R[1] - 20} L${EYE_R[0] + 26} ${EYE_R[1] - 26}`, 8); },
    thinking(p) { arc(p, `M${EYE_R[0] - 22} ${EYE_R[1] - 30} L${EYE_R[0] + 24} ${EYE_R[1] - 42}`, 8); },
    raised(p) { arc(p, `M${EYE_L[0] - 20} ${EYE_L[1] - 48} Q${EYE_L[0]} ${EYE_L[1] - 58} ${EYE_L[0] + 20} ${EYE_L[1] - 48}`, 7); arc(p, `M${EYE_R[0] - 20} ${EYE_R[1] - 48} Q${EYE_R[0]} ${EYE_R[1] - 58} ${EYE_R[0] + 20} ${EYE_R[1] - 48}`, 7); },
  };
  const MX = 252, MY = 272; // mouth anchor
  const MOUTHS = {
    none() {},
    smile(p) { arc(p, `M${MX - 16} ${MY} Q${MX} ${MY + 12} ${MX + 16} ${MY}`, 7); },
    small(p) { el('path', { d: `M${MX - 14} ${MY - 2} Q${MX} ${MY + 18} ${MX + 14} ${MY - 2} Z`, fill: C.mouth, stroke: C.mouth, 'stroke-width': 4, 'stroke-linejoin': 'round' }, p); },
    mid(p) {
      el('path', { d: `M${MX - 20} ${MY - 6} Q${MX} ${MY + 28} ${MX + 20} ${MY - 6} Z`, fill: C.mouth, stroke: C.mouth, 'stroke-width': 4, 'stroke-linejoin': 'round' }, p);
      el('ellipse', { cx: MX, cy: MY + 10, rx: 9, ry: 5, fill: C.tongue }, p);
    },
    wide(p) {
      el('path', { d: `M${MX - 26} ${MY - 10} Q${MX} ${MY + 40} ${MX + 26} ${MY - 10} Z`, fill: C.mouth, stroke: C.mouth, 'stroke-width': 4, 'stroke-linejoin': 'round' }, p);
      el('ellipse', { cx: MX, cy: MY + 14, rx: 13, ry: 7, fill: C.tongue }, p);
    },
    o(p) { el('ellipse', { cx: MX, cy: MY + 4, rx: 11, ry: 15, fill: C.mouth }, p); },
    grin(p) { // happy / excited open smile
      el('path', { d: `M${MX - 22} ${MY - 6} Q${MX} ${MY + 30} ${MX + 22} ${MY - 6} Z`, fill: C.mouth, stroke: C.mouth, 'stroke-width': 4, 'stroke-linejoin': 'round' }, p);
      el('ellipse', { cx: MX, cy: MY + 11, rx: 10, ry: 6, fill: C.tongue }, p);
    },
  };
  const EXPRESSIONS = {
    neutral: { eyes: 'capsule', brows: 'none', idleMouth: 'none' },
    curious: { eyes: 'capsule', brows: 'none', idleMouth: 'none', fx: 'question' },
    happy: { eyes: 'happy', brows: 'none', idleMouth: 'grin', fx: 'spark' },
    surprised: { eyes: 'surprised', brows: 'raised', idleMouth: 'o', fx: 'bang' },
    skeptical: { eyes: 'skeptical', brows: 'skeptical', idleMouth: 'none' },
    thinking: { eyes: 'thinking', brows: 'thinking', idleMouth: 'none', fx: 'dots' },
    excited: { eyes: 'excited', brows: 'none', idleMouth: 'grin', fx: 'spark' },
  };

  function drawFx(p, kind, t) {
    const wob = Math.sin(t * 4) * 4;
    if (kind === 'question') {
      const tx = el('text', { x: 462, y: 70 + wob, 'font-family': 'Anton, Space Grotesk, sans-serif', 'font-size': 84, fill: C.outline }, p); tx.textContent = '?';
    } else if (kind === 'dots') {
      [0, 1, 2].forEach((i) => el('circle', { cx: 448 + i * 24, cy: 60 + Math.sin(t * 5 + i) * 4, r: 8, fill: C.outline }, p));
    } else if (kind === 'spark') {
      [[60, 70, 0], [30, 120, 1]].forEach(([x, y, i]) => el('path', { d: `M${x} ${y} l18 -34`, stroke: C.yellow, 'stroke-width': 12, 'stroke-linecap': 'round', opacity: 0.6 + 0.4 * Math.sin(t * 6 + i) }, p));
      el('path', { d: 'M88 96 l34 -14', stroke: C.yellow, 'stroke-width': 12, 'stroke-linecap': 'round' }, p);
    } else if (kind === 'bang') {
      el('path', { d: `M52 ${60 + wob} l8 54 M80 ${50 + wob} l6 56`, stroke: C.yellow, 'stroke-width': 14, 'stroke-linecap': 'round' }, p);
      el('circle', { cx: 62, cy: 134 + wob, r: 8, fill: C.yellow }, p); el('circle', { cx: 88, cy: 126 + wob, r: 8, fill: C.yellow }, p);
    }
  }

  /* ---------------- arms ---------------- */
  // Angles in degrees: a1 = upper arm from straight down (+ = outward), a2 = forearm relative to a1.
  const POSES = {
    rest: { L: [12, -6], R: [12, -6], handL: 'mitten', handR: 'mitten' },
    wave: { L: [12, -6], R: [70, 105], handL: 'mitten', handR: 'open' },
    point: { L: [12, -6], R: [60, 70], handL: 'mitten', handR: 'point' },
    explain: { L: [30, 70], R: [36, 92], handL: 'open', handR: 'open' },
    shrug: { L: [52, 98], R: [52, 98], handL: 'open', handR: 'open' },
    think: { L: [12, -6], R: [-75, 255], handL: 'mitten', handR: 'fist', overHead: true },
    cheer: { L: [-40, 200], R: [70, 110], handL: 'fist', handR: 'fist', overHead: true },
  };
  const SHOULDER = { L: [146, 372], R: [364, 372] }, UA = 78, FA = 74;

  /* Talking gestures: while NODI speaks, the arms cycle through these shapes on a
   * deterministic schedule (segment lengths and order come from a seeded hash of the
   * segment index, so the same t always gives the same frame). */
  const GESTURES = {
    both: { L: [30, 72], R: [34, 88], handL: 'open', handR: 'open' },
    palm: { L: [14, -4], R: [30, 78], handL: 'mitten', handR: 'open' },
    present: { L: [14, -4], R: [78, 18], handL: 'mitten', handR: 'open' },
    count: { L: [14, -4], R: [-32, 206], handL: 'mitten', handR: 'point' },
    wide: { L: [58, 36], R: [58, 36], handL: 'open', handR: 'open' },
    leftpalm: { L: [32, 80], R: [14, -4], handL: 'open', handR: 'mitten' },
  };
  const GESTURE_ORDER = Object.keys(GESTURES);
  // How strongly auto-gestures override the authored pose while speaking.
  const GESTURE_WEIGHT = { explain: 1, rest: 0.6 };
  const hash = (i, seed) => { const x = Math.sin(i * 12.9898 + seed * 78.233) * 43758.5453; return x - Math.floor(x); };
  const ease = (k) => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2);

  function gestureAt(t, seed) {
    let start = 0, i = 0, idx = 0, prevIdx = 0;
    for (;;) {
      const len = 1.6 + 0.9 * hash(i, seed);
      if (t < start + len) break;
      start += len; i += 1; prevIdx = idx;
      idx = (idx + 1 + Math.floor(hash(i + 100, seed) * (GESTURE_ORDER.length - 1))) % GESTURE_ORDER.length;
    }
    const A = GESTURES[GESTURE_ORDER[prevIdx]], B = GESTURES[GESTURE_ORDER[idx]];
    const k = i === 0 ? 1 : ease(Math.min(1, (t - start) / 0.38));
    const mix = (sd) => [A[sd][0] + (B[sd][0] - A[sd][0]) * k, A[sd][1] + (B[sd][1] - A[sd][1]) * k];
    return { L: mix('L'), R: mix('R'), handL: k > 0.5 ? B.handL : A.handL, handR: k > 0.5 ? B.handR : A.handR };
  }

  function drawArm(p, side, a1, a2, hand, wrist = 0) {
    const sg = side === 'R' ? 1 : -1, [sx, sy] = SHOULDER[side];
    const r1 = a1 * Math.PI / 180, r2 = (a1 + a2) * Math.PI / 180;
    const ex = sx + sg * Math.sin(r1) * UA, ey = sy + Math.cos(r1) * UA;
    const hx = ex + sg * Math.sin(r2) * FA, hy = ey + Math.cos(r2) * FA;
    const d = `M${sx} ${sy} L${ex} ${ey} L${hx} ${hy}`;
    el('path', { d, stroke: C.outline, 'stroke-width': 46 + OW * 2, fill: 'none', 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, p);
    el('path', { d, stroke: C.navy, 'stroke-width': 46, fill: 'none', 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, p);
    // cuff
    const cx = ex + (hx - ex) * 0.78, cy = ey + (hy - ey) * 0.78;
    el('circle', { cx, cy, r: 22, fill: C.navyDark }, p);
    // hand (oriented along the forearm)
    const ang = Math.atan2(hy - ey, hx - ex) * 180 / Math.PI;
    const hg = el('g', { transform: `translate(${hx} ${hy}) rotate(${ang - 90 + wrist}) scale(1.22)` }, p);
    const skin = { fill: C.face, stroke: C.outline, 'stroke-width': 5, 'stroke-linejoin': 'round' };
    if (hand === 'point') {
      el('rect', Object.assign({ x: -7, y: 14, width: 14, height: 34, rx: 7 }, skin), hg);
      el('circle', Object.assign({ cx: 0, cy: 10, r: 18 }, skin), hg);
    } else if (hand === 'open') {
      el('path', Object.assign({ d: 'M-20 0 C-22 18 -18 34 -8 40 L-8 46 C-8 52 0 52 0 46 L0 42 L4 48 C6 54 14 52 12 44 L10 38 L16 42 C20 46 26 40 22 34 C26 22 24 6 18 -2 Z' }, skin), hg);
      el('ellipse', Object.assign({ cx: sg * -22, cy: 10, rx: 8, ry: 13, transform: `rotate(${sg * 30} ${sg * -22} 10)` }, skin), hg);
    } else if (hand === 'fist') {
      el('circle', Object.assign({ cx: 0, cy: 12, r: 21 }, skin), hg);
      el('path', { d: 'M-12 6 Q0 2 12 6 M-12 16 Q0 12 12 16', stroke: C.outline, 'stroke-width': 3.5, fill: 'none', 'stroke-linecap': 'round', opacity: 0.6 }, hg);
    } else {
      el('ellipse', Object.assign({ cx: 0, cy: 12, rx: 20, ry: 22 }, skin), hg);
      el('ellipse', Object.assign({ cx: sg * -18, cy: 6, rx: 8, ry: 11 }, skin), hg);
    }
  }

  /* ---------------- mount / update ---------------- */
  function mount(parent) {
    const root = el('g', { class: 'nodi' }, parent);
    el('ellipse', { cx: 255, cy: 740, rx: 170, ry: 16, fill: '#000', opacity: 0.18 }, root); // ground shadow
    const body = el('g', {}, root);
    const back = el('g', {}, body); buildBackpack(back);
    const legs = el('g', {}, body); buildLegs(legs);
    const armsBack = el('g', {}, body);
    const torso = el('g', {}, body); buildTorso(torso);
    const armsFront = el('g', {}, body);
    const head = el('g', {}, body); buildHead(head);
    const armsTop = el('g', {}, body);
    const q = (id) => head.querySelector('#' + id);
    const parts = { brows: q('nodi-brows'), eyes: q('nodi-eyes'), mouth: q('nodi-mouth'), fx: q('nodi-fx') };
    for (const k in parts) parts[k].removeAttribute('id');

    let prevPose = 'rest', curPose = 'rest', poseStart = 0;
    return {
      root,
      /**
       * state: { t, pose, poseT (seconds since pose change; optional), expression, mouth (lip-sync shape or null),
       *          blink (0..1), headTilt (deg), lookX (px), breathe (0..1 amplitude), talkEnergy (0..1),
       *          activity (0..1, smoothed "is speaking" — drives hand gestures),
       *          gesture ('auto' | 'none', default 'auto'), gestureSeed (number, vary per scene) }
       */
      update(s) {
        const t = s.t || 0;
        if (s.pose && s.pose !== curPose) { prevPose = curPose; curPose = s.pose; poseStart = t; }
        const k = s.poseT !== undefined ? Math.min(1, s.poseT / 0.32) : Math.min(1, (t - poseStart) / 0.32);
        const e = k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
        const A = POSES[prevPose] || POSES.rest, B = POSES[curPose] || POSES.rest;
        const mix = (sd) => [A[sd][0] + (B[sd][0] - A[sd][0]) * e, A[sd][1] + (B[sd][1] - A[sd][1]) * e];
        let aL = mix('L'), aR = mix('R');
        let handL = e > 0.5 ? B.handL : A.handL, handR = e > 0.5 ? B.handR : A.handR;
        const act = Math.max(0, Math.min(1, s.activity || 0));
        const seed = s.gestureSeed || 0;

        // 1) auto talking gestures blended over the authored pose
        const gw = s.gesture === 'none' ? 0 : (GESTURE_WEIGHT[curPose] || 0) * act;
        if (gw > 0) {
          const G = gestureAt(t, seed);
          aL = [aL[0] + (G.L[0] - aL[0]) * gw, aL[1] + (G.L[1] - aL[1]) * gw];
          aR = [aR[0] + (G.R[0] - aR[0]) * gw, aR[1] + (G.R[1] - aR[1]) * gw];
          if (gw > 0.5) { handL = G.handL; handR = G.handR; }
        }
        // 2) pose-specific loops
        if (curPose === 'wave' && e > 0.6) aR = [aR[0], aR[1] + Math.sin(t * 13) * 18];
        if (curPose === 'cheer') aR = [aR[0] + Math.sin(t * 9) * 6, aR[1]];
        if (curPose === 'shrug') { const b = Math.sin(t * 2.4) * 5; aL[1] += b; aR[1] += b; }
        // 3) beat motion while speaking + subtle idle sway always
        const ph = seed * 1.7;
        aL[0] += Math.sin(t * 1.1 + ph) * 1.5 + act * Math.sin(t * 2.3 + ph) * 4;
        aR[0] += Math.sin(t * 1.3 + ph + 2) * 1.5 + act * Math.sin(t * 2.1 + ph + 1) * 4;
        if (curPose !== 'wave' && curPose !== 'think') {
          aL[1] += act * (Math.sin(t * 5.3 + ph) * 7 + Math.sin(t * 8.1 + ph) * 3);
          aR[1] += act * (Math.sin(t * 4.9 + ph + 1.3) * 8 + Math.sin(t * 7.7 + ph) * 3);
        }
        const wristL = act * Math.sin(t * 4.7 + ph) * 12, wristR = act * Math.sin(t * 4.3 + ph + 0.8) * 12;

        armsBack.innerHTML = ''; armsFront.innerHTML = ''; armsTop.innerHTML = '';
        const front = (e > 0.5 ? B : A).overHead ? armsTop : armsFront;
        // raised arms in front of the torso, resting arms behind it
        drawArm(aL[1] > 40 || aL[0] < -10 ? front : armsBack, 'L', aL[0], aL[1], handL, wristL);
        drawArm(aR[1] > 40 || aR[0] < -10 ? front : armsBack, 'R', aR[0], aR[1], handR, wristR);

        const ex = EXPRESSIONS[s.expression] || EXPRESSIONS.neutral;
        parts.eyes.innerHTML = ''; parts.brows.innerHTML = ''; parts.mouth.innerHTML = ''; parts.fx.innerHTML = '';
        EYES[ex.eyes](parts.eyes, s.blink || 0, s.lookX || 0);
        BROWS[ex.brows](parts.brows);
        const m = s.mouth && s.mouth !== 'none' ? s.mouth : ex.idleMouth;
        MOUTHS[m] ? MOUTHS[m](parts.mouth) : null;
        if (ex.fx && s.fx !== false) drawFx(parts.fx, ex.fx, t);

        const energy = s.talkEnergy || 0;
        const tilt = (s.headTilt || 0) + Math.sin(t * 2.0) * 2 + energy * 3;
        const bob = Math.sin(t * 3.0) * 3 - energy * 5;
        head.setAttribute('transform', `translate(0 ${bob}) rotate(${tilt} 255 340)`);
        const br = (s.breathe === undefined ? 1 : s.breathe) * Math.sin(t * 1.8);
        body.setAttribute('transform', `translate(255 735) scale(${1 + br * 0.008} ${1 - br * 0.008}) translate(-255 -735)`);
      },
    };
  }

  global.NODI = { mount, POSES, GESTURES, EXPRESSIONS, MOUTHS: Object.keys(MOUTHS), colors: C };
})(window);
