"""Clarity lint (CLAUDE.md "Clarity rules", docs/HANDOFF_CLARITY.md).

Mechanical checks for the storytelling rules that can be verified from a spec alone:

(a) captions are the narration, verbatim (ignoring case and punctuation)
(b) the first scene shows something concrete (side icons, icons, or a chart)
(c) a mascot-only scene (title_question without side_icons) lasts at most 2 s, except the close
(d) every explanation scene has at least one `word:` beat

`validate` reports these as warnings; for `editorial_status: approved` specs they are errors
that block TTS and render (see `editorial_gate`).

Beat order (`beat_order_warnings`, warning only): an element that depends on another one
(the ✕ on the false link, an arrow leaving its cause, the X–Y link) must not be scheduled
before or at the same time as the element it depends on. A `word:` cue on the narration's
first word resolves to t=0, which is a common way to get this wrong.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from fnvideo.audio.timing import caption_timings, estimate_scene_seconds, resolve_beats
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


# dependent element -> the elements it visually depends on (template element ids)
BEAT_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "false-x": ("false-link",),  # causal_diagram: the cross needs the link it crosses
    "arrow-1": ("node-0",),  # causal_diagram: arrows leave the cause
    "arrow-2": ("node-0",),
    "arrow-zx": ("z", "x"),  # definition_card.diagram
    "arrow-zy": ("z", "y"),
    "xy": ("x", "y"),
    "link-0": ("item-0",),  # question_link
    "link-1": ("item-1",),
    "trend": ("chart",),  # scatter_regression: the fit needs its points
    "conclusion": ("chart-0", "chart-1", "chart"),  # a chart's "so what" needs the chart
    "r": ("chart-0", "chart-1"),
}
ENTRY_ACTIONS = {"pop", "slide", "draw", "count"}
# container -> its content; a container must not sit empty on screen
BEAT_CONTAINERS: dict[str, tuple[str, ...]] = {"card": ("term", "definition")}
MAX_EMPTY_SECONDS = 1.0


@dataclass(frozen=True)
class BeatOrderWarning:
    scene: str
    dependent: str
    source: str
    dependent_t: float
    source_t: float
    dependent_at: str

    def __str__(self) -> str:
        if self.dependent in BEAT_CONTAINERS:
            return (
                f"[beat order] {self.scene}: {self.dependent} ({self.dependent_at} → "
                f"{self.dependent_t:.2f}s) is empty until {self.source} ({self.source_t:.2f}s) — "
                "cue it with its content"
            )
        return (
            f"[beat order] {self.scene}: {self.dependent} ({self.dependent_at} → "
            f"{self.dependent_t:.2f}s) is scheduled at or before {self.source} "
            f"({self.source_t:.2f}s) — cue it after the element it depends on"
        )


def _entry_times(scene: SceneSpec) -> dict[str, tuple[float, str]]:
    """Earliest entry time (s, estimated timing) and its authored cue, per beat target."""
    speech = estimate_scene_seconds(scene)
    caps = caption_timings(scene, speech, None)
    times: dict[str, tuple[float, str]] = {}
    for beat in scene.beats:
        if beat.action not in ENTRY_ACTIONS:
            continue
        one = scene.model_copy(update={"beats": [beat]})
        t = float(resolve_beats(one, speech, speech, caps, None)[0]["t"])
        if beat.target not in times or t < times[beat.target][0]:
            times[beat.target] = (t, str(beat.at))
    return times


def beat_order_warnings(spec: EpisodeSpec) -> list[BeatOrderWarning]:
    """Dependent elements cued before or together with what they depend on."""
    warnings: list[BeatOrderWarning] = []
    for scene in spec.scenes:
        times = _entry_times(scene)
        for dep, sources in BEAT_DEPENDENCIES.items():
            if dep not in times:
                continue
            dep_t, dep_at = times[dep]
            for src in sources:
                if src in times and dep_t <= times[src][0]:
                    warnings.append(
                        BeatOrderWarning(scene.id, dep, src, dep_t, times[src][0], dep_at)
                    )
        for box, content in BEAT_CONTAINERS.items():
            filled = [(times[c][0], c) for c in content if c in times]
            if box in times and filled:
                first_t, first = min(filled)
                if first_t - times[box][0] > MAX_EMPTY_SECONDS:
                    box_t, box_at = times[box]
                    warnings.append(BeatOrderWarning(scene.id, box, first, box_t, first_t, box_at))
    return warnings
