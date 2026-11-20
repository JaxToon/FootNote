from __future__ import annotations

import base64
import html
import io
import json
import math
import re
from dataclasses import dataclass
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
}
YELLOW = "#F3D65B"
PAPER = "#F4F1E8"
CORAL = "#E56B50"
TEAL = "#6CB7A6"
BLUE = "#89B7D7"


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
    fill: str = PAPER,
    weight: int = 700,
    anchor: str = "middle",
    family: str = "Inter, Arial, sans-serif",
    max_chars: int = 22,
    line_gap: float | None = None,
) -> str:
    lines = split_lines(text, max_chars)
    gap = line_gap or size * 1.18
    tspans = "".join(
        f'<tspan x="{x}" dy="{0 if i == 0 else gap}">{esc(line)}</tspan>'
        for i, line in enumerate(lines)
    )
    return (
        f'<text x="{x}" y="{y}" fill="{fill}" font-family="{family}" '
        f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" '
        f'letter-spacing="-1">{tspans}</text>'
    )


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
) -> str:
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" '
        f'fill="{fill}" fill-opacity="{opacity}" stroke="{stroke}" stroke-opacity="{stroke_opacity}" stroke-width="2"/>'
    )


def pill(x: float, y: float, label: str, fill: str = YELLOW, text_fill: str = "#111D38") -> str:
    width = max(112, min(420, 36 + len(label) * 17))
    return (
        f'<rect x="{x - width / 2}" y="{y - 28}" width="{width}" height="56" rx="28" fill="{fill}"/>'
        f'<text x="{x}" y="{y + 9}" text-anchor="middle" fill="{text_fill}" '
        f'font-family="IBM Plex Mono, monospace" font-size="22" font-weight="700" letter-spacing="1">{esc(label.upper())}</text>'
    )


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
    """Canvas zones for one scene. Templates draw only inside the content zone."""

    width: int
    height: int
    portrait: bool
    cx: float  # content zone centre x
    rw: float  # content zone reference width (fractions are taken of this)
    top: float  # first content row baseline
    bottom: float  # content must end above this y
    caption_y: float
    caption_h: float
    nodi: tuple[float, float, float] | None  # x, y, scale

    def chars(self, base: int) -> int:
        """Scale a full-width max-chars budget to the content zone width."""
        return max(8, int(base * self.rw / self.width))


# NODI rig artwork box (assets/nodi_rig.js): 510 x 770 units before scaling.
NODI_W, NODI_H = 510, 770
SHORT_SAFE_BOTTOM = 0.80  # keep important info out of the bottom 20% (platform UI)


def compute_layout(width: int, height: int, mascot_on: bool) -> Layout:
    portrait = height > width
    if portrait:
        cap_h = 190
        caption_y = height * SHORT_SAFE_BOTTOM - 40 - cap_h
        nodi = None
        if mascot_on:
            scale = 0.56
            nodi = (width - 64 - NODI_W * scale, caption_y - 24 - NODI_H * scale, scale)
        return Layout(
            width, height, True, width / 2, width, 265, caption_y - 40, caption_y, cap_h, nodi
        )
    cap_h = 150
    caption_y = height - 290
    top, bottom = 185, caption_y - 30
    if mascot_on:
        scale = 0.50
        column = 380
        nodi = (width - 64 - NODI_W * scale, (top + bottom) / 2 - NODI_H * scale / 2, scale)
        left, right = 64, width - column
        return Layout(
            width,
            height,
            False,
            (left + right) / 2,
            right - left,
            top,
            bottom,
            caption_y,
            cap_h,
            nodi,
        )
    return Layout(width, height, False, width / 2, width, top, bottom, caption_y, cap_h, None)


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


def _dots(points: list[tuple[float, float]], color: str, r: int = 10) -> str:
    """Chart points; data-reveal is the fraction of the line-draw at which each appears."""
    n = len(points)
    dots = [
        f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r}" fill="{color}" '
        f'data-reveal="{j / max(1, n - 1):.3f}"/>'
        for j, (px, py) in enumerate(points)
    ]
    if dots:  # the newest data point keeps pulsing after the line is drawn
        dots[-1] = f'<g data-idle="pulse">{dots[-1]}</g>'
    return "".join(dots)


class Elements:
    """Collects template elements. Each element is one animatable unit with a data-id.

    `anim` is the element's default enter action (used when no beat targets it) and
    `seq` its default stagger order (defaults to insertion order, i.e. z-order).
    """

    def __init__(self) -> None:
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
    portrait = L.portrait
    cx, rw, top = L.cx, L.rw, L.top
    prop = scene.props
    template = scene.template
    els = Elements()

    if template in {"title_question", "chapter_title"}:
        els.add("chapter", pill(cx, top, str(prop.get("chapter", scene.title))))
        headline = str(prop.get("headline", prop.get("title", scene.title)))
        size = 94 if portrait else 86
        els.add(
            "headline",
            svg_text(cx, top + 220, headline, size=size, weight=800,
                     max_chars=16 if portrait else L.chars(30), line_gap=size * 1.22),
            "slide",
        )  # fmt: skip
        supporting = str(prop.get("supporting_text", "Lihat lebih dekat sebelum menyimpulkan"))
        els.add(
            "supporting",
            svg_text(cx, top + (500 if portrait else 330), supporting, size=32 if portrait else 30,
                     fill="#D8E0EF", weight=500, max_chars=34 if portrait else L.chars(70)),
            "slide",
        )  # fmt: skip
        rule_y = top + (590 if portrait else 400)
        els.add(
            "rule",
            f'<path d="M{cx - 115} {rule_y} H{cx + 115}" stroke="{YELLOW}" '
            'stroke-width="8" stroke-linecap="round"/>',
            "draw",
        )

    elif template == "definition_card":
        term = str(prop.get("term", "Konsep"))
        definition = str(prop.get("definition", scene.purpose))
        card_w = rw * 0.78
        card_h = 520 if portrait else 330
        x, y = cx - card_w / 2, top + 120
        els.add("card", rounded_card(x, y, card_w, card_h, PAPER, 0.98, YELLOW, 0.85, 34))
        els.add(
            "term",
            svg_text(cx, y + 130, term, size=68 if portrait else 64, fill="#111D38", weight=800,
                     max_chars=19),
            "slide",
        )  # fmt: skip
        els.add(
            "definition",
            svg_text(cx, y + 240, definition, size=34 if portrait else 31, fill="#243D57",
                     weight=500, max_chars=30 if portrait else L.chars(55)),
            "slide",
        )  # fmt: skip
        els.add("label", pill(cx, y + card_h + 55, "KEY IDEA"))

    elif template == "paired_trend":
        labels = prop.get("variables", ["Variabel A", "Variabel B"])
        data = prop.get("series")
        chart_h = 340
        if portrait:
            chart_w = rw * 0.78
            positions = [(cx - chart_w / 2, top + 65), (cx - chart_w / 2, top + 65 + chart_h + 40)]
        else:
            gap = 42
            chart_w = rw * 0.39
            positions = [(cx - chart_w - gap / 2, top + 100), (cx + gap / 2, top + 100)]
        for i, label in enumerate(labels[:2]):
            x, y = positions[i]
            color = YELLOW if i == 0 else TEAL
            values = (
                [float(v) for v in data[i]] if data and i < len(data) else _illustrative_series(i)
            )
            points = _series_points(values, x, y, chart_w, chart_h)
            path = "M" + " L".join(f"{px:.1f} {py:.1f}" for px, py in points)
            els.add(
                f"chart-{i}",
                rounded_card(x, y, chart_w, chart_h, "#FFFFFF", 0.08, "#FFFFFF", 0.22, 30)
                + svg_text(x + chart_w / 2, y + 76, str(label), size=30 if portrait else 26,
                           max_chars=20 if portrait else 24)
                + f'<path d="{path}" fill="none" stroke="{color}" stroke-width="9" '
                'stroke-linecap="round" stroke-linejoin="round"/>'
                + _dots(points, color),
                "draw",
            )  # fmt: skip
        last_y = positions[-1][1] + chart_h
        els.add("label", pill(cx, last_y + 60, str(prop.get("data_label", "ILUSTRASI"))))

    elif template == "line_chart":
        chart_w, chart_h = rw * 0.70, 420 if portrait else 360
        x0 = cx - chart_w / 2
        y0 = top + (735 if portrait else 445)
        grid = "".join(
            f'<path data-nodraw="1" d="M{x0} {y0 - i * chart_h / 3} H{x0 + chart_w}" '
            'stroke="#FFFFFF" stroke-opacity=".14" stroke-width="2"/>'
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
            rounded_card(x0 - 35, y0 - chart_h - 80, chart_w + 70, chart_h + 140,
                         "#FFFFFF", 0.06, "#FFFFFF", 0.2, 28)
            + grid
            + f'<path d="{path}" fill="none" stroke="{YELLOW}" stroke-width="10" '
            'stroke-linecap="round" stroke-linejoin="round"/>',
            "draw",
        )  # fmt: skip
        els.add("label", pill(cx, y0 + 105, str(prop.get("data_label", "ILUSTRASI"))))

    elif template == "scatter_regression":
        chart_w, chart_h = rw * 0.68, 430 if portrait else 360
        x0 = cx - chart_w / 2
        y0 = top + (815 if portrait else 455)
        pts = "".join(
            f'<circle cx="{x0 + 35 + ((i * 73) % int(max(80, chart_w - 70)))}" '
            f'cy="{y0 - 25 - ((i * 47 + (i % 5) * 21) % int(max(90, chart_h - 50)))}" r="9" '
            f'fill="{BLUE if i % 3 else YELLOW}" opacity=".9" data-reveal="{i / 27:.3f}"/>'
            for i in range(28)
        )
        els.add(
            "chart",
            rounded_card(x0 - 40, y0 - chart_h - 70, chart_w + 80, chart_h + 130,
                         "#FFFFFF", 0.05, "#FFFFFF", 0.18, 30)
            + f'<path d="M{x0} {y0 - chart_h} V{y0} H{x0 + chart_w}" fill="none" '
            'stroke="#D8E0EF" stroke-opacity=".6" stroke-width="4"/>'
            + pts,
            "draw",
        )  # fmt: skip
        els.add(
            "trend",
            f'<path d="M{x0 + 15} {y0 - 65} L{x0 + chart_w - 15} {y0 - chart_h + 50}" '
            f'stroke="{CORAL}" stroke-width="7" stroke-linecap="round"/>',
            "draw",
        )
        els.add("label", pill(cx, y0 + 105, "ILUSTRASI • TANPA ANGKA KLAIM"))

    elif template == "causal_diagram":
        nodes = prop.get(
            "nodes",
            [
                {"id": "z", "label": "Faktor ketiga"},
                {"id": "x", "label": "Variabel A"},
                {"id": "y", "label": "Variabel B"},
            ],
        )
        node_w = rw * (0.40 if portrait else 0.26)
        node_h = 150 if portrait else 132
        if portrait:
            node_pos = [
                (cx - node_w / 2, top + 130),
                (cx - node_w - 22, top + 620),
                (cx + 22, top + 620),
            ]
        else:
            node_pos = [
                (cx - node_w / 2, top + 30),
                (cx - node_w * 1.35, top + 330),
                (cx + node_w * 0.35, top + 330),
            ]
        sx, sy = cx, node_pos[0][1] + node_h
        # Arrows are drawn first (behind the cards) but animate after their source node.
        for k, (x, y) in enumerate(node_pos[1:], start=1):
            ex, ey = x + node_w / 2, y
            els.add(
                f"arrow-{k}",
                f'<path d="M{sx} {sy} Q{(sx + ex) / 2} {(sy + ey) / 2 - 20} {ex} {ey}" '
                f'fill="none" stroke="{YELLOW}" stroke-width="8" stroke-linecap="round"/>'
                f'<path d="M{ex - 13} {ey - 17} L{ex} {ey} L{ex + 13} {ey - 17}" fill="none" '
                f'stroke="{YELLOW}" stroke-width="7" stroke-linecap="round"/>',
                "draw",
                seq=2 * k - 1,
            )
        for idx, node in enumerate(nodes[:3]):
            x, y = node_pos[idx]
            body = (
                rounded_card(x, y, node_w, node_h, PAPER, 0.98,
                             YELLOW if idx == 0 else "#FFFFFF", 0.85, 26)
                + svg_text(x + node_w / 2, y + node_h / 2 + 12, str(node.get("label", "Node")),
                           size=29 if portrait else 26, fill="#111D38",
                           max_chars=17 if portrait else 25)
            )  # fmt: skip
            if idx == 0:  # the hidden cause breathes to keep attention on it
                body = f'<g data-idle="pulse">{body}</g>'
            els.add(f"node-{idx}", body, seq=0 if idx == 0 else 2 * idx)
        els.add(
            "label",
            pill(
                cx,
                top + (950 if portrait else 530),
                str(prop.get("data_label", "MODEL KONSEPTUAL")),
            ),
            seq=10,
        )

    elif template == "question_link":
        labels = prop.get("labels", ["A", "?", "B"])
        box_w = rw * 0.22 if portrait else min(rw * 0.20, 260)
        gap = rw * 0.06
        y = top + (435 if portrait else 150)
        start = cx - (box_w * 1.5 + gap)
        for i, label in enumerate(labels[:3]):
            x = start + i * (box_w + gap)
            fill = YELLOW if i == 1 else "#FFFFFF"
            text_fill = "#111D38" if i == 1 else PAPER
            els.add(
                f"item-{i}",
                f'<rect x="{x}" y="{y}" width="{box_w}" height="{box_w}" rx="32" fill="{fill}" '
                f'fill-opacity="{1 if i == 1 else 0.10}" stroke="{fill}" stroke-opacity=".75" '
                'stroke-width="3"/>'
                + svg_text(x + box_w / 2, y + box_w / 2 + 20, str(label),
                           size=68 if portrait else 60, fill=text_fill, max_chars=12),
            )  # fmt: skip
            if i < 2:
                els.add(
                    f"link-{i}",
                    svg_text(x + box_w + gap / 2, y + box_w / 2 + 14, "→", size=54,
                             fill=YELLOW, max_chars=4),
                    "slide",
                )  # fmt: skip
        els.add(
            "supporting",
            svg_text(cx, y + box_w + (160 if portrait else 110),
                     str(prop.get("supporting_text", "Hubungan belum tentu sebab-akibat")),
                     size=34, fill="#D8E0EF", max_chars=34 if portrait else L.chars(65)),
            "slide",
        )  # fmt: skip

    elif template == "takeaway":
        default_points = [
            "Pahami pola yang terlihat",
            "Uji penjelasan alternatif",
            "Cari bukti yang relevan",
        ]
        points = prop.get("points", default_points)[:4]
        card_w = rw * 0.78
        gap = 34
        y0 = top + 120
        limit = (L.nodi[1] - 30) if (portrait and L.nodi) else L.bottom
        n = max(1, len(points))
        card_h = min(155 if portrait else 130, (limit - y0 - gap * (n - 1)) / n)
        for i, point in enumerate(points):
            y = y0 + i * (card_h + gap)
            els.add(
                f"point-{i}",
                rounded_card(cx - card_w / 2, y, card_w, card_h, "#FFFFFF", 0.08,
                             YELLOW if i == 0 else "#FFFFFF", 0.35, 26)
                + f'<circle cx="{cx - card_w / 2 + 60}" cy="{y + card_h / 2}" r="27" fill="{YELLOW}"/>'
                + svg_text(cx - card_w / 2 + 60, y + card_h / 2 + 9, str(i + 1), size=26,
                           fill="#111D38", max_chars=3)
                + svg_text(cx + 15, y + card_h / 2 + 12, str(point), size=30 if portrait else 27,
                           max_chars=32 if portrait else L.chars(56)),
                "slide",
            )  # fmt: skip

    elif template == "follow_cta":
        els.add("badge", pill(cx, top + 90, "NEXT UP"))
        els.add(
            "headline",
            svg_text(cx, top + (300 if portrait else 230),
                     str(prop.get("headline", "Lanjutkan eksplorasi")),
                     size=78 if portrait else 72, max_chars=18 if portrait else L.chars(32)),
            "slide",
        )  # fmt: skip
        els.add(
            "supporting",
            svg_text(cx, top + (540 if portrait else 360),
                     str(prop.get("supporting_text", "Ikuti F/N untuk belajar lebih dalam")),
                     size=32, fill="#D8E0EF", max_chars=32 if portrait else L.chars(70)),
            "slide",
        )  # fmt: skip
        btn_y = top + (660 if portrait else 450)
        els.add(
            "button",
            f'<rect x="{cx - 210}" y="{btn_y}" width="420" height="78" rx="39" fill="{YELLOW}"/>'
            + svg_text(cx, btn_y + 52, "F/N  •  FOLLOW FOR MORE", size=24, fill="#111D38",
                       max_chars=30),
        )  # fmt: skip

    else:
        # Generic scene fallback keeps the template registry extensible.
        els.add("badge", pill(cx, top, scene.title))
        els.add(
            "headline",
            svg_text(cx, top + 250, scene.title, size=76 if portrait else 72,
                     max_chars=18 if portrait else L.chars(34)),
            "slide",
        )  # fmt: skip
        els.add(
            "supporting",
            svg_text(cx, top + 440, scene.purpose, size=32, fill="#D8E0EF", weight=500,
                     max_chars=32 if portrait else L.chars(70)),
            "slide",
        )  # fmt: skip

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


def decor_layer(width: int, height: int, count: int = 18) -> str:
    """Background circles; render(t) drifts each on its own seeded ellipse (data-drift)."""
    rng = np.random.default_rng(1729)
    out = []
    for i in range(count):
        ax, ay = rng.uniform(25, 70), rng.uniform(25, 70)
        w, ph = rng.uniform(0.25, 0.6), rng.uniform(0, 2 * math.pi)
        out.append(
            f'<circle cx="{(i * 193 + 97) % width}" cy="{(i * 277 + 143) % height}" '
            f'r="{10 + (i % 4) * 7}" fill="{YELLOW if i % 3 == 0 else PAPER}" opacity=".09" '
            f'data-drift="{ax:.1f},{ay:.1f},{w:.3f},{ph:.3f}"/>'
        )
    # A few large soft blobs: low-frequency ambient motion that reads even when small.
    for i in range(5):
        ax, ay = rng.uniform(60, 120), rng.uniform(60, 120)
        w, ph = rng.uniform(0.45, 0.75), rng.uniform(0, 2 * math.pi)
        out.insert(
            0,
            f'<circle cx="{width * (0.15 + 0.18 * i):.0f}" cy="{height * (0.2 + 0.15 * ((i * 3) % 5)):.0f}" '
            f'r="{min(width, height) * (0.16 + 0.03 * (i % 3)):.0f}" fill="{YELLOW if i % 2 else PAPER}" '
            f'opacity=".10" filter="url(#blobBlur)" data-drift="{ax:.1f},{ay:.1f},{w:.3f},{ph:.3f}"/>',
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


def grain_layer(width: int, height: int) -> str:
    patterns = "".join(
        f'<pattern id="grain-{i}" width="{GRAIN_SIZE}" height="{GRAIN_SIZE}" patternUnits="userSpaceOnUse">'
        f'<image href="{uri}" width="{GRAIN_SIZE}" height="{GRAIN_SIZE}"/></pattern>'
        for i, uri in enumerate(grain_tiles())
    )
    rects = "".join(
        f'<rect data-grain="{i}" width="{width}" height="{height}" fill="url(#grain-{i})" '
        f'opacity="{GRAIN_OPACITY}" style="mix-blend-mode:overlay" visibility="{"visible" if i == 0 else "hidden"}"/>'
        for i in range(GRAIN_TILES)
    )
    return f'<defs>{patterns}</defs><g id="grain" pointer-events="none">{rects}</g>'


def highlight_line(line: str, highlighted: list[str]) -> str:
    """Escape a caption line and wrap highlighted phrases in a yellow tspan."""
    if not highlighted:
        return esc(line)
    ordered = sorted(highlighted, key=len, reverse=True)
    pattern = re.compile("(" + "|".join(re.escape(h) for h in ordered) + ")", re.IGNORECASE)
    folded = {h.casefold() for h in highlighted}
    return "".join(
        f'<tspan fill="{YELLOW}" font-weight="850">{esc(part)}</tspan>'
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
    series = esc(spec.meta.series.upper())
    mascot_on = scene.character.mascot == "on"
    layout = compute_layout(width, height, mascot_on)
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
    if layout.nodi:
        nx, ny, scale = layout.nodi
        nodi = nodi_layer(nx, ny, scale, rim=scene.background in DARK_BACKGROUNDS)
        nodi_state = {
            "pose": NODI_POSE_MAP.get(scene.character.mascot_pose or "rest", "rest"),
            "expression": NODI_EXPRESSION_MAP.get(
                scene.character.expression or "neutral", "neutral"
            ),
            # varies the talking-gesture schedule from scene to scene (still deterministic)
            "gestureSeed": next((i for i, s in enumerate(spec.scenes) if s.id == scene.id), 0),
        }
    caption_y = layout.caption_y
    cap_h = layout.caption_h
    caps = []
    for idx, cap in enumerate(timing_scene.get("captions", [])):
        cap_text = str(cap["text"])
        size = 42 if portrait else 34
        maxc = 29 if portrait else 64
        lines = split_lines(cap_text, maxc)
        highlighted = [str(h) for h in cap.get("highlight", []) if str(h)]
        tspans = "".join(
            f'<tspan x="{cx}" dy="{0 if i == 0 else size * 1.15}">'
            f"{highlight_line(line, highlighted)}</tspan>"
            for i, line in enumerate(lines)
        )
        caps.append(
            f'<g id="caption-{idx}" opacity="0"><rect x="{cx - width * 0.43}" y="{caption_y}" width="{width * 0.86}" height="{cap_h}" rx="32" fill="#080F20" fill-opacity=".94" stroke="{YELLOW}" stroke-opacity=".62" stroke-width="3"/>'
            f'<text x="{cx}" y="{caption_y + cap_h / 2 - (len(lines) - 1) * size * 0.57 + size * 0.35}" text-anchor="middle" fill="{PAPER}" '
            f'font-family="Inter, Arial, sans-serif" font-size="{size}" font-weight="750" letter-spacing="-.8">{tspans}</text></g>'
        )
    captions_json = json.dumps(timing_scene.get("captions", []), ensure_ascii=False)
    # deterministic decor: no wall clock, no CSS animation, all movement comes from render(t).
    decor = decor_layer(width, height)
    grain = grain_layer(width, height)
    mascot_layer = nodi
    nodi_js = NODI_RIG_JS if layout.nodi else ""
    nodi_state_json = json.dumps(nodi_state)
    plan_json = json.dumps(plan)
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
      html,body{{margin:0;width:{width}px;height:{height}px;background:{bg};overflow:hidden}}
      svg{{display:block;width:{width}px;height:{height}px}}
      text{{font-synthesis:none}}
    </style></head><body><svg id="frame" xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
      <defs>
        <radialGradient id="bgGlow" cx="50%" cy="42%" r="75%" gradientUnits="objectBoundingBox"><stop offset="0" stop-color="#FFFFFF" stop-opacity=".10"/><stop offset="1" stop-color="#000000" stop-opacity=".10"/></radialGradient>
        <pattern id="grid" width="72" height="72" patternUnits="userSpaceOnUse" patternTransform="translate(0 0)"><path d="M72 0H0V72" fill="none" stroke="#FFFFFF" stroke-opacity=".035" stroke-width="1"/></pattern>
        <filter id="blobBlur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="40"/></filter>
        <filter id="softShadow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="18"/></filter>
        <filter id="nodiRim" x="-10%" y="-10%" width="120%" height="120%"><feMorphology in="SourceAlpha" operator="dilate" radius="9" result="d"/><feFlood flood-color="#F4F1E8" flood-opacity=".92"/><feComposite in2="d" operator="in" result="rim"/><feMerge><feMergeNode in="rim"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      </defs>
      <rect width="100%" height="100%" fill="{bg}"/><rect width="100%" height="100%" fill="url(#bgGlow)"/><rect width="100%" height="100%" fill="url(#grid)"/>
      <g id="decor">{decor}</g>
      <g id="brand"><text x="64" y="{brand_size + 40}" fill="{YELLOW}" font-family="Space Grotesk, Arial, sans-serif" font-size="{brand_size + 14}" font-weight="800">F/N</text>
        <text x="145" y="{brand_size + 39}" fill="{PAPER}" opacity=".92" font-family="Space Grotesk, Arial, sans-serif" font-size="{brand_size - 4}" font-weight="700" letter-spacing="2">FOOTNOTE</text>
        <text x="{width - 64}" y="{brand_size + 36}" fill="{PAPER}" opacity=".58" text-anchor="end" font-family="IBM Plex Mono, monospace" font-size="20" letter-spacing="2">{series}</text>
        <path d="M64 {brand_size + 61} H{width - 64}" stroke="#FFFFFF" stroke-opacity=".16" stroke-width="2"/></g>
      <g id="scene-art">{art}</g>
      <g id="mascot-layer" opacity="0">{mascot_layer}</g>
      {"".join(caps)}
      <text x="64" y="{height - 70}" fill="{PAPER}" opacity=".38" font-family="IBM Plex Mono, monospace" font-size="18" letter-spacing="2">BEYOND THE OBVIOUS.</text>
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
        node.querySelectorAll('path:not([data-nodraw])').forEach((path) => {{
          const len = strokeLen(path);
          if (len > 0) {{ path.style.strokeDasharray = `${{len}}`; path.style.strokeDashoffset = String(len * (1 - drawP)); }}
        }});
        if (en.action === 'draw') {{
          node.querySelectorAll(':scope > rect, :scope > text').forEach((x) => x.setAttribute('opacity', clamp(p * 3)));
        }}
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
      window.render = function(t, mouth='smile') {{
        secondaryMotion(t);
        for (const [e, node] of nodes) if (node) animateElement(e, node, t);
        const ml=document.getElementById('mascot-layer');
        if(mascotEnabled) {{
          ml.setAttribute('opacity', smooth(t/0.5));
          ml.setAttribute('transform', `translate(0 ${{Math.sin(t*2.1)*5}})`);
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
          if(active) el.setAttribute('transform',`translate(0 ${{(1-enter)*14}})`);
        }});
      }};
      window.render(0);
    }})();
    </script></body></html>'''
