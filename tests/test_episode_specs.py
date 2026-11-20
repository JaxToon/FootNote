from pathlib import Path

from fnvideo.services.spec_loader import load_episode_spec

ROOT = Path(__file__).resolve().parents[1]


def test_short_pilot_spec_is_valid() -> None:
    spec = load_episode_spec(ROOT / "specs/fondasi-01-korelasi-bukan-kausalitas/short.yaml")
    assert spec.meta.format == "short"
    assert spec.meta.width == 1080
    assert len(spec.scenes) >= 1


def test_unrelated_topic_spec_is_valid() -> None:
    spec = load_episode_spec(ROOT / "specs/example-sql-join.short.yaml")
    assert spec.meta.series == "Data Analyst"
    assert spec.scenes[0].template == "title_question"


def test_long_pilot_spec_is_valid() -> None:
    spec = load_episode_spec(ROOT / "specs/fondasi-01-korelasi-bukan-kausalitas/long.yaml")
    assert spec.meta.format == "long"
    assert spec.meta.width == 1920
