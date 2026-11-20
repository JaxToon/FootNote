from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class EpisodeMeta(StrictModel):
    id: str = Field(min_length=3, pattern=r"^[a-z0-9][a-z0-9-]*$")
    title: str = Field(min_length=3)
    series: str = Field(min_length=1)
    episode: str = Field(min_length=1)
    format: Literal["short", "long"]
    language: str = "id-ID"
    fps: int = Field(default=30, ge=1, le=120)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    paired_episode_id: str | None = None
    status: Literal["draft", "review", "approved"] = "draft"

    @model_validator(mode="after")
    def validate_aspect_ratio(self) -> EpisodeMeta:
        ratio = self.width / self.height
        if self.format == "short" and not (0.54 <= ratio <= 0.58):
            raise ValueError("Short format should use a 9:16 canvas (approximately 0.5625 ratio)")
        if self.format == "long" and not (1.75 <= ratio <= 1.80):
            raise ValueError("Long format should use a 16:9 canvas (approximately 1.7778 ratio)")
        return self


class VoiceConfig(StrictModel):
    provider: Literal["elevenlabs", "recorded", "none"] = "elevenlabs"
    voice_id: str | None = None
    speed: float = Field(default=1.0, ge=0.7, le=1.2)


class CaptionChunk(StrictModel):
    text: str = Field(min_length=1)
    highlight: list[str] = Field(default_factory=list)


class CharacterConfig(StrictModel):
    presenter: Literal["on", "off"] = "off"
    mascot: Literal["on", "off"] = "off"
    presenter_pose: str | None = None
    mascot_pose: str | None = None
    mascot_outfit: Literal["classic", "academic", "data_explorer", "creator", "career_ready"] = (
        "classic"
    )
    expression: str | None = None


ENTER_ACTIONS = ("pop", "slide", "draw", "count")
ELEMENT_ACTIONS = (*ENTER_ACTIONS, "highlight", "exit")
_AT_PATTERN = re.compile(r"^(caption:\d+|word:\S+)$")
_NODI_ACTION = re.compile(r"^(pose|expr):[a-z_]+$")


class Beat(StrictModel):
    """A cue: at a moment in the narration, do something to one on-screen element.

    at: "caption:<idx>" | "word:<word>" | fraction 0..1 of the scene duration.
    target: an element data-id from the scene template, or "nodi".
    action: pop | slide | draw | count | highlight | exit, or for NODI pose:<p> / expr:<e>.
    """

    at: str | float
    target: str = Field(min_length=1)
    action: str = Field(min_length=1)
    duration: float | None = Field(default=None, gt=0, le=5)

    @field_validator("at")
    @classmethod
    def _check_at(cls, value: str | float) -> str | float:
        if isinstance(value, int | float):
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError("numeric beat 'at' must be a fraction between 0 and 1")
            return float(value)
        if not _AT_PATTERN.match(value):
            raise ValueError("beat 'at' must be 'caption:<idx>', 'word:<word>' or 0..1")
        return value

    @model_validator(mode="after")
    def _check_action(self) -> Beat:
        if self.target == "nodi":
            if not _NODI_ACTION.match(self.action):
                raise ValueError("NODI beats use action 'pose:<pose>' or 'expr:<expression>'")
        elif self.action not in ELEMENT_ACTIONS:
            raise ValueError(f"beat action must be one of {', '.join(ELEMENT_ACTIONS)}")
        return self


class Hold(StrictModel):
    """An intentional visual hold (fractions of the scene) excused from the motion QA."""

    start: float = Field(ge=0, le=1)
    end: float = Field(ge=0, le=1)
    reason: str = Field(min_length=3)

    @model_validator(mode="after")
    def _ordered(self) -> Hold:
        if self.end <= self.start:
            raise ValueError("hold end must be after start")
        return self


class SceneSpec(StrictModel):
    id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9-]*$")
    title: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    narration: str = Field(min_length=1)
    captions: list[CaptionChunk] = Field(min_length=1)
    character: CharacterConfig = Field(default_factory=CharacterConfig)
    background: str = "navy"
    template: str = Field(min_length=1)
    props: dict[str, Any] = Field(default_factory=dict)
    duration_hint_seconds: float | None = Field(default=None, gt=0)
    source_notes: list[str] = Field(default_factory=list)
    beats: list[Beat] = Field(default_factory=list)
    holds: list[Hold] = Field(default_factory=list)

    @model_validator(mode="after")
    def _caption_beats_exist(self) -> SceneSpec:
        for beat in self.beats:
            if isinstance(beat.at, str) and beat.at.startswith("caption:"):
                if int(beat.at.split(":", 1)[1]) >= len(self.captions):
                    raise ValueError(f"scene {self.id}: beat refers to missing {beat.at}")
        return self


CURRENT_SCHEMA_VERSION = 2


class EpisodeSpec(StrictModel):
    schema_version: Literal[2] = CURRENT_SCHEMA_VERSION
    meta: EpisodeMeta
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    editorial_status: Literal["draft", "needs_review", "approved"] = "draft"
    sources: list[str] = Field(default_factory=list)
    scenes: list[SceneSpec] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_scene_ids(self) -> EpisodeSpec:
        ids = [scene.id for scene in self.scenes]
        if len(ids) != len(set(ids)):
            raise ValueError("Scene IDs must be unique within an episode")
        return self
