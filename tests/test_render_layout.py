from __future__ import annotations

import json
from pathlib import Path

import pytest

from fnvideo.audio.timing import build_estimated_timing
from fnvideo.models.episode import EpisodeSpec
from fnvideo.render import engine
from fnvideo.render.svg_scene import (
    NODI_CENTER_X,
    NODI_H,
    NODI_TOP_Y,
    NODI_W,
    build_scene_html,
    compute_layout,
)
from fnvideo.services.spec_loader import load_episode_spec

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = [
    "title_question", "chapter_title", "definition_card", "paired_trend", "line_chart",
    "scatter_regression", "question_link", "causal_diagram", "takeaway", "follow_cta", "unknown",
]  # fmt: skip
PROFILES = [("short", 1080, 1920), ("long", 1920, 1080)]


def _spec(fmt: str, width: int, height: int) -> EpisodeSpec:
    base = load_episode_spec(ROOT / "specs/fondasi-01-korelasi-bukan-kausalitas/short.yaml")
    meta = base.meta.model_copy(update={"format": fmt, "width": width, "height": height})
    return EpisodeSpec.model_validate({**base.model_dump(), "meta": meta.model_dump()})


@pytest.mark.parametrize(("fmt", "width", "height"), PROFILES)
@pytest.mark.parametrize("mascot", [True, False])
def test_layout_zones(fmt: str, width: int, height: int, mascot: bool) -> None:
    lay = compute_layout(width, height, mascot)
    assert lay.top < lay.bottom < lay.caption_base
    if fmt == "short":
        assert lay.top == 200
        if not mascot:
            assert lay.bottom >= 1440  # content fills y=200..~1450
        assert lay.caption_base <= height * 0.80  # one-line caption stays above the UI zone
        t = lay.type
        assert 110 <= t["headline"] <= 160
        assert t["label"] >= 36 and t["supporting"] >= 40 and t["caption"] == 56
    if mascot:
        assert lay.nodi is not None
        x, y, s = lay.nodi
        assert 0 <= x and x + NODI_W * s <= width
        assert y >= 0 and y + NODI_H * s <= lay.caption_base
        if fmt == "long":  # NODI column is outside the content zone
            assert lay.right <= x
        else:  # portrait: NODI is the centred performer below the content band
            assert 1.2 <= s <= 1.5
            assert abs((x + NODI_CENTER_X * s) - width / 2) < 1
            assert 330 <= (343 - NODI_TOP_Y) * s <= 480  # head height in px
            assert lay.bottom < y + NODI_TOP_Y * s
    else:
        assert lay.nodi is None


def test_html_is_deterministic_and_has_no_wall_clock() -> None:
    spec = _spec("short", 1080, 1920)
    timing = build_estimated_timing(spec, 0.35)
    for scene, st in zip(spec.scenes, timing["scenes"], strict=False):
        a = build_scene_html(spec, scene, st, timing)
        assert a == build_scene_html(spec, scene, st, timing)
        for banned in (
            "Date.now",
            "requestAnimationFrame",
            "Math.random",
            "@keyframes",
            "transition:",
        ):
            assert banned not in a


def test_paired_trend_plots_spec_series() -> None:
    spec = _spec("long", 1920, 1080)
    scene = spec.scenes[1].model_copy(
        update={"props": {**spec.scenes[1].props, "series": [[1, 2, 3], [3, 2, 1]]}}
    )
    html = build_scene_html(spec, scene, {"captions": []}, {})
    assert html.count('data-reveal="') == 6  # one dot per data point


def _chromium_ok() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            p.chromium.launch().close()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _chromium_ok(), reason="Playwright Chromium not installed")
def test_all_templates_run_in_browser_and_scenes_do_not_leak_state() -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for fmt, width, height in PROFILES:
                spec = _spec(fmt, width, height)
                page = browser.new_page(viewport={"width": width, "height": height})
                page.on("pageerror", lambda exc, pg=page: engine.page_errors(pg).append(str(exc)))
                for name in TEMPLATES:
                    scene = spec.scenes[0].model_copy(update={"template": name})
                    engine.load_scene_page(
                        page, build_scene_html(spec, scene, {"captions": []}, {})
                    )
                    page.evaluate("() => window.render(1.0, 'mid')")
                # Two scenes on one page: the second scene's captions must drive render().
                caps_a = {"captions": [{"text": "A", "highlight": [], "start": 0, "end": 1}]}
                caps_b = {"captions": [{"text": "B", "highlight": [], "start": 5, "end": 9}]}
                for caps in (caps_a, caps_b):
                    engine.load_scene_page(page, build_scene_html(spec, spec.scenes[0], caps, {}))
                op = page.evaluate(
                    "() => { window.render(6, 'smile');"
                    " return document.getElementById('caption-0').getAttribute('opacity'); }"
                )
                assert float(op) == 1.0
                page.close()
        finally:
            browser.close()


def test_ffmpeg_atomic_keeps_previous_output_on_failure(tmp_path: Path, monkeypatch) -> None:
    out = tmp_path / "final.mp4"
    out.write_bytes(b"previous-good")

    def failing_run(cmd: list[str]) -> None:
        Path(cmd[-1]).write_bytes(b"partial")
        raise RuntimeError("ffmpeg failed")

    monkeypatch.setattr(engine, "_run", failing_run)
    with pytest.raises(RuntimeError):
        engine.run_ffmpeg_atomic(["-i", "x"], out)
    assert out.read_bytes() == b"previous-good"
    assert not engine.tmp_path_for(out).exists()

    def ok_run(cmd: list[str]) -> None:
        assert cmd[-1].endswith("final.tmp.mp4")  # container extension preserved
        Path(cmd[-1]).write_bytes(b"new")

    monkeypatch.setattr(engine, "_run", ok_run)
    engine.run_ffmpeg_atomic(["-i", "x"], out)
    assert out.read_bytes() == b"new"


def test_ffmpeg_atomic_rejects_empty_output(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(engine, "_run", lambda cmd: Path(cmd[-1]).write_bytes(b""))
    with pytest.raises(RuntimeError, match="no output"):
        engine.run_ffmpeg_atomic([], tmp_path / "a.wav")
    assert not (tmp_path / "a.wav").exists()


def test_silent_wav_duration(tmp_path: Path) -> None:
    import wave

    path = engine.write_silent_wav(tmp_path / "s.wav", 1.5)
    with wave.open(str(path)) as w:
        assert w.getnframes() == 66150 and w.getnchannels() == 2


def test_qa_report_metadata(tmp_path: Path) -> None:
    from fnvideo.config import load_settings

    spec = _spec("short", 1080, 1920)
    timing = build_estimated_timing(spec, 0.35)
    total = timing["scenes"][-1]["end_seconds"]
    media = {
        "video_codec": "h264", "width": 1080, "height": 1920, "frame_rate": "30/1",
        "frame_count": round(total * 30), "audio_codec": "aac", "duration_seconds": total,
    }  # fmt: skip
    final = tmp_path / "final.mp4"
    final.write_bytes(b"x")
    qa = engine.build_qa_report(
        spec, timing, media, load_settings(), final_path=final, contact=tmp_path / "c.png",
        scene_count=len(spec.scenes), silent_audio=True,
    )  # fmt: skip
    assert qa["technical_checks_passed"] is True
    assert qa["publish_ready"] is False
    assert qa["status"] == "draft_test_render"
    assert qa["audio_source"] == "silent_placeholder"
    assert qa["caption_timing_quality"] == {"estimated": sum(len(s.captions) for s in spec.scenes)}
    json.dumps(qa)  # serialisable

    bad = engine.build_qa_report(
        spec, timing, {**media, "duration_seconds": total + 1, "width": 720}, load_settings(),
        final_path=final, contact=final, scene_count=4, silent_audio=False,
    )  # fmt: skip
    assert bad["checks"]["duration_matches_timing"] is False
    assert bad["technical_checks_passed"] is False


def test_captions_fit_one_line_and_pilot_short_has_no_caption_warnings() -> None:
    from fnvideo.render.svg_scene import CAPTION_MIN_SIZE, caption_fit, caption_warnings

    lay = compute_layout(1080, 1920, False)
    size, lines = caption_fit("Belum tentu saling menyebabkan", lay)
    assert len(lines) == 1 and size <= 56
    size, lines = caption_fit("Kalimat yang sangat panjang sekali untuk satu baris caption", lay)
    assert size == CAPTION_MIN_SIZE and len(lines) == 2
    spec = load_episode_spec(ROOT / "specs/fondasi-01-korelasi-bukan-kausalitas/short.yaml")
    assert caption_warnings(spec) == []
