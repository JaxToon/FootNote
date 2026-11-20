from __future__ import annotations

import html
import json
import math
import re
from typing import Any

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


def nodi_svg(x: float, y: float, scale: float, pose: str, outfit: str, expression: str) -> str:
    """Reusable NODI vector puppet; keep anatomy stable across outfit variants."""
    outfit_color = {
        "classic": "#243D57",
        "academic": "#245F59",
        "data_explorer": "#5142A0",
        "creator": "#E56B50",
        "career_ready": "#243D57",
    }.get(outfit, "#243D57")
    # Pose changes are deliberately small: NODI is a companion, not the focal content.
    left_arm = "M72 218 Q25 218 24 164" if pose in {"wave", "curious"} else "M72 218 Q34 250 43 286"
    right_arm = (
        "M205 218 Q252 203 260 150"
        if pose in {"explaining", "point"}
        else "M205 218 Q244 250 232 286"
    )
    right_hand = (
        '<circle cx="260" cy="145" r="15" fill="#B97958"/>'
        if pose in {"explaining", "point"}
        else '<circle cx="232" cy="286" r="15" fill="#B97958"/>'
    )
    mouth = {
        "curious": "M116 143 Q132 151 148 143",
        "thinking": "M119 146 Q132 143 145 146",
        "skeptical": "M116 148 Q132 139 148 149",
        "happy": "M111 139 Q132 169 153 139",
        "surprised": "M122 140 Q132 162 142 140",
        "thoughtful": "M116 147 Q132 155 148 147",
        "explaining": "M113 141 Q132 160 151 141",
    }.get(expression, "M114 142 Q132 158 150 142")
    brow = {
        "curious": ("M103 104 Q116 96 127 103", "M139 103 Q151 95 163 101"),
        "thinking": ("M103 103 Q115 96 127 103", "M139 103 Q151 105 163 108"),
        "skeptical": ("M103 108 Q116 105 127 99", "M139 102 Q151 96 163 97"),
        "surprised": ("M102 96 Q115 88 127 96", "M139 96 Q151 88 164 96"),
        "happy": ("M104 106 Q115 101 127 105", "M139 105 Q151 101 162 106"),
    }.get(expression, ("M104 105 Q115 100 127 105", "M139 105 Q151 100 162 105"))

    outfit_detail = {
        "classic": '<path d="M105 220 Q132 235 159 220" fill="none" stroke="#F4F1E8" stroke-opacity=".7" stroke-width="4"/><circle cx="132" cy="254" r="5" fill="#F3D65B"/>',
        "academic": '<path d="M99 221 L165 221 L158 278 L106 278 Z" fill="#F4F1E8" fill-opacity=".14" stroke="#F4F1E8" stroke-opacity=".75" stroke-width="3"/><path d="M110 235 H151 M110 247 H146 M110 259 H138" stroke="#F4F1E8" stroke-width="3" stroke-linecap="round"/><path d="M119 89 h-18 m62 0 h-18" stroke="#111D38" stroke-width="5"/>',
        "data_explorer": '<path d="M95 228 H169 V282 H95 Z" fill="#F3D65B" fill-opacity=".16" stroke="#F3D65B" stroke-width="3"/><path d="M106 266 L119 253 L132 261 L151 238" fill="none" stroke="#F3D65B" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/><circle cx="151" cy="238" r="4" fill="#F3D65B"/>',
        "creator": '<path d="M102 225 L162 225 L155 281 H109 Z" fill="#F4F1E8" fill-opacity=".12" stroke="#F4F1E8" stroke-opacity=".65" stroke-width="3"/><path d="M112 242 H152 M112 254 H142" stroke="#F4F1E8" stroke-width="3" stroke-linecap="round"/><path d="M78 43 Q132 -1 186 43" fill="none" stroke="#F3D65B" stroke-width="7" stroke-linecap="round"/>',
        "career_ready": '<path d="M132 211 L145 231 L132 254 L119 231 Z" fill="#F3D65B"/><path d="M119 231 L132 254 L132 283 L111 265 Z M145 231 L132 254 L132 283 L153 265 Z" fill="#F4F1E8" fill-opacity=".85"/>',
    }.get(outfit, "")

    return f'''<g id="nodi" transform="translate({x} {y}) scale({scale})">
      <ellipse cx="135" cy="337" rx="101" ry="13" fill="#050B17" opacity=".30"/>
      <!-- Stable hood silhouette and folded-corner signature -->
      <path d="M55 103 Q52 26 126 17 Q204 9 222 89 L215 174 Q207 205 184 218 L78 218 Q54 192 50 158 Z" fill="#111D38" stroke="#070E1D" stroke-width="8" stroke-linejoin="round"/>
      <path d="M66 94 Q76 42 132 39 Q190 39 207 94 Q203 151 178 171 Q133 190 91 169 Q68 147 66 94 Z" fill="#F4F1E8" stroke="#D9D4C9" stroke-width="4"/>
      <path d="M178 34 L222 17 L213 71 L190 62 Z" fill="#F3D65B" stroke="#111D38" stroke-width="6" stroke-linejoin="round"/>
      <path d="M189 61 L213 71" stroke="#D4B73D" stroke-width="3"/>
      <!-- Brows and eyes -->
      <path d="{brow[0]}" fill="none" stroke="#111D38" stroke-width="5" stroke-linecap="round"/>
      <path d="{brow[1]}" fill="none" stroke="#111D38" stroke-width="5" stroke-linecap="round"/>
      <ellipse cx="115" cy="124" rx="7.5" ry="12" fill="#111D38"/>
      <ellipse cx="150" cy="124" rx="7.5" ry="12" fill="#111D38"/>
      <path id="nodi-mouth" d="{mouth}" fill="none" stroke="#111D38" stroke-width="5.5" stroke-linecap="round"/>
      <path d="M87 151 Q96 156 104 151 M160 151 Q168 156 176 151" fill="none" stroke="#E56B50" stroke-opacity=".45" stroke-width="4" stroke-linecap="round"/>
      <!-- Arms behind torso -->
      <path d="{left_arm}" fill="none" stroke="{outfit_color}" stroke-width="25" stroke-linecap="round"/>
      <path d="{right_arm}" fill="none" stroke="{outfit_color}" stroke-width="25" stroke-linecap="round"/>
      <circle cx="24" cy="164" r="14" fill="#B97958"/>
      {right_hand}
      <!-- Modular torso, consistent anatomy -->
      <path d="M75 198 Q132 177 198 198 L211 294 Q133 321 59 294 Z" fill="{outfit_color}" stroke="#0B1428" stroke-width="6" stroke-linejoin="round"/>
      <path d="M108 202 Q132 225 156 202" fill="none" stroke="#F4F1E8" stroke-opacity=".40" stroke-width="4"/>
      {outfit_detail}
      <!-- Legs and signature sneakers -->
      <path d="M82 288 L78 320 Q100 331 121 319 L119 291 Z M146 291 L145 319 Q169 332 190 320 L182 288 Z" fill="#111D38"/>
      <path d="M62 322 Q89 313 119 322 Q127 327 122 340 H59 Q48 335 62 322 Z" fill="#F4F1E8" stroke="#111D38" stroke-width="5"/>
      <path d="M145 322 Q173 313 199 322 Q211 335 199 340 H145 Q137 331 145 322 Z" fill="#F4F1E8" stroke="#111D38" stroke-width="5"/>
      <path d="M72 333 H111 M157 333 H190" stroke="#F3D65B" stroke-width="4" stroke-linecap="round"/>
    </g>'''


def template_art(scene: SceneSpec, width: int, height: int) -> str:
    portrait = height > width
    cx = width / 2
    top = 265 if portrait else 185
    main_y = 700 if portrait else 470
    prop = scene.props
    template = scene.template
    out: list[str] = []

    if template in {"title_question", "chapter_title"}:
        out.append(pill(cx, top, str(prop.get("chapter", scene.title))))
        headline = str(prop.get("headline", prop.get("title", scene.title))).replace(" ≠ ", " ≠ ")
        maxc = 16 if portrait else 30
        size = 94 if portrait else 86
        out.append(
            svg_text(
                cx,
                top + 220,
                headline,
                size=size,
                fill=PAPER,
                weight=800,
                max_chars=maxc,
                line_gap=size * 1.22,
            )
        )
        supporting = prop.get("supporting_text", "Lihat lebih dekat sebelum menyimpulkan")
        out.append(
            svg_text(
                cx,
                top + (500 if portrait else 340),
                str(supporting),
                size=32 if portrait else 30,
                fill="#D8E0EF",
                weight=500,
                max_chars=34 if portrait else 70,
            )
        )
        out.append(
            f'<path d="M{cx - 115} {top + 590} H{cx + 115}" stroke="{YELLOW}" stroke-width="8" stroke-linecap="round"/>'
        )

    elif template == "definition_card":
        term = str(prop.get("term", "Konsep"))
        definition = str(prop.get("definition", scene.purpose))
        card_w = width * 0.78
        card_h = 520 if portrait else 360
        x = cx - card_w / 2
        y = top + 120
        out.append(rounded_card(x, y, card_w, card_h, "#F4F1E8", 0.98, "#F3D65B", 0.85, 34))
        out.append(
            svg_text(
                cx,
                y + 130,
                term,
                size=68 if portrait else 64,
                fill="#111D38",
                weight=800,
                max_chars=19,
            )
        )
        out.append(
            svg_text(
                cx,
                y + 250,
                definition,
                size=34 if portrait else 31,
                fill="#243D57",
                weight=500,
                max_chars=30 if portrait else 55,
            )
        )
        out.append(pill(cx, y + card_h + 85, "KEY IDEA"))

    elif template in {"paired_trend", "line_chart", "scatter_regression"}:
        if template == "paired_trend":
            labels = prop.get("variables", ["Variabel A", "Variabel B"])
            chart_w = width * (0.78 if portrait else 0.39)
            chart_h = 340 if portrait else 340
            gap = 34 if portrait else 42
            start_x = cx - chart_w - gap / 2 if not portrait else cx - chart_w / 2
            positions = (
                [(start_x, main_y - 80), (start_x + chart_w + gap, main_y - 80)]
                if not portrait
                else [(start_x, main_y - 120), (start_x, main_y + 240)]
            )
            for i, label in enumerate(labels[:2]):
                x, y = positions[i]
                out.append(
                    rounded_card(x, y, chart_w, chart_h, "#FFFFFF", 0.08, "#FFFFFF", 0.22, 30)
                )
                out.append(
                    svg_text(
                        x + chart_w / 2,
                        y + 76,
                        str(label),
                        size=30 if portrait else 26,
                        fill=PAPER,
                        max_chars=20 if portrait else 24,
                    )
                )
                points = [
                    (
                        x + 42 + j * (chart_w - 84) / 5,
                        y
                        + chart_h
                        - 75
                        - (0.16 + 0.12 * j + 0.11 * math.sin(j * 1.3 + i * 0.4)) * (chart_h - 160),
                    )
                    for j in range(6)
                ]
                path = "M" + " L".join(f"{px:.1f} {py:.1f}" for px, py in points)
                out.append(
                    f'<path d="{path}" fill="none" stroke="{YELLOW if i == 0 else TEAL}" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>'
                )
                for px, py in points:
                    out.append(
                        f'<circle cx="{px:.1f}" cy="{py:.1f}" r="10" fill="{YELLOW if i == 0 else TEAL}"/>'
                    )
            out.append(
                pill(
                    cx,
                    main_y + (535 if portrait else 380),
                    str(prop.get("data_label", "ILUSTRASI")),
                )
            )
        elif template == "line_chart":
            x0, y0 = cx - width * 0.35, main_y + (300 if portrait else 160)
            chart_w, chart_h = width * 0.70, 420 if portrait else 360
            out.append(
                rounded_card(
                    x0 - 35,
                    y0 - chart_h - 80,
                    chart_w + 70,
                    chart_h + 140,
                    "#FFFFFF",
                    0.06,
                    "#FFFFFF",
                    0.2,
                    28,
                )
            )
            for i in range(4):
                yy = y0 - i * chart_h / 3
                out.append(
                    f'<path d="M{x0} {yy} H{x0 + chart_w}" stroke="#FFFFFF" stroke-opacity=".14" stroke-width="2"/>'
                )
            points = [
                (
                    x0 + j * chart_w / 7,
                    y0 - chart_h * (0.18 + 0.58 * (0.5 + 0.5 * math.sin(j * 1.1))),
                )
                for j in range(8)
            ]
            path = "M" + " L".join(f"{px:.1f} {py:.1f}" for px, py in points)
            out.append(
                f'<path d="{path}" fill="none" stroke="{YELLOW}" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>'
            )
            out.append(pill(cx, y0 + 105, str(prop.get("data_label", "ILUSTRASI"))))
        else:
            x0, y0 = cx - width * 0.34, main_y + 380
            chart_w, chart_h = width * 0.68, 430 if portrait else 380
            out.append(
                rounded_card(
                    x0 - 40,
                    y0 - chart_h - 70,
                    chart_w + 80,
                    chart_h + 130,
                    "#FFFFFF",
                    0.05,
                    "#FFFFFF",
                    0.18,
                    30,
                )
            )
            out.append(
                f'<path d="M{x0} {y0 - chart_h} V{y0} H{x0 + chart_w}" fill="none" stroke="#D8E0EF" stroke-opacity=".6" stroke-width="4"/>'
            )
            for i in range(28):
                px = x0 + 35 + ((i * 73) % int(max(80, chart_w - 70)))
                py = y0 - 25 - ((i * 47 + (i % 5) * 21) % int(max(90, chart_h - 50)))
                out.append(
                    f'<circle cx="{px}" cy="{py}" r="9" fill="{BLUE if i % 3 else YELLOW}" opacity=".9"/>'
                )
            out.append(
                f'<path d="M{x0 + 15} {y0 - 65} L{x0 + chart_w - 15} {y0 - chart_h + 50}" stroke="{CORAL}" stroke-width="7" stroke-dasharray="15 12"/>'
            )
            out.append(pill(cx, y0 + 110, "ILUSTRASI • TANPA ANGKA KLAIM"))

    elif template == "causal_diagram":
        nodes = prop.get(
            "nodes",
            [
                {"id": "z", "label": "Faktor ketiga"},
                {"id": "x", "label": "Variabel A"},
                {"id": "y", "label": "Variabel B"},
            ],
        )
        node_w = width * (0.40 if portrait else 0.26)
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
                (cx - node_w - node_w * 0.35, top + 330),
                (cx + node_w * 0.35, top + 330),
            ]
        # arrows first, behind the cards
        for x, y in node_pos[1:]:
            sx = cx
            sy = node_pos[0][1] + node_h
            ex = x + node_w / 2
            ey = y
            out.append(
                f'<path d="M{sx} {sy} Q{(sx + ex) / 2} {(sy + ey) / 2 - 20} {ex} {ey}" fill="none" stroke="{YELLOW}" stroke-width="8" stroke-linecap="round"/>'
            )
            out.append(
                f'<path d="M{ex - 13} {ey - 17} L{ex} {ey} L{ex + 13} {ey - 17}" fill="none" stroke="{YELLOW}" stroke-width="7" stroke-linecap="round"/>'
            )
        for idx, node in enumerate(nodes[:3]):
            x, y = node_pos[idx]
            out.append(
                rounded_card(
                    x,
                    y,
                    node_w,
                    node_h,
                    "#F4F1E8",
                    0.98,
                    YELLOW if idx == 0 else "#FFFFFF",
                    0.85,
                    26,
                )
            )
            out.append(
                svg_text(
                    x + node_w / 2,
                    y + node_h / 2 + 12,
                    str(node.get("label", "Node")),
                    size=29 if portrait else 26,
                    fill="#111D38",
                    max_chars=17 if portrait else 25,
                )
            )
        out.append(
            pill(
                cx,
                top + (950 if portrait else 560),
                str(prop.get("data_label", "MODEL KONSEPTUAL")),
            )
        )

    elif template == "question_link":
        labels = prop.get("labels", ["A", "?", "B"])
        y = main_y
        box_w = width * 0.22 if portrait else width * 0.20
        gap = width * 0.06
        start = cx - (box_w * 1.5 + gap)
        for i, label in enumerate(labels[:3]):
            x = start + i * (box_w + gap)
            fill = YELLOW if i == 1 else "#FFFFFF"
            text_fill = "#111D38" if i == 1 else PAPER
            out.append(
                f'<rect x="{x}" y="{y}" width="{box_w}" height="{box_w}" rx="32" fill="{fill}" fill-opacity="{1 if i == 1 else 0.10}" stroke="{fill}" stroke-opacity=".75" stroke-width="3"/>'
            )
            out.append(
                svg_text(
                    x + box_w / 2,
                    y + box_w / 2 + 20,
                    str(label),
                    size=68 if portrait else 60,
                    fill=text_fill,
                    max_chars=12,
                )
            )
            if i < 2:
                out.append(
                    svg_text(
                        x + box_w + gap / 2,
                        y + box_w / 2 + 14,
                        "→",
                        size=54,
                        fill=YELLOW,
                        max_chars=4,
                    )
                )
        out.append(
            svg_text(
                cx,
                y + box_w + 160,
                str(prop.get("supporting_text", "Hubungan belum tentu sebab-akibat")),
                size=34,
                fill="#D8E0EF",
                max_chars=34 if portrait else 65,
            )
        )

    elif template == "takeaway":
        points = prop.get(
            "points",
            ["Pahami pola yang terlihat", "Uji penjelasan alternatif", "Cari bukti yang relevan"],
        )
        card_w = width * 0.78
        card_h = 155 if portrait else 130
        gap = 34
        y0 = top + 120
        for i, point in enumerate(points[:4]):
            y = y0 + i * (card_h + gap)
            out.append(
                rounded_card(
                    cx - card_w / 2,
                    y,
                    card_w,
                    card_h,
                    "#FFFFFF",
                    0.08,
                    YELLOW if i == 0 else "#FFFFFF",
                    0.35,
                    26,
                )
            )
            out.append(
                f'<circle cx="{cx - card_w / 2 + 60}" cy="{y + card_h / 2}" r="27" fill="{YELLOW}"/>'
            )
            out.append(
                svg_text(
                    cx - card_w / 2 + 60,
                    y + card_h / 2 + 9,
                    str(i + 1),
                    size=26,
                    fill="#111D38",
                    max_chars=3,
                )
            )
            out.append(
                svg_text(
                    cx + 15,
                    y + card_h / 2 + 12,
                    str(point),
                    size=30 if portrait else 27,
                    fill=PAPER,
                    anchor="middle",
                    max_chars=32 if portrait else 56,
                )
            )

    elif template == "follow_cta":
        out.append(pill(cx, top + 90, "NEXT UP"))
        out.append(
            svg_text(
                cx,
                top + 300,
                str(prop.get("headline", "Lanjutkan eksplorasi")),
                size=78 if portrait else 72,
                fill=PAPER,
                max_chars=18 if portrait else 32,
            )
        )
        out.append(
            svg_text(
                cx,
                top + 540,
                str(prop.get("supporting_text", "Ikuti F/N untuk belajar lebih dalam")),
                size=32,
                fill="#D8E0EF",
                max_chars=32 if portrait else 70,
            )
        )
        out.append(
            f'<rect x="{cx - 210}" y="{top + 660}" width="420" height="78" rx="39" fill="{YELLOW}"/>'
        )
        out.append(
            svg_text(
                cx, top + 712, "F/N  •  FOLLOW FOR MORE", size=24, fill="#111D38", max_chars=30
            )
        )

    else:
        # Generic scene fallback keeps the template registry extensible.
        out.append(pill(cx, top, scene.title))
        out.append(
            svg_text(
                cx,
                top + 250,
                scene.title,
                size=76 if portrait else 72,
                max_chars=18 if portrait else 34,
            )
        )
        out.append(
            svg_text(
                cx,
                top + 440,
                scene.purpose,
                size=32,
                fill="#D8E0EF",
                weight=500,
                max_chars=32 if portrait else 70,
            )
        )

    return "".join(out)


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
    art = template_art(scene, width, height)
    brand_size = 28 if portrait else 24
    series = esc(spec.meta.series.upper())
    mascot_on = scene.character.mascot == "on"
    nodi = ""
    if mascot_on:
        scale = 0.78 if portrait else 0.70
        nodi = nodi_svg(
            width - 335 if portrait else width - 390,
            height * 0.39 if portrait else height * 0.24,
            scale,
            scene.character.mascot_pose or "rest",
            scene.character.mascot_outfit,
            scene.character.expression or "curious",
        )
    caption_y = height - 560 if portrait else height - 290
    cap_h = 190 if portrait else 150
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
    decor = "".join(
        f'<circle cx="{(i * 193 + 97) % width}" cy="{(i * 277 + 143) % height}" r="{8 + (i % 4) * 4}" fill="{YELLOW if i % 3 == 0 else PAPER}" opacity=".08"/>'
        for i in range(18)
    )
    mascot_layer = nodi
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
      html,body{{margin:0;width:{width}px;height:{height}px;background:{bg};overflow:hidden}}
      svg{{display:block;width:{width}px;height:{height}px}}
      text{{font-synthesis:none}}
    </style></head><body><svg id="frame" xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
      <defs>
        <radialGradient id="bgGlow" cx="50%" cy="42%" r="75%"><stop offset="0" stop-color="#FFFFFF" stop-opacity=".10"/><stop offset="1" stop-color="#000000" stop-opacity=".10"/></radialGradient>
        <pattern id="grid" width="72" height="72" patternUnits="userSpaceOnUse"><path d="M72 0H0V72" fill="none" stroke="#FFFFFF" stroke-opacity=".035" stroke-width="1"/></pattern>
        <filter id="softShadow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="18"/></filter>
      </defs>
      <rect width="100%" height="100%" fill="{bg}"/><rect width="100%" height="100%" fill="url(#bgGlow)"/><rect width="100%" height="100%" fill="url(#grid)"/>
      {decor}
      <g id="brand"><text x="64" y="{brand_size + 40}" fill="{YELLOW}" font-family="Space Grotesk, Arial, sans-serif" font-size="{brand_size + 14}" font-weight="800">F/N</text>
        <text x="145" y="{brand_size + 39}" fill="{PAPER}" opacity=".92" font-family="Space Grotesk, Arial, sans-serif" font-size="{brand_size - 4}" font-weight="700" letter-spacing="2">FOOTNOTE</text>
        <text x="{width - 64}" y="{brand_size + 36}" fill="{PAPER}" opacity=".58" text-anchor="end" font-family="IBM Plex Mono, monospace" font-size="20" letter-spacing="2">{series}</text>
        <path d="M64 {brand_size + 61} H{width - 64}" stroke="#FFFFFF" stroke-opacity=".16" stroke-width="2"/></g>
      <g id="scene-art" opacity="0">{art}</g>
      <g id="mascot-layer" opacity="0">{mascot_layer}</g>
      {"".join(caps)}
      <text x="64" y="{height - 70}" fill="{PAPER}" opacity=".38" font-family="IBM Plex Mono, monospace" font-size="18" letter-spacing="2">BEYOND THE OBVIOUS.</text>
    </svg>
    <script>
      const captions = {captions_json};
      const mascotEnabled = {str(mascot_on).lower()};
      const mouthShapes = {{smile:'M114 142 Q132 158 150 142', small:'M119 146 Q132 152 145 146', mid:'M116 140 Q132 162 148 140', wide:'M111 137 Q132 175 153 137', o:'M122 139 Q132 165 142 139'}};
      window.render = function(t, mouth='smile') {{
        const smooth = (v) => {{v=Math.max(0,Math.min(1,v));return v*v*(3-2*v)}};
        const art=document.getElementById('scene-art');
        art.setAttribute('opacity', smooth(t/0.48));
        art.setAttribute('transform', `translate(0 ${{(1-smooth(t/0.48))*28}})`);
        // Deterministic line draw-on for charts, arrows, and causal links.
        art.querySelectorAll('path').forEach((p,i)=>{{
          if(!p.dataset.pathLength){{try{{p.dataset.pathLength=p.getTotalLength()}}catch(e){{p.dataset.pathLength='0'}}}}
          const len=Number(p.dataset.pathLength||0);
          if(len>0){{p.style.strokeDasharray=`${{len}}`;p.style.strokeDashoffset=String(len*(1-smooth((t-.18-i*.025)/.72)))}}
        }});
        const ml=document.getElementById('mascot-layer');
        if(mascotEnabled) {{
          ml.setAttribute('opacity', smooth(t/0.5));
          ml.setAttribute('transform', `translate(0 ${{Math.sin(t*2.1)*5}})`);
          const m=document.getElementById('nodi-mouth');
          if(m) m.setAttribute('d', mouthShapes[mouth] || mouthShapes.smile);
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
    </script></body></html>'''
