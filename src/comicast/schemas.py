"""Pydantic schemas — single source of truth for every JSON contract."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class BubbleType(StrEnum):
    DIALOGUE = "dialogue"
    THOUGHT = "thought"
    NARRATION = "narration"
    SFX = "sfx"


# Reserved speaker ids — never collide with character ids
RESERVED_SPEAKER_IDS = {"__narrator__", "__sfx__"}


Bbox = Annotated[tuple[int, int, int, int], Field(description="(x1, y1, x2, y2) in page pixels")]
Confidence = Annotated[float, Field(ge=0.0, le=1.0)]


class Bubble(BaseModel):
    """A single speech/thought/narration/sfx unit on a page."""

    model_config = ConfigDict(frozen=False, extra="forbid")

    text: str = Field(min_length=1)
    speaker_id: str = Field(min_length=1)
    emotion: str = Field(default="neutral")
    type: BubbleType
    bbox: Bbox
    confidence: Confidence

    @model_validator(mode="after")
    def _sfx_uses_reserved_speaker(self) -> Bubble:
        if self.type is BubbleType.SFX and self.speaker_id != "__sfx__":
            raise ValueError(f"SFX bubble must use speaker_id='__sfx__', got {self.speaker_id!r}")
        return self


class Panel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order: int = Field(ge=1, description="Reading order within a page (1-based)")
    bubbles: list[Bubble]


class PageScript(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int = Field(ge=1)
    panels: list[Panel]


class ScriptFile(BaseModel):
    """Top-level script.json — the output of Pass 2b."""

    model_config = ConfigDict(extra="forbid")

    series_name: str
    volume_id: str
    pages: list[PageScript]


class CastEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9_]+$", description="Snake-case stable id")
    canonical_name: str
    aliases: list[str] = Field(default_factory=list)
    description: str = Field(min_length=10)
    confidence: Confidence = 1.0
    voice_id: str | None = None
    voice_archetype: str | None = None
    user_confirmations: int = 0
    user_corrections: int = 0


class CastFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    series_name: str
    cast: list[CastEntry]


class Flag(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int = Field(ge=1)
    panel: int = Field(ge=1)
    issue: str = Field(min_length=5)
    severity: Literal["low", "medium", "high"]
    suggestion: str | None = None


class FlagsFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    series_name: str
    volume_id: str
    flags: list[Flag] = Field(default_factory=list)


class SeriesProfile(BaseModel):
    """Persistent per-series memory (the self-improving asset)."""

    model_config = ConfigDict(extra="forbid")

    series_name: str
    version: int = 0
    volumes_processed: list[str] = Field(default_factory=list)
    cast: list[CastEntry] = Field(default_factory=list)
    common_errors_learned: list[str] = Field(default_factory=list)
    voice_archetype_library: dict[str, str] = Field(default_factory=dict)

    @field_validator("cast")
    @classmethod
    def cast_ids_unique(cls, v: list[CastEntry]) -> list[CastEntry]:
        ids = [c.id for c in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate cast ids")
        return v
