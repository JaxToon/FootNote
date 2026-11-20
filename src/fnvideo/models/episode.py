from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    def validate_aspect_ratio(self) -> "EpisodeMeta":
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
    mascot_outfit: Literal["classic", "academic", "data_explorer", "creator", "career_ready"] = "classic"
    expression: str | None = None


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


class EpisodeSpec(StrictModel):
    schema_version: Literal[1] = 1
    meta: EpisodeMeta
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    editorial_status: Literal["draft", "needs_review", "approved"] = "draft"
    sources: list[str] = Field(default_factory=list)
    scenes: list[SceneSpec] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_scene_ids(self) -> "EpisodeSpec":
        ids = [scene.id for scene in self.scenes]
        if len(ids) != len(set(ids)):
            raise ValueError("Scene IDs must be unique within an episode")
        return self
