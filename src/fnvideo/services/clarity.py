"""Clarity lint (CLAUDE.md "Clarity rules", docs/HANDOFF_CLARITY.md).

Mechanical checks for the storytelling rules that can be verified from a spec alone:

(a) captions are the narration, verbatim (ignoring case and punctuation)
(b) the first scene shows something concrete (side icons, icons, or a chart)
(c) a mascot-only scene (title_question without side_icons) lasts at most 2 s, except the close
(d) every explanation scene has at least one `word:` beat

`validate` reports these as warnings; for `editorial_status: approved` specs they are errors
that block TTS and render (see `editorial_gate`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from fnvideo.audio.timing import estimate_scene_seconds
from fnvideo.models.episode import EpisodeSpec, SceneSpec

CHART_TEMPLATES = {"paired_trend", "line_chart", "scatter_regression"}
EXPLANATION_TEMPLATES = CHART_TEMPLATES | {"causal_diagram", "definition_card", "compare"}
MASCOT_ONLY_MAX_SECONDS = 2.0

_NON_WORD = re.compile(r"[^\w]+", re.UNICODE)


@dataclass(frozen=True)
class ClarityIssue:
    rule: str  # "a".."d"
    scene: str
    message: str

    def __str__(self) -> str:
        return f"[clarity {self.rule}] {self.scene}: {self.message}"


def normalize(text: str) -> str:
    """Casefold, drop punctuation, collapse whitespace."""
    return " ".join(_NON_WORD.sub(" ", text.casefold()).split())


def _has_icon(value: Any) -> bool:
    if isinstance(value, dict):
        return bool(value.get("icon")) or any(_has_icon(v) for v in value.values())
    if isinstance(value, list):
        return any(_has_icon(v) for v in value)
    return False


def is_concrete(scene: SceneSpec) -> bool:
    props = scene.props
    return bool(
        scene.template in CHART_TEMPLATES
        or props.get("side_icons")
        or props.get("icons")
        or props.get("icon")
        or _has_icon(props)
    )


def is_mascot_only(scene: SceneSpec) -> bool:
    return (
        scene.character.mascot == "on"
        and scene.template == "title_question"
        and not scene.props.get("side_icons")
    )


def check_clarity(
    spec: EpisodeSpec, scene_seconds: dict[str, float] | None = None
) -> list[ClarityIssue]:
    """All clarity issues in *spec*. *scene_seconds* (scene id → duration) overrides the
    duration estimate, e.g. from a real narration timing manifest."""
    issues: list[ClarityIssue] = []
    last = len(spec.scenes) - 1
    for index, scene in enumerate(spec.scenes):
        narration = normalize(scene.narration)
        for i, cap in enumerate(scene.captions):  # (a)
            if normalize(cap.text) not in narration:
                issues.append(
                    ClarityIssue(
                        "a",
                        scene.id,
                        f"caption {i} {cap.text!r} is not verbatim narration — split the "
                        "caption or change the narration, never paraphrase",
                    )
                )
        if index == 0 and not is_concrete(scene):  # (b)
            issues.append(
                ClarityIssue(
                    "b",
                    scene.id,
                    "first scene has no concrete element (side_icons, icons or a chart)",
                )
            )
        if index != last and is_mascot_only(scene):  # (c)
            seconds = (scene_seconds or {}).get(scene.id, estimate_scene_seconds(scene))
            if seconds > MASCOT_ONLY_MAX_SECONDS:
                issues.append(
                    ClarityIssue(
                        "c",
                        scene.id,
                        f"NODI alone for {seconds:.1f}s (max {MASCOT_ONLY_MAX_SECONDS:.0f}s) — "
                        "add side_icons or shorten",
                    )
                )
        if scene.template in EXPLANATION_TEMPLATES and not any(  # (d)
            isinstance(b.at, str) and b.at.startswith("word:") for b in scene.beats
        ):
            issues.append(
                ClarityIssue(
                    "d",
                    scene.id,
                    f"explanation scene ({scene.template}) has no word: beat — cue each "
                    "visual change on the spoken word",
                )
            )
    return issues


class ClarityGateError(RuntimeError):
    pass


def editorial_gate(spec: EpisodeSpec, scene_seconds: dict[str, float] | None = None) -> None:
    """Approved specs must be clarity-clean; drafts are only warned."""
    if spec.editorial_status != "approved":
        return
    issues = check_clarity(spec, scene_seconds)
    if issues:
        raise ClarityGateError(
            "Approved spec fails the clarity rules:\n- " + "\n- ".join(map(str, issues))
        )
