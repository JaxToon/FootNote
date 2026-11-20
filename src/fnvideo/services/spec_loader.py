from pathlib import Path
from typing import Any

import yaml

from fnvideo.models.episode import CURRENT_SCHEMA_VERSION, EpisodeSpec


def load_raw_spec(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Episode spec not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError("Episode spec must be a YAML mapping at the top level")
    return data


def migrate_spec(data: dict[str, Any]) -> dict[str, Any]:
    """Upgrade a raw spec mapping to the current schema version (pure, no I/O)."""
    data = dict(data)
    version = data.get("schema_version", 1)
    if version == 1:
        # v2 adds optional per-scene `beats`; v1 content is otherwise unchanged.
        data["schema_version"] = 2
        version = 2
    if version != CURRENT_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported schema_version {version}; this build reads up to {CURRENT_SCHEMA_VERSION}"
        )
    return data


def load_episode_spec(path: Path) -> EpisodeSpec:
    return EpisodeSpec.model_validate(migrate_spec(load_raw_spec(path)))
