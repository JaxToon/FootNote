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
    assert "icon" in els.seq and "Di sini" in els.html()


def test_nodi_yields_to_side_icons_in_portrait() -> None:
    from fnvideo.render.svg_scene import NODI_PORTRAIT_SCALE, NODI_SIDE_SCALE, compute_layout

    assert NODI_SIDE_SCALE < NODI_PORTRAIT_SCALE
    lay = compute_layout(1080, 1920, True, "paper", nodi_scale=NODI_SIDE_SCALE)
    assert lay.nodi is not None and lay.nodi[2] == NODI_SIDE_SCALE
