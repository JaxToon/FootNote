from __future__ import annotations

import re
from pathlib import Path

import pytest

from fnvideo.audio.timing import build_estimated_timing
from fnvideo.render import engine
from fnvideo.render.svg_scene import FONT_DIR, FONT_FACES, build_scene_html
from fnvideo.services.spec_loader import load_episode_spec

ROOT = Path(__file__).resolve().parents[1]
SPECS = sorted((ROOT / "specs").rglob("*.yaml"))
BRAND = {"Space Grotesk", "Inter", "IBM Plex Mono"}


def _texts(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [t for v in value.values() for t in _texts(v)]
    if isinstance(value, list):
        return [t for v in value for t in _texts(v)]
    return []


def test_font_files_and_licenses_present() -> None:
    for _, filename, _ in FONT_FACES:
        assert (FONT_DIR / filename).stat().st_size > 50_000
    assert len(list(FONT_DIR.glob("OFL-*.txt"))) == 3


@pytest.mark.parametrize("spec_path", SPECS, ids=lambda p: p.name)
def test_every_on_screen_glyph_is_in_the_brand_fonts(spec_path: Path) -> None:
    ttlib = pytest.importorskip("fontTools.ttLib")
    covered = set(ttlib.TTFont(FONT_DIR / "Inter[opsz,wght].ttf").getBestCmap())
    covered &= set(ttlib.TTFont(FONT_DIR / "SpaceGrotesk[wght].ttf").getBestCmap())
    spec = load_episode_spec(spec_path)
    missing = set()
    for scene in spec.scenes:
        texts = [c.text for c in scene.captions] + _texts(scene.props) + [scene.title]
        missing |= {ch for text in texts for ch in text if ord(ch) not in covered and ch != "\n"}
    assert not missing, f"glyphs not in brand fonts (draw as SVG instead): {sorted(missing)}"


def _chromium_ok() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            p.chromium.launch().close()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _chromium_ok(), reason="Playwright Chromium not installed")
def test_rendered_text_uses_brand_fonts_not_arial() -> None:
    """Ask Chromium which platform font actually rendered each text node."""
    from playwright.sync_api import sync_playwright

    spec = load_episode_spec(ROOT / "specs/fondasi-01-korelasi-bukan-kausalitas/short.yaml")
    timing = build_estimated_timing(spec, 0.35)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1080, "height": 1920})
            page.on("pageerror", lambda exc: engine.page_errors(page).append(str(exc)))
            cdp = page.context.new_cdp_session(page)
            cdp.send("DOM.enable")
            cdp.send("CSS.enable")
            for scene, st in zip(spec.scenes, timing["scenes"], strict=False):
                engine.load_scene_page(page, build_scene_html(spec, scene, st, timing))
                assert page.evaluate("document.fonts.status") == "loaded"
                page.evaluate("() => window.render(3.0, 'smile')")  # throws if fonts not ready
                root = cdp.send("DOM.getDocument", {"depth": -1})["root"]["nodeId"]
                nodes = cdp.send("DOM.querySelectorAll", {"nodeId": root, "selector": "text"})
                used: set[str] = set()
                for node_id in nodes["nodeIds"]:
                    fonts = cdp.send("CSS.getPlatformFontsForNode", {"nodeId": node_id})["fonts"]
                    used |= {f["familyName"] for f in fonts}
                assert used, "no text nodes measured"
                fallback = {f for f in used if not any(re.search(b, f) for b in BRAND)}
                assert not fallback, f"{scene.id}: text fell back to {fallback}"
        finally:
            browser.close()


@pytest.mark.skipif(not _chromium_ok(), reason="Playwright Chromium not installed")
def test_neq_is_drawn_as_svg_at_glyph_position() -> None:
    from playwright.sync_api import sync_playwright

    spec = load_episode_spec(ROOT / "specs/fondasi-01-korelasi-bukan-kausalitas/short.yaml")
    timing = build_estimated_timing(spec, 0.35)
    html = build_scene_html(spec, spec.scenes[0], timing["scenes"][0], timing)
    assert 'data-sym="neq"' in html and "data-sym-path" in html
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1080, "height": 1920})
            page.on("pageerror", lambda exc: engine.page_errors(page).append(str(exc)))
            engine.load_scene_page(page, html)
            page.evaluate("() => window.render(2.0, 'smile')")
            box = page.evaluate(
                "() => { const b = document.querySelector('[data-sym-path]').getBBox();"
                " return [b.x, b.y, b.width, b.height]; }"
            )
        finally:
            browser.close()
    x, y, w, h = box
    assert w > 40 and h > 40  # a real symbol, sized like the 94px headline
    assert 0 < x < 1080 and 0 < y < 1920
