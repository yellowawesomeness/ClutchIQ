"""Frozen replay state models."""

from __future__ import annotations

from dataclasses import dataclass

from clutchiq.timeline_engine.models import Participant, Tick, TimelineEvent, TimelineId, TimelineMetadata


@dataclass(frozen=True, slots=True)
class ReplayProvenance:
    timeline_id: TimelineId | None
    timeline_schema_version: int
    ruleset_version: str


@dataclass(frozen=True, slots=True)
class ReplaySnapshot:
    tick: Tick
    provenance: ReplayProvenance
    applied_event_count: int


@dataclass(frozen=True, slots=True)
class ReplayState:
    snapshot: ReplaySnapshot
    metadata: TimelineMetadata
    participants: tuple[Participant, ...]
    applied_events: tuple[TimelineEvent, ...]
