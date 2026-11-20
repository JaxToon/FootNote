"""Template features that implement the CLAUDE.md clarity rules."""

from __future__ import annotations

from pathlib import Path

import pytest

from fnvideo.audio.timing import _word_start
from fnvideo.render.svg_scene import compute_layout, pearson_r, template_art
from fnvideo.services.spec_loader import load_episode_spec

SPEC = Path("specs/fondasi-01-korelasi-bukan-kausalitas/short.yaml")


def _scene(scene_id: str):
    return next(s for s in load_episode_spec(SPEC).scenes if s.id == scene_id)


def _els(scene_id: str, mascot: bool):
    scene = _scene(scene_id)
    scale = 0.95 if scene.props.get("side_icons") and mascot else None
    return template_art(scene, compute_layout(1080, 1920, mascot, scene.background, scale))


def test_side_icons_flank_nodi() -> None:
    els = _els("hook", mascot=True)
    assert {"side-0", "side-1"} <= set(els.order())
    assert 'data-icon="swimmer"' in els.html() and 'data-icon="arrow_up"' in els.html()


def test_side_icons_shrink_nodi() -> None:
    big = compute_layout(1080, 1920, True, "paper")
    small = compute_layout(1080, 1920, True, "paper", 0.95)
    assert small.nodi[2] < big.nodi[2]
    assert small.bottom > big.bottom  # more room for the headline band


def test_false_link_is_crossable() -> None:
    order = _els("hidden-factor", mascot=False).order()
    assert {"false-link", "false-x"} <= set(order)
    assert order.index("false-link") < order.index("false-x") < order.index("node-0")


def test_chart_has_conclusion_and_computed_r() -> None:
    els = _els("example", mascot=False)
    assert {"conclusion", "r"} <= set(els.order())
    series = _scene("example").props["series"]
    assert f"r = {pearson_r(*series):.2f}" in els.html()  # Pearson r, lowercase


def test_pearson_r() -> None:
    assert pearson_r([1, 2, 3], [2, 4, 6]) == pytest.approx(1.0)
    assert pearson_r([1, 2, 3], [3, 2, 1]) == pytest.approx(-1.0)
    assert pearson_r([1, 1, 1], [1, 2, 3]) == 0.0


def test_word_cue_ignores_punctuation() -> None:
    t, _ = _word_start("Bukan.", "Bukan. Ada faktor ketiga.", 4.0, None)
    assert t == 0.0


def test_definition_card_icon_ties_term_to_example() -> None:
    from fnvideo.render.svg_scene import compute_layout, template_art
    from fnvideo.services.spec_loader import load_episode_spec

    spec = load_episode_spec(SPEC)
    scene = next(s for s in spec.scenes if s.template == "definition_card")
    els = template_art(scene, compute_layout(1080, 1920, False, scene.background))
    # tied to the example either by an icon + "Di sini" label or by the Z/X/Y diagram
    has_icon = "icon" in els.seq and "Di sini" in els.html()
    has_diagram = {"z", "x", "y"} <= set(els.seq) and "cuaca panas" in els.html()
    assert has_icon or has_diagram


def test_nodi_yields_to_side_icons_in_portrait() -> None:
    from fnvideo.render.svg_scene import NODI_PORTRAIT_SCALE, NODI_SIDE_SCALE, compute_layout

    assert NODI_SIDE_SCALE < NODI_PORTRAIT_SCALE
    lay = compute_layout(1080, 1920, True, "paper", nodi_scale=NODI_SIDE_SCALE)
    assert lay.nodi is not None and lay.nodi[2] == NODI_SIDE_SCALE


def test_scene_headline_with_accent_on_explanation_templates() -> None:
    els = _els("example", mascot=False)
    assert els.order()[0] == "headline"
    assert '<tspan fill="#F3D65B">PLOT</tspan>' in els.html()


def test_definition_card_diagram_uses_episode_example() -> None:
    els = _els("name-it", mascot=False)
    assert {"z", "x", "y", "arrow-zx", "arrow-zy", "xy"} <= set(els.order())
    assert "cuaca panas" in els.html() and "korelasi palsu" in els.html()


def test_captions_render_in_dark_box() -> None:
    from fnvideo.audio.timing import build_estimated_timing
    from fnvideo.render.svg_scene import build_scene_html

    spec = load_episode_spec(SPEC)
    timing = build_estimated_timing(spec, 0.35)
    html = build_scene_html(spec, spec.scenes[0], timing["scenes"][0], timing)
    assert 'data-cap-bg="1"' in html


def test_arrow_head_follows_line_and_waits_for_it() -> None:
    import math
    import re

    from fnvideo.render.svg_scene import arrow_svg

    svg = arrow_svg(0, 0, 100, 100, "#fff")
    assert 'data-nodraw="1" data-reveal="0.9"' in svg
    # both head points sit behind the tip along the 45° line (head is aligned, not vertical)
    head_d = re.search(r'data-reveal="0.9" d="([^"]+)"', svg).group(1)
    pts = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", head_d)]
    (hx0, hy0), (hx1, hy1) = (pts[0], pts[1]), (pts[4], pts[5])
    mid = ((hx0 + hx1) / 2, (hy0 + hy1) / 2)
    assert math.isclose(mid[0], mid[1], abs_tol=0.5) and mid[0] < 100


def test_dashed_links_keep_their_pattern_when_drawn() -> None:
    assert 'data-dash="20 16"' in _els("hidden-factor", mascot=False).html()
    assert 'data-dash="18 16"' in _els("name-it", mascot=False).html()


def test_decor_marks_stay_in_the_side_gutters() -> None:
    import re

    from fnvideo.render.svg_scene import decor_layer

    xs = [
        float(x) for x in re.findall(r'<circle cx="(\d+)" cy="\d+" r="13"', decor_layer(1080, 1920))
    ]
    xs += [float(x) for x in re.findall(r"M(\d+) \d+H", decor_layer(1080, 1920))]
    assert xs and all(x < 80 or x > 1000 for x in xs)


LONG = Path("specs/fondasi-01-korelasi-bukan-kausalitas/long.yaml")


def _long_els(scene_id: str):
    scene = next(s for s in load_episode_spec(LONG).scenes if s.id == scene_id)
    return template_art(scene, compute_layout(1920, 1080, False, scene.background))


def _group(html: str, element_id: str) -> str:
    import re

    return re.search(rf'data-id="{element_id}".*?(?=<g data-id=|$)', html, re.S).group(0)


@pytest.mark.parametrize("scene_id", ["hidden-factor", "work-confounder"])
def test_landscape_causal_arrows_run_down_to_their_effects(scene_id: str) -> None:
    import re

    html = _long_els(scene_id).html()
    for k in (1, 2):
        x0, y0, x1, y1 = map(
            float,
            re.search(
                r'd="M([\d.]+) ([\d.]+) L([\d.]+) ([\d.]+)"', _group(html, f"arrow-{k}")
            ).groups(),
        )
        assert y1 - y0 > 60, f"arrow-{k} must point down at its effect, not sideways or up"


def test_landscape_definition_card_puts_the_visual_beside_the_card() -> None:
    import re

    html = _long_els("name-confounder").html()
    card_x, card_w = map(
        float,
        re.search(r'<rect x="([\d.]+)" y="[\d.]+" width="([\d.]+)"', _group(html, "card")).groups(),
    )
    z_cx = float(re.search(r'<circle cx="([\d.]+)"', _group(html, "z")).group(1))
    assert z_cx > card_x + card_w  # diagram in its own column, not squeezed under the card


def test_paired_trend_resting_icons_do_not_overlap() -> None:
    import re

    for els in (_long_els("data"), _els("example", mascot=False)):
        rests = [float(r) for r in re.findall(r'data-rest="(-?[\d.]+)"', els.html())]
        assert len(rests) == 2 and rests[0] != rests[1]  # spread apart where the lines end close
