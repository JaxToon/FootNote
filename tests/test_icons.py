from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from fnvideo.render.svg_scene import ICON_DIR, available_icons, icon, icon_inner

REQUIRED = {"sun", "ice_cream", "sunburn", "person", "database", "chart", "magnifier", "arrow_up"}


def test_required_icons_exist_and_are_valid_svg() -> None:
    assert REQUIRED <= set(available_icons())
    for path in ICON_DIR.glob("*.svg"):
        root = ET.fromstring(path.read_text(encoding="utf-8"))
        assert root.get("viewBox") == "0 0 200 200", path.name
        assert "<image" not in path.read_text(encoding="utf-8")  # vector only, no embedded art


def test_icon_is_scaled_and_centred() -> None:
    svg = icon("sun", 500, 400, 300)
    assert 'data-icon="sun"' in svg and "translate(350.0 250.0)" in svg and "scale(1.5000)" in svg
    assert 'data-idle="spin"' in icon_inner("sun")


def test_unknown_icon_lists_available() -> None:
    with pytest.raises(ValueError, match="ice_cream"):
        icon_inner("unicorn")


def test_every_icon_named_in_specs_exists() -> None:
    import yaml

    names: set[str] = set()

    def walk(v: object) -> None:
        if isinstance(v, dict):
            for k, x in v.items():
                if k == "icon":
                    names.add(str(x))
                elif k == "icons":
                    names.update(map(str, x))
                else:
                    walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)

    for spec in (Path(__file__).resolve().parents[1] / "specs").rglob("*.yaml"):
        walk(yaml.safe_load(spec.read_text(encoding="utf-8")))
    assert names and names <= set(available_icons())
