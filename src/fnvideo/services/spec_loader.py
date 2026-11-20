from pathlib import Path
from typing import Any

import yaml

from fnvideo.models.episode import EpisodeSpec


def load_raw_spec(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Episode spec not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError("Episode spec must be a YAML mapping at the top level")
    return data


def load_episode_spec(path: Path) -> EpisodeSpec:
    return EpisodeSpec.model_validate(load_raw_spec(path))
