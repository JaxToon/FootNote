from __future__ import annotations

import base64
import html
import io
import json
import math
import re
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from fnvideo.models.episode import EpisodeSpec, SceneSpec

SCENE_BACKGROUNDS = {
    "navy": "#111D38",
    "navy_dark": "#0B1428",
    "purple": "#5142A0",
    "teal": "#245F59",
    "paper": "#F4F1E8",
    "deep_blue": "#243D57",
    "coral": "#E56B50",
    "yellow": "#F3D65B",
}
NAVY = "#111D38"
YELLOW = "#F3D65B"
PAPER = "#F4F1E8"
CORAL = "#E56B50"
TEAL = "#6CB7A6"
BLUE = "#89B7D7"


@dataclass(frozen=True)
class Theme:
    """Colour roles for one background. Light = editorial paper look (navy ink, like the
    NODI concept board); dark = contrast scenes."""

    name: str
    ink: str  # main text and lines on the background
    muted: str  # secondary text
    accent: str  # rules, drawn symbols
    line: str  # connectors / arrows
    highlight: str  # caption highlighter swipe
    card_fill: str
    card_opacity: float
    card_stroke: str
    card_stroke_opacity: float
    card_stroke_width: float
    label_fill: str  # label cards under icons
    caption_stroke: str | None
    blobs: tuple[str, ...]
    blob_opacity: float
    grain_opacity: float


THEME_DARK = Theme(
    "dark", PAPER_HEX := "#F4F1E8", "#D8E0EF", "#F3D65B", "#F3D65B", "#F3D65B",
    "#FFFFFF", 0.08, "#FFFFFF", 0.22, 2, PAPER_HEX, "#0B1428",
    ("#2B4A6F", "#5142A0"), 0.45, 0.30,
)  # fmt: skip
THEME_PAPER = Theme(
    "light", "#111D38", "#4C5A75", "#E56B50", "#111D38", "#F3D65B",
    "#FFFFFF", 0.75, "#111D38", 0.9, 5, "#FFFFFF", None,
    ("#F3D65B", "#FFFFFF"), 0.30, 0.22,
)  # fmt: skip
THEME_YELLOW = Theme(
    "light", "#111D38", "#3A3A2A", "#E56B50", "#111D38", "#F4F1E8",
    "#FFFFFF", 0.6, "#111D38", 0.9, 5, "#FFFFFF", None,
    ("#FFFFFF", "#F7E089"), 0.30, 0.22,
)  # fmt: skip
# Coral is a dark (light-text) scene, but its colour fields must stay warm.
THEME_CORAL = replace(THEME_DARK, blobs=("#F3D65B", "#F4F1E8"), blob_opacity=0.18)
THEMES = {"paper": THEME_PAPER, "yellow": THEME_YELLOW, "coral": THEME_CORAL}


def theme_for(background: str) -> Theme:
    return THEMES.get(background, THEME_DARK)


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def split_lines(text: str, max_chars: int = 22) -> list[str]:
    words = str(text).split()
    if not words:
        return [""]
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > max_chars and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines[:4]


def svg_text(
    x: float,
    y: float,
    text: str,
    *,
    size: int = 48,
    fill: str = "currentColor",
    weight: int = 700,
    anchor: str = "middle",
    family: str = "Inter, sans-serif",
    max_chars: int = 22,
    line_gap: float | None = None,
) -> str:
    lines = split_lines(text, max_chars)
    gap = line_gap or size * 1.18
    tspans = "".join(
        f'<tspan x="{x}" dy="{0 if i == 0 else gap}">{symbol_placeholders(esc(line))}</tspan>'
        for i, line in enumerate(lines)
    )
    node = (
        f'<text x="{x}" y="{y}" fill="{fill}" font-family="{family}" '
        f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" '
        f'letter-spacing="-1">{tspans}</text>'
    )
    count = sum(line.count(ch) for line in lines for ch in DRAWN_SYMBOLS)
    if not count:
        return node
    # One path per drawn symbol; render(t) positions it from the placeholder's glyph box.
    paths = "".join(
        '<path data-sym-path="1" data-nodraw="1" class="fn-accent"/>' for _ in range(count)
    )
    return f'<g data-sym-size="{size}">{node}{paths}</g>'


# Symbols drawn as SVG instead of font glyphs (display fonts render them too small/thin).
# Each becomes an invisible placeholder glyph of similar width in the text run.
DRAWN_SYMBOLS = {"≠": "neq"}


def symbol_placeholders(escaped_line: str) -> str:
    for ch, name in DRAWN_SYMBOLS.items():
        escaped_line = escaped_line.replace(
            ch, f'<tspan data-sym="{name}" fill-opacity="0">M</tspan>'
        )
    return escaped_line


def rounded_card(
    x: float,
    y: float,
    w: float,
    h: float,
    fill: str = "#FFFFFF",
    opacity: float = 0.09,
    stroke: str = "#FFFFFF",
    stroke_opacity: float = 0.18,
    radius: int = 28,
    stroke_width: float = 2,
) -> str:
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{radius}" '
        f'fill="{fill}" fill-opacity="{opacity}" stroke="{stroke}" stroke-opacity="{stroke_opacity}" '
        f'stroke-width="{stroke_width}"/>'
    )


def theme_card(th: Theme, x: float, y: float, w: float, h: float, *, radius: int = 32,
               accent: str | None = None) -> str:  # fmt: skip
    return rounded_card(x, y, w, h, th.card_fill, th.card_opacity, accent or th.card_stroke,
                        th.card_stroke_opacity, radius, th.card_stroke_width)  # fmt: skip


NODI_RIG_JS = (Path(__file__).parent / "assets" / "nodi_rig.js").read_text(encoding="utf-8")

# Spec vocabulary -> rig vocabulary (see assets/nodi_rig.js POSES / EXPRESSIONS).
NODI_POSE_MAP = {
    "rest": "rest",
    "curious": "rest",
    "wave": "wave",
    "point": "point",
    "explaining": "explain",
    "explain": "explain",
    "thinking": "think",
    "think": "think",
    "shrug": "shrug",
    "cheer": "cheer",
    "excited": "cheer",
    "talk": "explain",
    "gesture": "explain",
}
NODI_EXPRESSION_MAP = {
    "neutral": "neutral",
    "curious": "curious",
    "happy": "happy",
    "surprised": "surprised",
    "skeptical": "skeptical",
    "thinking": "thinking",
    "thoughtful": "thinking",
    "excited": "excited",
    "explaining": "neutral",
}
DARK_BACKGROUNDS = {"navy", "navy_dark", "deep_blue"}


def nodi_layer(x: float, y: float, scale: float, *, rim: bool) -> str:
    """Mount point for the layered NODI rig (drawn and animated by nodi_rig.js).

    On dark backgrounds a paper-coloured sticker rim keeps the navy hood readable.
    """
    rim_attr = ' filter="url(#nodiRim)"' if rim else ""
    return (
        f'<g id="nodi" transform="translate({x:.1f} {y:.1f}) scale({scale})"{rim_attr}>'
        '<g id="nodi-holder"></g></g>'
    )


@dataclass(frozen=True)
class Layout:
    """Canvas zones and type scale for one scene. Templates draw only inside the content zone."""

    width: int
    height: int
    portrait: bool
    left: float
    right: float
    top: float  # content zone top
    bottom: float  # content must end above this y
    caption_base: float  # baseline of the (last) caption line
    type: dict[str, int]
    nodi: tuple[float, float, float] | None  # x, y, scale
    th: Theme = THEME_DARK

    @property
    def cx(self) -> float:
        return (self.left + self.right) / 2

    @property
    def usable(self) -> float:
        return self.right - self.left

    def chars(self, size: float, width: float | None = None, em: float = 0.56) -> int:
        """How many characters of *size* px fit in *width* (default: content width)."""
        return max(6, int((width or self.usable) / (size * em)))


# NODI rig artwork box (assets/nodi_rig.js): 510 x 770 units before scaling.
NODI_W, NODI_H = 510, 770
SHORT_SAFE_BOTTOM = 0.80  # keep important info out of the bottom 20% (platform UI)
# Measured rig geometry (artwork units): body centre x, feet incl. shadow, head y 31..343.
NODI_CENTER_X, NODI_FEET_Y, NODI_TOP_Y = 255, 756, 31
NODI_PORTRAIT_SCALE = 1.2
NODI_SIDE_SCALE = (
    0.78  # NODI yields to concrete side icons (clarity rule 1; NODI must not dominate)
)
SIDE_ICON_SIZE = 240.0
NODI_SLIDE_SECONDS = 0.5
HEADLINE_MIN = 110
DISPLAY_CAP_EM = 0.66  # Space Grotesk bold caps average advance (em), measured conservatively

# 9:16 is the primary format: big type that reads on a phone at arm's length.
TYPE_PORTRAIT = {
    "headline": 132, "term": 100, "supporting": 46, "body": 44, "node": 42,
    "label": 38, "caption": 56, "number": 40,
}  # fmt: skip
TYPE_LANDSCAPE = {
    "headline": 104, "term": 84, "supporting": 40, "body": 36, "node": 34,
    "label": 32, "caption": 48, "number": 34,
}  # fmt: skip


def compute_layout(
    width: int,
    height: int,
    mascot_on: bool,
    background: str = "navy",
    nodi_scale: float | None = None,
) -> Layout:
    """Layout plus the theme for *background* (light paper/yellow or dark).

    *nodi_scale* shrinks NODI in 9:16 when the scene puts content beside it (side_icons).
    """
    return replace(_compute_layout(width, height, mascot_on, nodi_scale), th=theme_for(background))


def _compute_layout(
    width: int, height: int, mascot_on: bool, nodi_scale: float | None = None
) -> Layout:
    portrait = height > width
    if portrait:
        # Content y=200..1450; one-line captions sit on a baseline just above the
        # bottom-20% platform-UI zone (1536 on a 1920 canvas).
        caption_base = height * SHORT_SAFE_BOTTOM - 21
        left, right, top, bottom = 64, width - 64, 200, caption_base - 65
        nodi = None
        if mascot_on:
            # NODI is the performer: centred, feet on the content floor, head ~370px.
            scale = nodi_scale or NODI_PORTRAIT_SCALE
            nodi = (width / 2 - NODI_CENTER_X * scale, bottom - NODI_FEET_Y * scale, scale)
            bottom = nodi[1] - 24  # the content band sits above NODI's head
        return Layout(
            width, height, True, left, right, top, bottom, caption_base, TYPE_PORTRAIT, nodi
        )
    caption_base = height - 90
    left, right, top, bottom = 96, width - 96, 140, caption_base - 110
    if mascot_on:
        scale = 0.50
        nodi = (width - 72 - NODI_W * scale, (top + bottom) / 2 - NODI_H * scale / 2, scale)
        return Layout(
            width, height, False, left, width - 420, top, bottom, caption_base, TYPE_LANDSCAPE, nodi
        )
    return Layout(
        width, height, False, left, right, top, bottom, caption_base, TYPE_LANDSCAPE, None
    )


def text_block(
    x: float,
    y: float,
    text: str,
    *,
    size: int,
    max_chars: int,
    gap: float = 1.15,
    **kwargs: Any,
) -> tuple[str, float]:
    """svg_text plus the y where the block ends (last baseline + descent)."""
    n = len(split_lines(text, max_chars))
    svg = svg_text(x, y, text, size=size, max_chars=max_chars, line_gap=size * gap, **kwargs)
    return svg, y + (n - 1) * size * gap + size * 0.28


def pill(x: float, y: float, label: str, size: int = 38, fill: str = YELLOW,
         text_fill: str = "#111D38") -> str:  # fmt: skip
    """Rounded label centred on (x, y). Inter bold, not the old 22px mono."""
    label = label.upper()
    h = size * 1.75
    w = len(label) * size * 0.66 + size * 1.6
    return (
        f'<rect x="{x - w / 2:.1f}" y="{y - h / 2:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'rx="{h / 2:.1f}" fill="{fill}"/>'
        f'<text x="{x}" y="{y + size * 0.36:.1f}" text-anchor="middle" fill="{text_fill}" '
        f'font-family="{FONT_BODY}" font-size="{size}" font-weight="800" letter-spacing="1.5">'
        f"{esc(label)}</text>"
    )


def _series_points(
    values: list[float], x: float, y: float, w: float, h: float
) -> list[tuple[float, float]]:
    """Map numeric series into a chart box (min..max normalised to the plotting band)."""
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0
    n = len(values)
    return [
        (x + 42 + j * (w - 84) / max(1, n - 1), y + h - 75 - ((v - lo) / span) * (h - 175))
        for j, v in enumerate(values)
    ]


def _illustrative_series(i: int) -> list[float]:
    """Deterministic illustrative upward trends, used only when a spec gives no data."""
    return [0.16 + 0.12 * j + 0.11 * math.sin(j * 1.3 + i * 0.4) for j in range(6)]


def _dots(
    points: list[tuple[float, float]], color: str, r: int = 10, *, pulse_last: bool = True
) -> str:
    """Chart points; data-reveal is the fraction of the line-draw at which each appears."""
    n = len(points)
    dots = [
        f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r}" fill="{color}" '
        f'data-reveal="{j / max(1, n - 1):.3f}"/>'
        for j, (px, py) in enumerate(points)
    ]
    if dots and pulse_last:  # the newest data point keeps pulsing after the line is drawn
        dots[-1] = f'<g data-idle="pulse">{dots[-1]}</g>'
    return "".join(dots)


ICON_DIR = Path(__file__).parent / "assets" / "icons"
DEFAULT_MONTHS = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun"]


def pearson_r(a: list[float], b: list[float]) -> float:
    """Pearson correlation of two equal-length series (shown on charts; never hand-typed)."""
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    sab = sum((x - ma) * (y - mb) for x, y in zip(a, b, strict=True))
    sa = sum((x - ma) ** 2 for x in a) ** 0.5
    sb = sum((y - mb) ** 2 for y in b) ** 0.5
    return sab / (sa * sb) if sa and sb else 0.0


def available_icons() -> list[str]:
    return sorted(p.stem for p in ICON_DIR.glob("*.svg"))


@lru_cache(maxsize=64)
def icon_inner(name: str) -> str:
    path = ICON_DIR / f"{name}.svg"
    if not path.is_file():
        raise ValueError(f"unknown icon {name!r}; available: {', '.join(available_icons())}")
    text = path.read_text(encoding="utf-8")
    return re.sub(r"^.*?<svg[^>]*>|</svg>\s*$", "", text, flags=re.S).strip()


def icon(name: str, cx: float, cy: float, size: float) -> str:
    """Original F/N icon (200x200 artwork) centred on (cx, cy)."""
    s = size / 200
    return (
        f'<g data-icon="{esc(name)}" transform="translate({cx - size / 2:.1f} {cy - size / 2:.1f}) '
        f'scale({s:.4f})">{icon_inner(name)}</g>'
    )


def label_card(
    cx: float,
    y: float,
    label: str,
    width: float,
    size: int,
    accent: str,
    *,
    min_h: float = 0,
    th: Theme = THEME_DARK,
) -> tuple[str, float]:
    """Paper label card (wrapping text) whose top edge is at y; returns (svg, bottom)."""
    max_chars = max(6, int((width - 50) / (size * 0.56)))
    lines = split_lines(label, max_chars)
    h = max(min_h, len(lines) * size * 1.12 + size * 1.1)
    text_y = y + h / 2 - (len(lines) - 1) * size * 0.56 + size * 0.36
    stroke = accent if th.name == "dark" else th.card_stroke
    svg = rounded_card(
        cx - width / 2, y, width, h, th.label_fill, 0.98, stroke, 0.9, 28, th.card_stroke_width
    ) + svg_text(  # fmt: skip
        cx, text_y, label, size=size, fill="#111D38", max_chars=max_chars, line_gap=size * 1.12
    )
    return svg, y + h


def fit_size(text: str, size: int, width: float, em: float, floor: float = 0.8) -> int:
    """Largest size <= *size* (down to floor*size) at which *text* fits *width* on one line."""
    fitted = int(width / max(1, len(text)) / em)
    return max(int(size * floor), min(size, fitted))


def chart_conclusion(els: Elements, prop: dict[str, Any], x: float, y: float) -> None:
    """Optional "so what" pill for any chart template (clarity rule 8)."""
    if prop.get("conclusion"):
        th = els.theme
        els.add("conclusion", pill(x, y, str(prop["conclusion"]), els.label_size,
                                   fill=th.accent, text_fill=PAPER))  # fmt: skip


class Elements:
    """Collects template elements. Each element is one animatable unit with a data-id.

    `anim` is the element's default enter action (used when no beat targets it) and
    `seq` its default stagger order (defaults to insertion order, i.e. z-order).
    """

    def __init__(self, theme: Theme = THEME_DARK, label_size: int = 38) -> None:
        self.theme = theme
        self.label_size = label_size
        self.parts: list[str] = []
        self.seq: dict[str, float] = {}
        self.anim: dict[str, str] = {}

    def add(self, eid: str, body: str, anim: str = "pop", seq: float | None = None) -> None:
        if eid in self.seq:
            raise ValueError(f"duplicate element id {eid!r}")
        self.seq[eid] = float(len(self.seq) if seq is None else seq)
        self.anim[eid] = anim
        self.parts.append(f'<g data-id="{esc(eid)}" data-anim="{anim}">{body}</g>')

    def html(self) -> str:
        return "".join(self.parts)

    def order(self) -> list[str]:
        return sorted(self.seq, key=lambda k: self.seq[k])


def template_art(scene: SceneSpec, layout: Layout) -> Elements:
    L = layout
    T = L.type
    portrait = L.portrait
    cx, top, bottom, usable = L.cx, L.top, L.bottom, L.usable
    prop = scene.props
    template = scene.template
    els = Elements(L.th, T["label"])
    th = L.th
    muted = th.muted

    def headline_stack(
        head: str, sub: str | None, y: float, *, size: int | None = None, reserve: float = 0
    ) -> float:
        """Headline (+ optional supporting line) from y; fits above `bottom - reserve`.

        The headline steps down to HEADLINE_MIN, then the supporting line is dropped, so a
        tight band (e.g. above NODI) never overflows.
        """
        sup = T["supporting"]
        limit = bottom - reserve

        def measure(sz: int, with_sub: bool) -> float:
            lines = split_lines(head, L.chars(sz, em=0.62))
            n = len(lines)
            if max(len(x) for x in lines) * sz * DISPLAY_CAP_EM > usable:  # a single long word
                return float("inf")
            end = y + sz * 0.8 + (n - 1) * sz * 1.04 + sz * 0.28
            if with_sub and sub:
                m = len(split_lines(sub, L.chars(sup, usable * 0.9)))
                end += sup * 1.5 + (m - 1) * sup * 1.15 + sup * 0.28
            return end

        size = size or T["headline"]
        # below HEADLINE_MIN only as a last resort for one very long word
        sizes = list(range(size, min(size, HEADLINE_MIN) - 1, -6)) + list(
            range(HEADLINE_MIN - 6, 71, -6)
        )
        choice = next(((sz, True) for sz in sizes if measure(sz, True) <= limit), None)
        choice = choice or next(((sz, False) for sz in sizes if measure(sz, False) <= limit), None)
        size, with_sub = choice or (sizes[-1], False)
        svg, end = text_block(
            cx,
            y + size * 0.8,
            head,
            size=size,
            gap=1.04,
            weight=700,
            family=FONT_DISPLAY,
            max_chars=L.chars(size, em=0.62),
        )
        els.add("headline", svg, "slide")
        if sub and with_sub:
            svg, end = text_block(
                cx,
                end + sup * 1.5,
                sub,
                size=sup,
                fill=muted,
                weight=500,
                max_chars=L.chars(sup, usable * 0.9),
            )
            els.add("supporting", svg, "slide")
        return end  # fmt: skip

    if template in {"title_question", "chapter_title"}:
        y = top
        if prop.get("chapter"):  # no fallback to the scene title
            els.add("chapter", pill(cx, y + T["label"], str(prop["chapter"]), T["label"]))
            y += T["label"] * 2.6
        end = headline_stack(
            str(prop.get("headline", prop.get("title", scene.title))),
            prop.get("supporting_text"),
            y,
            reserve=70,
        )
        rule_y = end + 50
        els.add(
            "rule",
            f'<path d="M{cx - 120} {rule_y} H{cx + 120}" stroke="{th.accent}" stroke-width="12" stroke-linecap="round"/>',
            "draw",
        )
        # Concrete things on screen (clarity rule 1): two icons flanking NODI in 9:16,
        # or a row under the headline when NODI is off / in 16:9. Elements side-0, side-1.
        side = [i if isinstance(i, dict) else {"icon": str(i)} for i in prop.get("side_icons", [])][
            :2
        ]
        if side:
            if portrait and L.nodi:
                _, ny, ns = L.nodi
                size, ycen = SIDE_ICON_SIZE, ny + 150 * ns  # beside NODI's head
                xs = [L.left + size / 2 + 6, L.right - size / 2 - 6]
                label_w = size + 40
            else:
                size = max(140.0, min(260.0, (bottom - rule_y - T["node"] * 3) * 0.8))
                ycen = rule_y + 50 + size / 2
                xs = [cx - usable * 0.25, cx + usable * 0.25]
                label_w = usable * 0.45
            for i, item in enumerate(side):
                sx_ = xs[i] if len(side) == 2 else cx
                idle = "bob" if i == 0 else "sway"
                body = f'<g data-idle="{idle}">{icon(str(item["icon"]), sx_, ycen, size)}</g>'
                if item.get("trend") == "up":
                    body += icon("arrow_up", sx_ + size * 0.44, ycen - size * 0.36, size * 0.42)
                if item.get("label"):
                    svg, _ = text_block(
                        sx_,
                        ycen + size / 2 + T["node"] * 1.05,
                        str(item["label"]),
                        size=T["node"],
                        fill=th.ink,
                        weight=700,
                        max_chars=L.chars(T["node"], label_w),
                    )
                    body += svg
                els.add(f"side-{i}", body, "pop")

    elif template == "definition_card":
        term = str(prop.get("term", "Konsep"))
        definition = str(prop.get("definition", scene.purpose))
        pad = 56
        x, y, w = L.left, top + 20, usable
        term_svg, end = text_block(
            cx,
            y + pad + T["term"] * 0.8,
            term,
            size=T["term"],
            weight=700,
            fill="#111D38",
            family=FONT_DISPLAY,
            max_chars=L.chars(T["term"], w - 2 * pad, 0.6),
        )
        def_svg, end = text_block(
            cx,
            end + T["body"] * 1.6,
            definition,
            size=T["body"],
            weight=500,
            fill="#243D57",
            max_chars=L.chars(T["body"], w - 2 * pad),
        )
        card_h = end - y + pad
        els.add("card", rounded_card(x, y, w, card_h, PAPER, 0.98, YELLOW, 0.85, 40))
        els.add("term", term_svg, "slide")
        els.add("definition", def_svg, "slide")
        label_y = y + card_h + 90
        els.add("label", pill(cx, label_y, str(prop.get("data_label", "KEY IDEA")), T["label"]))  # fmt: skip
        if prop.get("icon"):  # the episode's concrete instance of the term (clarity rule 6)
            free = bottom - (label_y + T["label"] * 1.6)
            size = max(160.0, min(420.0, free - (T["node"] * 2.2 if prop.get("icon_label") else 0)))
            icy = label_y + T["label"] * 1.6 + size / 2 + 10
            body = f'<g data-idle="bob">{icon(str(prop["icon"]), cx, icy, size)}</g>'
            if prop.get("icon_label"):
                body += svg_text(
                    cx,
                    icy + size / 2 + T["node"] * 1.2,
                    str(prop["icon_label"]),
                    size=T["node"],
                    fill=th.ink,
                    weight=700,
                    max_chars=L.chars(T["node"]),
                )
            els.add("icon", body)

    elif template == "paired_trend":
        # One plot, two lines: "moving together" reads at a glance. Each line's icon rides
        # its leading point while it draws. Series are normalised separately (illustrative).
        labels = prop.get("variables", ["Variabel A", "Variabel B"])
        icons = prop.get("icons", [])
        data = prop.get("series")
        colors = [YELLOW, TEAL] if th.name == "dark" else [CORAL, TEAL]
        label_space = T["label"] * 3
        legend_row = T["node"] * 2.2
        tick = int(T["node"] * 0.8)
        x0, x1 = L.left + 30, L.right - 20
        legend_top = top + 10
        py0 = legend_top + 2 * legend_row + 90  # plot top (room for riding icons)
        py1 = bottom - label_space - tick * 2.2  # x axis
        head = T["node"] * 3.6  # riding icon size
        els.add(
            "axes",
            f'<path d="M{x0} {py0 - 40} V{py1} H{x1}" fill="none" stroke="{th.ink}" '
            'stroke-opacity=".75" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>'
            + "".join(
                f'<path data-nodraw="1" d="M{x0 + 12} {py1 - k * (py1 - py0) / 3:.1f} H{x1}" '
                f'stroke="{th.ink}" stroke-opacity=".10" stroke-width="3" stroke-dasharray="4 14" '
                'stroke-linecap="round"/>'
                for k in (1, 2, 3)
            ),
            "draw",
            seq=-1,
        )
        for i, label in enumerate(labels[:2]):
            color = colors[i]
            values = (
                [float(v) for v in data[i]] if data and i < len(data) else _illustrative_series(i)
            )
            n = len(values)
            x_labels = prop.get("x_labels") or (DEFAULT_MONTHS if not data and n == 6 else [])
            lo, hi = min(values), max(values)
            span = (hi - lo) or 1.0
            band_lo, band_hi = (
                (0.08, 0.62) if i == 0 else (0.30, 0.92)
            )  # offset so lines don't overlap
            points = [
                (
                    x0 + 70 + j * (x1 - x0 - 150) / max(1, n - 1),
                    py1 - (band_lo + (v - lo) / span * (band_hi - band_lo)) * (py1 - py0),
                )
                for j, v in enumerate(values)
            ]
            path = "M" + " L".join(f"{qx:.1f} {qy:.1f}" for qx, qy in points)
            ly = legend_top + i * legend_row + legend_row / 2
            parts = [
                # legend row: swatch line + label
                f'<path data-nodraw="1" d="M{x0 + 10} {ly} H{x0 + 90}" stroke="{color}" stroke-width="16" '
                'stroke-linecap="round"/>',
                svg_text(
                    x0 + 120,
                    ly + T["node"] * 0.36,
                    str(label),
                    size=T["node"],
                    anchor="start",
                    weight=700,
                    max_chars=L.chars(T["node"], x1 - x0 - 120),
                ),
            ]
            if i == 0:
                parts += [
                    svg_text(
                        points[j][0],
                        py1 + tick * 1.6,
                        str(xl),
                        size=tick,
                        fill=muted,
                        weight=600,
                        max_chars=8,
                    )
                    for j, xl in enumerate(x_labels[:n])
                ]
            outline = NAVY if th.name == "light" else "#0B1428"
            parts.append(
                f'<path data-series="1" d="{path}" fill="none" stroke="{outline}" stroke-width="26" '
                'stroke-linecap="round" stroke-linejoin="round" stroke-opacity=".9"/>'
            )
            parts.append(
                f'<path d="{path}" fill="none" stroke="{color}" stroke-width="14" '
                'stroke-linecap="round" stroke-linejoin="round"/>'
            )
            if i < len(icons):
                parts.append(
                    f'<g data-head="1" data-lift="{head * 0.62:.1f}">{icon(str(icons[i]), 0, 0, head)}</g>'
                )
            else:
                parts.append(
                    f'<circle data-head="1" cx="{points[0][0]:.1f}" cy="{points[0][1]:.1f}" r="20" '
                    f'fill="{color}" stroke="{outline}" stroke-width="7"/>'
                )
            els.add(f"chart-{i}", "".join(parts), "draw")  # fmt: skip
        # The chart's "so what" (clarity rule 8): a conclusion pill in the empty top-left
        # of the plot, plus Pearson r when real series are given (computed, never typed).
        if prop.get("conclusion"):
            els.add(
                "conclusion",
                pill(x0 + usable * 0.30, py0 + 10, str(prop["conclusion"]), T["label"],
                     fill=th.accent, text_fill=PAPER),
            )  # fmt: skip
        if prop.get("show_r") and data and len(data) >= 2 and len(data[0]) == len(data[1]) > 2:
            r = pearson_r([float(v) for v in data[0]], [float(v) for v in data[1]])
            els.add("r", pill(x0 + usable * 0.30, py0 + 10 + T["label"] * 2.2, f"r = {r:.2f}",
                              T["label"]))  # fmt: skip
        els.add(
            "label",
            pill(cx, bottom - T["label"], str(prop.get("data_label", "ILUSTRASI")), T["label"]),
        )

    elif template == "compare":
        # Two concepts as icon + term + one-line meaning (no text boxes).
        items = prop.get("items", [])[:2]
        vs_h = T["label"] * 2.6
        n = max(1, len(items))
        if portrait:
            slot = (bottom - top - vs_h) / n
            for i, item in enumerate(items):
                y = top + i * (slot + vs_h)
                size = min(slot * 0.56, 360)
                term_y = y + size + T["term"] * 0.95
                idle = "bob" if i == 0 else "sway"  # icons keep living after they land
                body = f'<g data-idle="{idle}">{icon(str(item.get("icon", "chart")), cx, y + size / 2 + 10, size)}</g>'
                term = str(item.get("term", ""))
                # shrink a long term to stay on one line (never below 80% of the scale)
                tsize = fit_size(term, T["term"], usable * 0.96, DISPLAY_CAP_EM)
                term_svg, term_end = text_block(
                    cx, term_y, term, size=tsize, weight=700, family=FONT_DISPLAY,
                    max_chars=L.chars(tsize, usable * 0.96, DISPLAY_CAP_EM), gap=1.02,
                )  # fmt: skip
                body += term_svg
                d_svg, _ = text_block(
                    cx,
                    term_end + T["body"] * 1.3,
                    str(item.get("definition", "")),
                    size=T["body"],
                    fill=th.ink,  # content, not secondary (clarity rule 9)
                    weight=600,
                    max_chars=L.chars(T["body"], usable * 0.92),
                )
                els.add(f"side-{i}", body + d_svg, "pop" if i == 0 else "slide")
            vy = top + slot + vs_h / 2
        else:
            col = (usable - 120) / n
            for i, item in enumerate(items):
                ccx = L.left + col / 2 + i * (col + 120)
                size = min(col * 0.42, (bottom - top) * 0.42)
                term_y = top + size + T["term"]
                idle = "bob" if i == 0 else "sway"
                body = f'<g data-idle="{idle}">{icon(str(item.get("icon", "chart")), ccx, top + size / 2, size)}</g>'
                term = str(item.get("term", ""))
                # shrink a long term to stay on one line (never below 80% of the scale)
                tsize = fit_size(term, T["term"], col, DISPLAY_CAP_EM)
                term_svg, term_end = text_block(
                    ccx, term_y, term, size=tsize, weight=700, family=FONT_DISPLAY,
                    max_chars=L.chars(tsize, col, DISPLAY_CAP_EM), gap=1.02,
                )  # fmt: skip
                body += term_svg
                d_svg, _ = text_block(
                    ccx,
                    term_end + T["body"] * 1.3,
                    str(item.get("definition", "")),
                    size=T["body"],
                    fill=th.ink,
                    weight=600,
                    max_chars=L.chars(T["body"], col),
                )
                els.add(f"side-{i}", body + d_svg, "pop" if i == 0 else "slide")
            vy = (top + bottom) / 2
        if len(items) == 2:
            els.add("vs", pill(cx, vy, str(prop.get("divider", "VS")), T["label"], fill=th.accent,
                               text_fill=PAPER), seq=0.5)  # fmt: skip

    elif template == "causal_diagram":
        nodes = prop.get(
            "nodes",
            [
                {"id": "z", "label": "Faktor ketiga"},
                {"id": "x", "label": "Variabel A"},
                {"id": "y", "label": "Variabel B"},
            ],
        )[:3]
        label_space = T["label"] * 3
        with_icons = any(n.get("icon") for n in nodes)
        node_w = usable * (0.47 if portrait else 0.34)
        zone_bottom = bottom - label_space
        if with_icons:
            top_icon = (zone_bottom - top) * (0.30 if portrait else 0.36)
            low_icon = top_icon * (0.95 if portrait else 0.86)
            centers = [
                (cx, top + top_icon / 2 + 10, top_icon),
                (L.left + node_w / 2, top + (zone_bottom - top) * 0.62, low_icon),
                (L.right - node_w / 2, top + (zone_bottom - top) * 0.62, low_icon),
            ]
        else:
            box_h = T["node"] * 4.6
            centers = [
                (cx, top + 40 + box_h / 2, box_h),
                (L.left + node_w / 2, top + (zone_bottom - top) * 0.62, box_h),
                (L.right - node_w / 2, top + (zone_bottom - top) * 0.62, box_h),
            ]
        bodies: list[tuple[str, float, float]] = []  # (svg, top_y, bottom_y)
        for idx, node in enumerate(nodes):
            ncx, ncy, size = centers[idx]
            label = str(node.get("label", "Node"))
            accent = YELLOW if idx == 0 else "#FFFFFF"
            if with_icons:
                ico = icon(str(node["icon"]), ncx, ncy, size) if node.get("icon") else ""
                card_svg, card_bottom = label_card(
                    ncx, ncy + size / 2 + 18, label, node_w, T["node"], accent, th=th
                )
                bodies.append((ico + card_svg, ncy - size / 2, card_bottom))
            else:
                card_svg, card_bottom = label_card(
                    ncx, ncy - size / 2, label, node_w, T["node"], accent, min_h=size, th=th
                )
                bodies.append((card_svg, ncy - size / 2, card_bottom))
        sy = bodies[0][2] + 14
        # Arrows are drawn first (behind the nodes) but animate after their source node.
        # Each arrow leaves from its own side of the cause so two arrows read as two causes.
        for k in range(1, len(bodies)):
            ex, ey = centers[k][0], bodies[k][1] - 14
            sx = cx + (-1 if centers[k][0] < cx else 1) * node_w * 0.22
            els.add(
                f"arrow-{k}",
                f'<path d="M{sx} {sy} L{ex} {ey}" '
                f'fill="none" stroke="{th.line}" stroke-width="10" stroke-linecap="round"/>'
                f'<path d="M{ex - 18} {ey - 22} L{ex} {ey} L{ex + 18} {ey - 22}" fill="none" '
                f'stroke="{th.line}" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>',
                "draw",
                seq=2 * k - 1,
            )
        if prop.get("false_link") and len(bodies) == 3:
            # The link the viewer assumed (A -> B) is shown first, then crossed out on a beat
            # (clarity rule 5). Elements: false-link (draw), false-x (pop).
            ly = centers[1][1]
            lx0 = centers[1][0] + centers[1][2] * 0.55
            lx1 = centers[2][0] - centers[2][2] * 0.55
            els.add(
                "false-link",
                f'<path d="M{lx0:.1f} {ly:.1f} H{lx1:.1f}" stroke="{th.line}" stroke-width="10" '
                'stroke-dasharray="20 16" stroke-linecap="round" stroke-opacity=".8"/>',
                "draw",
                seq=-0.5,
            )
            mx = (lx0 + lx1) / 2
            els.add(
                "false-x",
                f'<circle cx="{mx:.1f}" cy="{ly:.1f}" r="46" fill="{CORAL}" stroke="#111D38" stroke-width="7"/>'
                f'<path d="M{mx - 18:.1f} {ly - 18:.1f} L{mx + 18:.1f} {ly + 18:.1f} M{mx + 18:.1f} {ly - 18:.1f} '
                f'L{mx - 18:.1f} {ly + 18:.1f}" stroke="{PAPER}" stroke-width="11" stroke-linecap="round"/>',
                "pop",
                seq=-0.4,
            )
        for idx, (body, _, _) in enumerate(bodies):
            if idx == 0 and not with_icons:  # the hidden cause breathes (icons idle on their own)
                body = f'<g data-idle="pulse">{body}</g>'
            els.add(f"node-{idx}", body, seq=0 if idx == 0 else 2 * idx)
        els.add(
            "label",
            pill(
                cx, bottom - T["label"], str(prop.get("data_label", "MODEL KONSEPTUAL")), T["label"]
            ),
            seq=10,
        )

    elif template == "question_link" and portrait:
        # 9:16: a vertical chain A ↓ ? ↓ B fills the tall canvas.
        items = [
            i if isinstance(i, dict) else {"label": str(i)}
            for i in prop.get("labels", ["A", "?", "B"])
        ][:3]
        sup_text = prop.get("supporting_text")
        sup = T["supporting"]
        arrow_h, label_h = 110, T["node"] * 1.7
        sup_h = sup * 2.6 if sup_text else 0
        n = len(items)
        labels_h = sum(label_h for it in items if it.get("label") and it.get("icon"))
        box = min(340.0, (bottom - top - sup_h - (n - 1) * arrow_h - labels_h) / n)
        total = n * box + (n - 1) * arrow_h + labels_h + sup_h
        y = top + max(0.0, (bottom - top - total) / 2)
        for i, item in enumerate(items):
            x = cx - box / 2
            fill = YELLOW if i == 1 else "#FFFFFF"
            body = ""
            if item.get("icon"):  # icons stand on their own: no box behind them
                body += icon(str(item["icon"]), cx, y + box / 2, box * (1.0 if i == 1 else 1.08))
            else:
                body += theme_card(th, x, y, box, box, radius=44, accent=fill if i == 1 else None)
                body += svg_text(
                    cx,
                    y + box / 2 + T["headline"] * 0.3,
                    str(item.get("label", "")),
                    size=int(T["headline"] * 0.8),
                    fill=th.ink,
                    weight=700,
                    family=FONT_DISPLAY,
                    max_chars=8,
                )
            y += box
            if item.get("label") and item.get("icon"):
                body += svg_text(
                    cx,
                    y + label_h * 0.72,
                    str(item["label"]),
                    size=T["node"],
                    max_chars=L.chars(T["node"]),
                )
                y += label_h
            els.add(f"item-{i}", body)
            if i < n - 1:
                a0, a1 = y + 16, y + arrow_h - 16
                els.add(
                    f"link-{i}",
                    f'<path d="M{cx} {a0} V{a1}" stroke="{th.line}" stroke-width="12" stroke-linecap="round"/>'
                    f'<path d="M{cx - 24} {a1 - 26} L{cx} {a1} L{cx + 24} {a1 - 26}" fill="none" '
                    f'stroke="{th.line}" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/>',
                    "draw",
                )
                y += arrow_h
        if sup_text:
            svg, _ = text_block(
                cx,
                y + sup * 1.6,
                str(sup_text),
                size=sup,
                fill=muted,
                max_chars=L.chars(sup, usable * 0.9),
            )
            els.add("supporting", svg, "slide")  # fmt: skip

    elif template == "question_link":
        items = [
            i if isinstance(i, dict) else {"label": str(i)}
            for i in prop.get("labels", ["A", "?", "B"])
        ][:3]
        box_w = min(usable * 0.27, 300)
        gap = (usable - 3 * box_w) / 2
        y = top + (260 if portrait else 100)
        below = y + box_w
        for i, item in enumerate(items):
            x = L.left + i * (box_w + gap)
            fill = YELLOW if i == 1 else "#FFFFFF"
            text_fill = NAVY if i == 1 else th.ink
            body = (
                f'<rect x="{x}" y="{y}" width="{box_w}" height="{box_w}" rx="40" fill="{fill}" '
                f'fill-opacity="{1 if i == 1 else 0.10}" stroke="{fill}" stroke-opacity=".75" stroke-width="4"/>'
            )
            if item.get("icon"):
                body += icon(str(item["icon"]), x + box_w / 2, y + box_w / 2, box_w * 0.74)
                if item.get("label"):
                    svg, end = text_block(
                        x + box_w / 2,
                        y + box_w + T["node"] * 1.3,
                        str(item["label"]),
                        size=T["node"],
                        max_chars=L.chars(T["node"], box_w + gap * 0.8),
                    )
                    body += svg
                    below = max(below, end)
            else:
                body += svg_text(
                    x + box_w / 2,
                    y + box_w / 2 + T["headline"] * 0.3,
                    str(item.get("label", "")),
                    size=int(T["headline"] * 0.8),
                    fill=text_fill,
                    weight=700,
                    family=FONT_DISPLAY,
                    max_chars=8,
                )
            els.add(f"item-{i}", body)
            if i < len(items) - 1:
                els.add(
                    f"link-{i}",
                    svg_text(
                        x + box_w + gap / 2,
                        y + box_w / 2 + 20,
                        "→",
                        size=64,
                        fill=YELLOW,
                        max_chars=4,
                    ),
                    "slide",
                )
        svg, _ = text_block(
            cx,
            below + T["supporting"] * 2.2,
            str(prop.get("supporting_text", "Hubungan belum tentu sebab-akibat")),
            size=T["supporting"],
            fill=muted,
            max_chars=L.chars(T["supporting"], usable * 0.9),
        )
        els.add("supporting", svg, "slide")  # fmt: skip

    elif template == "line_chart":
        label_space = T["label"] * 3
        x0, x1 = L.left + 50, L.right - 50
        y_top, y0 = top + 80, bottom - label_space - 60
        chart_w, chart_h = x1 - x0, y0 - y_top
        grid = "".join(
            f'<path data-nodraw="1" d="M{x0} {y0 - i * chart_h / 3:.1f} H{x1}" '
            f'stroke="{th.ink}" stroke-opacity=".14" stroke-width="2"/>'
            for i in range(4)
        )
        if prop.get("values"):
            values = [float(v) for v in prop["values"]]
        else:
            values = [0.18 + 0.58 * (0.5 + 0.5 * math.sin(j * 1.1)) for j in range(8)]
        lo, hi = min(values), max(values)
        span = (hi - lo) or 1.0
        n = len(values)
        points = [
            (x0 + j * chart_w / max(1, n - 1), y0 - chart_h * (0.1 + 0.8 * (v - lo) / span))
            for j, v in enumerate(values)
        ]
        path = "M" + " L".join(f"{px:.1f} {py:.1f}" for px, py in points)
        els.add(
            "chart",
            theme_card(th, L.left, top, usable, bottom - label_space - top, radius=34)
            + grid
            + f'<path d="{path}" fill="none" stroke="{YELLOW}" stroke-width="12" '
            'stroke-linecap="round" stroke-linejoin="round"/>' + _dots(points, YELLOW, r=13),
            "draw",
        )
        chart_conclusion(els, prop, x0 + chart_w * 0.32, y_top + 20)
        els.add(
            "label",
            pill(cx, bottom - T["label"], str(prop.get("data_label", "ILUSTRASI")), T["label"]),
        )

    elif template == "scatter_regression":
        label_space = T["label"] * 3
        x0, x1 = L.left + 60, L.right - 50
        y_top, y0 = top + 60, bottom - label_space - 60
        chart_w, chart_h = x1 - x0, y0 - y_top
        pts = "".join(
            f'<circle cx="{x0 + 35 + ((i * 73) % int(max(80, chart_w - 70)))}" '
            f'cy="{y0 - 25 - ((i * 47 + (i % 5) * 21) % int(max(90, chart_h - 50)))}" r="13" '
            f'fill="{BLUE if i % 3 else YELLOW}" opacity=".9" data-reveal="{i / 27:.3f}"/>'
            for i in range(28)
        )
        els.add(
            "chart",
            theme_card(th, L.left, top, usable, bottom - label_space - top, radius=34)
            + f'<path d="M{x0} {y_top} V{y0} H{x1}" fill="none" stroke="{th.ink}" stroke-opacity=".6" stroke-width="4"/>'
            + pts,
            "draw",
        )
        els.add(
            "trend",
            f'<path d="M{x0 + 15} {y0 - 65} L{x1 - 15} {y_top + 50}" stroke="{CORAL}" stroke-width="9" stroke-linecap="round"/>',
            "draw",
        )
        chart_conclusion(els, prop, x0 + (x1 - x0) * 0.32, y_top + 30)
        els.add("label", pill(cx, bottom - T["label"], "ILUSTRASI • TANPA ANGKA KLAIM", T["label"]))

    elif template == "takeaway":
        default_points = [
            "Pahami pola yang terlihat",
            "Uji penjelasan alternatif",
            "Cari bukti yang relevan",
        ]
        points = prop.get("points", default_points)[:4]
        gap = 36
        y0 = top + 40
        limit = (L.nodi[1] - 40) if (portrait and L.nodi) else bottom
        n = max(1, len(points))
        card_h = min(T["body"] * 4.6, (limit - y0 - gap * (n - 1)) / n)
        # centre the stack in the free band (slightly above centre reads better)
        y0 += max(0.0, (limit - y0 - (n * card_h + gap * (n - 1))) * 0.42)
        num_r = T["number"] * 0.95
        text_x0 = L.left + 40 + 2 * num_r + 32
        for i, point in enumerate(points):
            y = y0 + i * (card_h + gap)
            lines = len(split_lines(str(point), L.chars(T["body"], L.right - text_x0 - 40)))
            ty = y + card_h / 2 - (lines - 1) * T["body"] * 0.58 + T["body"] * 0.35
            els.add(
                f"point-{i}",
                theme_card(th, L.left, y, usable, card_h, radius=30)
                # number badge keeps a gentle pulse so text-only scenes never freeze
                + '<g data-idle="pulse">'
                + f'<circle cx="{L.left + 40 + num_r}" cy="{y + card_h / 2}" r="{num_r}" fill="{YELLOW}"/>'
                + svg_text(L.left + 40 + num_r, y + card_h / 2 + T["number"] * 0.36, str(i + 1),
                           size=T["number"], fill="#111D38", weight=800, max_chars=3)
                + "</g>"
                + svg_text(text_x0, ty, str(point), size=T["body"], anchor="start",
                           max_chars=L.chars(T["body"], L.right - text_x0 - 40), line_gap=T["body"] * 1.16),
                "slide",
            )  # fmt: skip

    elif template == "follow_cta":
        els.add("badge", pill(cx, top + T["label"], "NEXT UP", T["label"]))
        end = headline_stack(
            str(prop.get("headline", "Lanjutkan eksplorasi")),
            str(prop.get("supporting_text", "Ikuti F/N untuk belajar lebih dalam")),
            top + T["label"] * 2.6,
            size=int(T["headline"] * 0.85),
        )
        btn_y, bw, bh = end + 80, T["label"] * 15, T["label"] * 2.2
        els.add(
            "button",
            f'<rect x="{cx - bw / 2}" y="{btn_y}" width="{bw}" height="{bh}" rx="{bh / 2}" fill="{YELLOW}"/>'
            + svg_text(
                cx,
                btn_y + bh / 2 + T["label"] * 0.36,
                "F/N  •  FOLLOW FOR MORE",
                size=T["label"],
                fill="#111D38",
                weight=800,
                max_chars=40,
            ),
        )

    else:
        # Generic scene fallback keeps the template registry extensible.
        els.add("badge", pill(cx, top + T["label"], scene.title, T["label"]))
        headline_stack(scene.title, scene.purpose, top + T["label"] * 2.6)

    return els


DEFAULT_STAGGER = 0.15
DEFAULT_FIRST = 0.15
ACTION_SECONDS = {
    "pop": 0.35,
    "slide": 0.45,
    "draw": 0.8,
    "count": 0.9,
    "highlight": 0.5,
    "exit": 0.3,
}


def animation_plan(
    els: Elements,
    beats: list[dict[str, Any]],
    *,
    pose: str,
    expression: str,
) -> dict[str, Any]:
    """Per-element enter/highlight/exit schedule plus the NODI pose/expression timeline.

    Elements with an enter beat (pop/slide/draw/count) use it; the rest enter on a default
    stagger in their `seq` order. Unknown targets are an authoring error.
    """
    known = set(els.seq)
    plan: dict[str, dict[str, Any]] = {eid: {"highlights": [], "exit": None} for eid in els.order()}
    poses = [{"t": 0.0, "value": pose}]
    exprs = [{"t": 0.0, "value": expression}]
    for beat in beats:
        target, action, t = beat["target"], beat["action"], float(beat["t"])
        if target == "nodi":
            kind, value = action.split(":", 1)
            (poses if kind == "pose" else exprs).append({"t": t, "value": value})
            continue
        if target not in known:
            raise ValueError(
                f"beat target {target!r} is not an element of this template; "
                f"available: {', '.join(els.order())}"
            )
        dur = float(beat.get("duration") or ACTION_SECONDS[action])
        entry = plan[target]
        if action in ("pop", "slide", "draw", "count"):
            if "enter" not in entry:  # first enter beat wins
                entry["enter"] = {"t": t, "action": action, "dur": dur}
        elif action == "highlight":
            entry["highlights"].append({"t": t, "dur": dur})
        else:
            entry["exit"] = {"t": t, "dur": dur}
    k = 0
    for eid in els.order():
        if "enter" not in plan[eid]:
            action = els.anim[eid]
            plan[eid]["enter"] = {
                "t": DEFAULT_FIRST + k * DEFAULT_STAGGER,
                "action": action,
                "dur": ACTION_SECONDS[action],
            }
            k += 1
    return {
        "elements": [{"id": eid, **plan[eid]} for eid in els.order()],
        "nodi_pose": sorted(poses, key=lambda p: p["t"]),
        "nodi_expression": sorted(exprs, key=lambda p: p["t"]),
    }


def decor_layer(width: int, height: int, th: Theme = THEME_DARK) -> str:
    """Clean ambient background: a few large soft colour fields plus small crisp marks.

    Everything drifts on its own seeded ellipse (data-drift), as a pure function of t.
    """
    rng = np.random.default_rng(1729)
    out = []
    span = min(width, height)
    for i in range(4):  # large soft colour fields
        ax, ay = rng.uniform(70, 130), rng.uniform(70, 130)
        w, ph = rng.uniform(0.35, 0.6), rng.uniform(0, 2 * math.pi)
        out.append(
            f'<circle cx="{width * (0.12 + 0.28 * i):.0f}" cy="{height * (0.18 + 0.22 * ((i * 3) % 4)):.0f}" '
            f'r="{span * (0.30 + 0.05 * (i % 2)):.0f}" fill="{th.blobs[i % len(th.blobs)]}" '
            f'opacity="{th.blob_opacity}" filter="url(#blobBlur)" data-drift="{ax:.1f},{ay:.1f},{w:.3f},{ph:.3f}"/>'
        )
    for i in range(6):  # small crisp editorial marks (plus signs / rings)
        ax, ay = rng.uniform(20, 45), rng.uniform(20, 45)
        w, ph = rng.uniform(0.4, 0.8), rng.uniform(0, 2 * math.pi)
        x = width * (0.08 + 0.84 * ((i * 0.37) % 1))
        y = height * (0.06 + 0.70 * ((i * 0.61) % 1))
        mark = (
            f'<path d="M{x - 14:.0f} {y:.0f}H{x + 14:.0f}M{x:.0f} {y - 14:.0f}V{y + 14:.0f}" '
            if i % 2 == 0
            else f'<circle cx="{x:.0f}" cy="{y:.0f}" r="13" fill="none" '
        )
        out.append(
            mark
            + f'stroke="{th.ink}" stroke-opacity=".16" stroke-width="5" stroke-linecap="round" '
            f'data-drift="{ax:.1f},{ay:.1f},{w:.3f},{ph:.3f}"/>'
        )
    return "".join(out)


GRAIN_TILES = 3
GRAIN_SIZE = 256
GRAIN_OPACITY = 0.3


@lru_cache(maxsize=1)
def grain_tiles() -> tuple[str, ...]:
    """Deterministic noise tiles (seeded numpy) as PNG data URIs."""
    rng = np.random.default_rng(20261120)
    uris = []
    for _ in range(GRAIN_TILES):
        noise = rng.normal(128, 42, (GRAIN_SIZE, GRAIN_SIZE)).clip(0, 255).astype(np.uint8)
        buf = io.BytesIO()
        Image.fromarray(noise).save(buf, format="PNG", optimize=True)
        uris.append("data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii"))
    return tuple(uris)


def grain_layer(width: int, height: int, opacity: float = GRAIN_OPACITY) -> str:
    patterns = "".join(
        f'<pattern id="grain-{i}" width="{GRAIN_SIZE}" height="{GRAIN_SIZE}" patternUnits="userSpaceOnUse">'
        f'<image href="{uri}" width="{GRAIN_SIZE}" height="{GRAIN_SIZE}"/></pattern>'
        for i, uri in enumerate(grain_tiles())
    )
    rects = "".join(
        f'<rect data-grain="{i}" width="{width}" height="{height}" fill="url(#grain-{i})" '
        f'opacity="{opacity}" style="mix-blend-mode:overlay" visibility="{"visible" if i == 0 else "hidden"}"/>'
        for i in range(GRAIN_TILES)
    )
    return f'<defs>{patterns}</defs><g id="grain" pointer-events="none">{rects}</g>'


FONT_DIR = Path(__file__).parent / "assets" / "fonts"
FONT_DISPLAY = "Space Grotesk, sans-serif"
FONT_BODY = "Inter, sans-serif"
FONT_MONO = "IBM Plex Mono, monospace"
# Unmodified OFL font files (see assets/fonts/README.md). Embedded as data URIs because
# scene pages are loaded with set_content (about:blank), where file:// URLs are blocked.
FONT_FACES = (
    ("Space Grotesk", "SpaceGrotesk[wght].ttf", "300 700"),
    ("Inter", "Inter[opsz,wght].ttf", "100 900"),
    ("IBM Plex Mono", "IBMPlexMono-Regular.ttf", "400"),
    ("IBM Plex Mono", "IBMPlexMono-Bold.ttf", "700"),
)


@lru_cache(maxsize=1)
def font_face_css() -> str:
    rules = []
    for family, filename, weight in FONT_FACES:
        data = base64.b64encode((FONT_DIR / filename).read_bytes()).decode("ascii")
        rules.append(
            f"@font-face{{font-family:'{family}';src:url(data:font/ttf;base64,{data}) "
            f"format('truetype');font-weight:{weight};font-display:block}}"
        )
    return "".join(rules)


CAPTION_MIN_SIZE = 46
CAPTION_MAX_WORDS = 5


def caption_fit(text: str, layout: Layout) -> tuple[int, list[str]]:
    """Caption size and lines: shrink (down to CAPTION_MIN_SIZE) to stay on one line."""
    size = layout.type["caption"]
    while size > CAPTION_MIN_SIZE and len(text) > layout.chars(size, em=0.55):
        size -= 2
    return size, split_lines(text, layout.chars(size, em=0.55))


def caption_warnings(spec: EpisodeSpec) -> list[str]:
    """Authoring lint: portrait captions should be short single-line chunks."""
    warnings: list[str] = []
    layout = compute_layout(spec.meta.width, spec.meta.height, False)
    for scene in spec.scenes:
        for i, cap in enumerate(scene.captions):
            words = len(cap.text.split())
            _, lines = caption_fit(cap.text, layout)
            if layout.portrait and words > CAPTION_MAX_WORDS:
                warnings.append(
                    f"{scene.id} caption {i}: {words} words (max {CAPTION_MAX_WORDS}) — split it"
                )
            if len(lines) > 1:
                warnings.append(
                    f"{scene.id} caption {i}: wraps to {len(lines)} lines — shorten or split"
                )
    return warnings


EXPLANATION_TEMPLATES = {
    "paired_trend",
    "line_chart",
    "scatter_regression",
    "causal_diagram",
    "definition_card",
}


def character_warnings(spec: EpisodeSpec) -> list[str]:
    """Authoring lint for NODI staging (portrait: NODI is a full-size performer)."""
    if spec.meta.height <= spec.meta.width:
        return []
    out = []
    for scene in spec.scenes:
        if scene.character.mascot != "on":
            continue
        if scene.template in EXPLANATION_TEMPLATES:
            out.append(
                f"{scene.id}: NODI on in an explanation scene ({scene.template}) — turn it off so the material is full-screen"
            )
        if scene.background in {"navy", "navy_dark"}:
            out.append(
                f"{scene.id}: NODI on a navy background — prefer purple/teal/coral (rim outline is the fallback)"
            )
    return out


def highlight_line(line: str, highlighted: list[str]) -> str:
    """Escape a caption line and mark highlighted phrases (navy ink on a highlighter swipe)."""
    if not highlighted:
        return esc(line)
    ordered = sorted(highlighted, key=len, reverse=True)
    pattern = re.compile("(" + "|".join(re.escape(h) for h in ordered) + ")", re.IGNORECASE)
    folded = {h.casefold() for h in highlighted}
    return "".join(
        f'<tspan data-hl="1" fill="{NAVY}" stroke="none" font-weight="900">{esc(part)}</tspan>'
        if part.casefold() in folded
        else esc(part)
        for part in pattern.split(line)
    )


def build_scene_html(
    spec: EpisodeSpec, scene: SceneSpec, timing_scene: dict[str, Any], timing: dict[str, Any]
) -> str:
    width, height = spec.meta.width, spec.meta.height
    bg = SCENE_BACKGROUNDS.get(scene.background, SCENE_BACKGROUNDS["navy"])
    portrait = height > width
    cx = width / 2
    brand_size = 28 if portrait else 24
    mascot_on = scene.character.mascot == "on"
    # NODI steps down a size when concrete icons stand beside it (9:16 side_icons).
    side_scale = NODI_SIDE_SCALE if (scene.props.get("side_icons") and height > width) else None
    layout = compute_layout(width, height, mascot_on, scene.background, side_scale)
    th = layout.th
    els = template_art(scene, layout)
    art = els.html()
    plan = animation_plan(
        els,
        timing_scene.get("beats", []),
        pose=NODI_POSE_MAP.get(scene.character.mascot_pose or "rest", "rest"),
        expression=NODI_EXPRESSION_MAP.get(scene.character.expression or "neutral", "neutral"),
    )
    nodi = ""
    nodi_state = {}
    index = next((i for i, s in enumerate(spec.scenes) if s.id == scene.id), 0)
    if layout.nodi:
        nx, ny, scale = layout.nodi
        nodi = nodi_layer(nx, ny, scale, rim=scene.background in DARK_BACKGROUNDS)
        nodi_state = {
            "pose": NODI_POSE_MAP.get(scene.character.mascot_pose or "rest", "rest"),
            "expression": NODI_EXPRESSION_MAP.get(
                scene.character.expression or "neutral", "neutral"
            ),
            # varies the talking-gesture schedule from scene to scene (still deterministic)
            "gestureSeed": index,
            # slide in/out only when the neighbouring scene has no NODI
            "enter": index == 0 or spec.scenes[index - 1].character.mascot != "on",
            "exit": index == len(spec.scenes) - 1
            or spec.scenes[index + 1].character.mascot != "on",
            "duration": float(timing_scene.get("duration_seconds", 0) or 0),
            "slide": float(height - ny),
        }
    caps = []
    for idx, cap in enumerate(timing_scene.get("captions", [])):
        cap_size, lines = caption_fit(str(cap["text"]), layout)
        highlighted = [str(h) for h in cap.get("highlight", []) if str(h)]
        gap = cap_size * 1.12
        first = layout.caption_base - (len(lines) - 1) * gap  # grows upward, never into the UI zone
        tspans = "".join(
            f'<tspan x="{cx}" dy="{0 if i == 0 else gap}">{highlight_line(line, highlighted)}</tspan>'
            for i, line in enumerate(lines)
        )
        # Borderless caption. Dark scenes: light text with a dark outline. Light scenes: navy
        # ink. Highlighted words get a highlighter swipe (rects positioned by render()).
        n_hl = tspans.count("data-hl=")
        swipes = "".join(
            f'<rect data-hl-rect="1" rx="10" fill="{th.highlight}" width="0" height="0"/>'
            for _ in range(n_hl)
        )
        outline = (
            f'stroke="{th.caption_stroke}" stroke-width="{cap_size * 0.2:.1f}" stroke-linejoin="round" '
            'paint-order="stroke" '
            if th.caption_stroke
            else ""
        )
        caps.append(
            f'<g id="caption-{idx}" opacity="0">{swipes}<text x="{cx}" y="{first:.1f}" text-anchor="middle" '
            f'fill="{th.ink}" {outline}font-family="{FONT_BODY}" font-size="{cap_size}" font-weight="800" '
            f'letter-spacing="-.5">{tspans}</text></g>'
        )
    captions_json = json.dumps(timing_scene.get("captions", []), ensure_ascii=False)
    # deterministic decor: no wall clock, no CSS animation, all movement comes from render(t).
    decor = decor_layer(width, height, th)
    grain = grain_layer(width, height, th.grain_opacity)
    grid_cell = (
        '<circle cx="36" cy="36" r="2.4" fill="#111D38" fill-opacity=".10"/>'
        if th.name == "light"
        else '<path d="M72 0H0V72" fill="none" stroke="#FFFFFF" stroke-opacity=".035" stroke-width="1"/>'
    )
    mascot_layer = nodi
    nodi_js = NODI_RIG_JS if layout.nodi else ""
    nodi_state_json = json.dumps(nodi_state)
    plan_json = json.dumps(plan)
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
      html,body{{margin:0;width:{width}px;height:{height}px;background:{bg};overflow:hidden}}
      svg{{display:block;width:{width}px;height:{height}px}}
      text{{font-synthesis:none}}
      .fn-accent{{fill:{th.accent}}}
      {font_face_css()}
    </style></head><body><svg id="frame" xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" color="{th.ink}">
      <defs>
        <radialGradient id="bgGlow" cx="50%" cy="42%" r="75%" gradientUnits="objectBoundingBox"><stop offset="0" stop-color="#FFFFFF" stop-opacity=".10"/><stop offset="1" stop-color="#000000" stop-opacity=".10"/></radialGradient>
        <pattern id="grid" width="72" height="72" patternUnits="userSpaceOnUse" patternTransform="translate(0 0)">{grid_cell}</pattern>
        <filter id="blobBlur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="40"/></filter>
        <filter id="softShadow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="18"/></filter>
        <filter id="nodiRim" x="-10%" y="-10%" width="120%" height="120%"><feMorphology in="SourceAlpha" operator="dilate" radius="9" result="d"/><feFlood flood-color="#F4F1E8" flood-opacity=".92"/><feComposite in2="d" operator="in" result="rim"/><feMerge><feMergeNode in="rim"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      </defs>
      <rect width="100%" height="100%" fill="{bg}"/><rect width="100%" height="100%" fill="url(#bgGlow)"/><rect width="100%" height="100%" fill="url(#grid)"/>
      <g id="decor">{decor}</g>
      <text id="brand" x="{width - 56}" y="{brand_size + 60}" text-anchor="end" fill="{th.ink}" opacity=".5" font-family="Space Grotesk, sans-serif" font-size="{brand_size + 10}" font-weight="700" letter-spacing="1">F/N</text>
      <g id="scene-art">{art}</g>
      <g id="mascot-layer" opacity="0">{mascot_layer}</g>
      {"".join(caps)}
      {grain}
    </svg>
    <script>{nodi_js}</script>
    <script>
    // Scoped: Playwright set_content reuses the same window across scenes, so top-level
    // const declarations would collide and silently keep the previous scene's render().
    (() => {{
      const captions = {captions_json};
      const mascotEnabled = {str(mascot_on).lower()};
      const nodiState = {nodi_state_json};
      const holder = document.getElementById('nodi-holder');
      const nodi = (mascotEnabled && holder && window.NODI) ? window.NODI.mount(holder) : null;
      const ENERGY = {{smile:0, none:0, small:.3, mid:.6, o:.5, wide:.9}};
      const plan = {plan_json};
      const clamp = (v) => Math.max(0, Math.min(1, v));
      const smooth = (v) => {{v=clamp(v);return v*v*(3-2*v)}};
      const easeOut = (v) => 1 - Math.pow(1 - clamp(v), 3);
      const easeBack = (v) => {{v=clamp(v);const c1=1.70158,c3=c1+1;return 1+c3*Math.pow(v-1,3)+c1*Math.pow(v-1,2)}};
      const nodes = plan.elements.map((e) => [e, document.querySelector(`[data-id="${{CSS.escape(e.id)}}"]`)]);
      const strokeLen = (p) => {{ try {{ return p.getTotalLength(); }} catch (err) {{ return 0; }} }};
      const fmtCount = (v, dec) => Number(v).toLocaleString('id-ID', {{minimumFractionDigits: dec, maximumFractionDigits: dec}});
      // Timeline value active at time t (sorted [{{t, value}}]) and when it started.
      const at = (track, t) => {{ let cur = track[0], prev = track[0]; for (const k of track) {{ if (k.t <= t) {{ prev = cur; cur = k; }} }} return [cur, prev]; }};

      function animateElement(e, node, t) {{
        const en = e.enter, p = clamp((t - en.t) / en.dur);
        let opacity = t < en.t ? 0 : 1, scale = 1, dy = 0;
        if (en.action === 'pop') {{ scale = t < en.t ? 0 : Math.max(0, easeBack(p)); opacity = clamp(p * 4); }}
        else if (en.action === 'slide') {{ opacity = easeOut(p); dy = (1 - easeOut(p)) * 70; }}
        // draw: strokes are drawn on; fills/text fade in quickly; chart points follow the line
        const drawP = en.action === 'draw' ? easeOut(p) : (t < en.t ? 0 : 1);
        node.querySelectorAll('path:not([data-nodraw]):not([data-icon] path)').forEach((path) => {{
          const len = strokeLen(path);
          if (len > 0) {{ path.style.strokeDasharray = `${{len}}`; path.style.strokeDashoffset = String(len * (1 - drawP)); }}
        }});
        if (en.action === 'draw') {{
          node.querySelectorAll(':scope > rect, :scope > text').forEach((x) => x.setAttribute('opacity', clamp(p * 3)));
        }}
        node.querySelectorAll('[data-head]').forEach((h) => {{
          const series = h.parentNode.querySelector('[data-series]'), len = series ? strokeLen(series) : 0;
          if (len > 0) {{
            const pt = series.getPointAtLength(len * drawP);
            if (h.tagName === 'circle') {{ h.setAttribute('cx', pt.x); h.setAttribute('cy', pt.y); h.setAttribute('r', 20 + (drawP >= 1 ? 3 * Math.sin(t * 4) : 0)); }}
            else {{
              const lift = Number(h.dataset.lift || 0), bob = drawP >= 1 ? Math.sin(t * 3.2) * 6 : 0;
              h.setAttribute('transform', `translate(${{pt.x}} ${{pt.y - lift + bob}}) rotate(${{drawP < 1 ? Math.sin(t * 9) * 6 : 0}})`);
            }}
          }}
        }});
        node.querySelectorAll('[data-reveal]').forEach((c) => c.setAttribute('opacity', smooth((drawP - Number(c.dataset.reveal)) / 0.08 + 1)));
        node.querySelectorAll('[data-count]').forEach((x) => {{
          const target = Number(x.dataset.count), dec = Number(x.dataset.decimals || 0);
          x.textContent = (x.dataset.prefix || '') + fmtCount(en.action === 'count' ? target * easeOut(p) : target, dec) + (x.dataset.suffix || '');
        }});
        for (const h of e.highlights) {{
          const q = (t - h.t) / h.dur;
          if (q > 0 && q < 1) scale *= 1 + 0.12 * Math.sin(Math.PI * q);
        }}
        if (e.exit && t >= e.exit.t) {{ const q = easeOut((t - e.exit.t) / e.exit.dur); opacity *= 1 - q; scale *= 1 - 0.2 * q; }}
        node.setAttribute('opacity', opacity);
        if (scale === 1 && dy === 0) {{ node.removeAttribute('transform'); return; }}
        const b = node.getBBox(), cx = b.x + b.width / 2, cy = b.y + b.height / 2;
        node.setAttribute('transform', `translate(0 ${{dy}}) translate(${{cx}} ${{cy}}) scale(${{scale}}) translate(${{-cx}} ${{-cy}})`);
      }}

      const FPS = {spec.meta.fps};
      const decorNodes = [...document.querySelectorAll('#decor [data-drift]')].map((n) => [n, n.dataset.drift.split(',').map(Number)]);
      const grainTiles = [...document.querySelectorAll('[data-grain]')];
      const idleNodes = [...document.querySelectorAll('[data-idle]')];
      const grid = document.getElementById('grid'), glow = document.getElementById('bgGlow');
      function placeSymbols() {{
        document.querySelectorAll('[data-sym-size]').forEach((g) => {{
          const size = Number(g.dataset.symSize), slots = g.querySelectorAll('[data-sym]'), paths = g.querySelectorAll('[data-sym-path]');
          slots.forEach((slot, i) => {{
            const p = slot.getStartPositionOfChar(0), w = slot.getComputedTextLength();
            const cx = p.x + w / 2, cy = p.y - 0.36 * size, half = 0.30 * size, bar = 0.085 * size, gap = 0.13 * size;
            const rect = (y) => `M${{cx - half}} ${{y - bar / 2}}h${{2 * half}}v${{bar}}h${{-2 * half}}z`;
            // slash as a thin parallelogram from lower-left to upper-right
            const sx = 0.16 * size, sy = 0.36 * size, sw = 0.05 * size;
            const slash = `M${{cx - sx - sw}} ${{cy + sy}}L${{cx + sx - sw}} ${{cy - sy}}L${{cx + sx + sw}} ${{cy - sy}}L${{cx - sx + sw}} ${{cy + sy}}z`;
            if (paths[i]) paths[i].setAttribute('d', rect(cy - gap) + rect(cy + gap) + slash);
          }});
        }});
      }}
      function secondaryMotion(t) {{
        // Background drift: grid slides diagonally, glow wanders (both pure functions of t).
        grid.setAttribute('patternTransform', `translate(${{(t * 14) % 72}} ${{(t * 9) % 72}})`);
        glow.setAttribute('cx', `${{50 + 14 * Math.sin(t * 0.45)}}%`);
        glow.setAttribute('cy', `${{42 + 10 * Math.cos(t * 0.37)}}%`);
        // Slow drifting decor: each circle orbits on its own (seeded) ellipse.
        for (const [n, [ax, ay, w, ph]] of decorNodes)
          n.setAttribute('transform', `translate(${{ax * Math.sin(t * w + ph)}} ${{ay * Math.cos(t * w * 0.8 + ph)}})`);
        // Film grain: swap tile every 2 frames.
        const tile = Math.floor(Math.round(t * FPS) / 2) % Math.max(1, grainTiles.length);
        grainTiles.forEach((g, i) => g.setAttribute('visibility', i === tile ? 'visible' : 'hidden'));
        // Idle motion on icons/accents (inner groups, so it composes with enter animations).
        for (const n of idleNodes) {{
          const kind = n.dataset.idle, b = n.getBBox(), cx = b.x + b.width / 2, cy = b.y + b.height / 2;
          if (kind === 'spin') n.setAttribute('transform', `rotate(${{(t * 18) % 360}} ${{cx}} ${{cy}})`);
          else if (kind === 'bob') n.setAttribute('transform', `translate(0 ${{Math.sin(t * 2.2) * 8}})`);
          else if (kind === 'pulse') {{ const s = 1 + 0.05 * Math.sin(t * 3.1); n.setAttribute('transform', `translate(${{cx}} ${{cy}}) scale(${{s}}) translate(${{-cx}} ${{-cy}})`); }}
          else if (kind === 'sway') n.setAttribute('transform', `rotate(${{Math.sin(t * 1.7) * 4}} ${{cx}} ${{cy}})`);
        }}
      }}
      window.render = function(t, mouth='smile', init=false) {{
        if (!init && document.fonts.status !== 'loaded') throw new Error('brand fonts not loaded');
        placeSymbols();
        secondaryMotion(t);
        for (const [e, node] of nodes) if (node) animateElement(e, node, t);
        const ml=document.getElementById('mascot-layer');
        if(mascotEnabled) {{
          // Enter/exit by sliding through the bottom edge (0.5 s) when a neighbour has no NODI.
          const D = nodiState.duration || 1e9, S = {NODI_SLIDE_SECONDS};
          const inY = nodiState.enter ? (1 - easeOut(t / S)) * nodiState.slide : 0;
          const outP = clamp((t - (D - S)) / S), outY = nodiState.exit ? outP * outP * nodiState.slide : 0;
          ml.setAttribute('opacity', 1);
          ml.setAttribute('transform', `translate(0 ${{inY + outY + Math.sin(t*2.1)*5}})`);
          if(nodi) {{
            // deterministic blink every 3.2 s; 'smile' from the audio pipeline = mouth closed
            const bp=(t+1.1)%3.2, blink = bp<0.16 ? 1-Math.abs(bp-0.08)/0.08 : 0;
            // smoothed "is speaking" from caption windows -> drives hand gestures
            let activity=0;
            for (const c of captions) activity=Math.max(activity,
              smooth((t-c.start)/0.3)*smooth((c.end+0.15-t)/0.3));
            const [pose, prevPose] = at(plan.nodi_pose, t);
            const [expr] = at(plan.nodi_expression, t);
            // The rig remembers its previous pose; set it explicitly so every frame is a
            // pure function of t (previews jump to arbitrary times).
            const first = pose === plan.nodi_pose[0];
            nodi.update({{t, pose: first ? 'rest' : prevPose.value, poseT: 1, expression: expr.value, gesture: 'none'}});
            nodi.update({{t, pose: pose.value, poseT: t - pose.t, expression: expr.value,
              mouth: mouth==='smile' ? 'none' : mouth, blink, talkEnergy: ENERGY[mouth]||0,
              activity, gesture:'auto', gestureSeed:nodiState.gestureSeed}});
          }}
        }}
        captions.forEach((c,i)=>{{
          const el=document.getElementById('caption-'+i);
          const active=t>=c.start && t<=c.end;
          const enter=active?smooth((t-c.start)/0.12):0;
          el.setAttribute('opacity',active?Math.max(.0,enter):0);
          if(active) {{
            el.setAttribute('transform',`translate(0 ${{(1-enter)*14}})`);
            const words = el.querySelectorAll('[data-hl]'), rects = el.querySelectorAll('[data-hl-rect]');
            words.forEach((w, k) => {{
              const r = rects[k], n = w.getNumberOfChars();
              if (!r || !n) return;
              // glyph positions (tspan getBBox under-reports the last advance)
              const x0 = w.getStartPositionOfChar(0).x, x1 = w.getEndPositionOfChar(n - 1).x;
              const e = w.getExtentOfChar(0), sw = easeOut((t - c.start - 0.12 - k * 0.1) / 0.32);
              r.setAttribute('x', x0 - 12); r.setAttribute('y', e.y + e.height * 0.14);
              r.setAttribute('width', Math.max(0, (x1 - x0 + 24) * sw)); r.setAttribute('height', e.height * 0.8);
            }});
          }}
        }});
      }};
      window.render(0, 'smile', true);
    }})();
    </script></body></html>'''
