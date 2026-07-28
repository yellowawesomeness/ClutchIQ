"""Immutable core models for the timeline engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

TimelineId = str
Tick = int
SequenceNumber = int
EventKind = str


@dataclass(frozen=True, slots=True)
class TimelineMetadata:
    """Canonical metadata for a stored timeline."""

    schema_version: int = 1
    source_name: str | None = None
    source_digest: str | None = None
    map_name: str | None = None
    tick_rate: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Participant:
    """A participant known to the timeline."""

    participant_id: int
    name: str | None = None
    steam_id: int | None = None
    team: str | None = None
    side: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TimelineEvent:
    """A raw canonical timeline event."""

    event_id: str
    tick: Tick
    sequence: SequenceNumber
    kind: EventKind
    round_number: int | None = None
    participant_id: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TimelineImport:
    """Input payload for storing a timeline."""

    metadata: TimelineMetadata
    participants: tuple[Participant, ...] = ()
    events: tuple[TimelineEvent, ...] = ()
    raw: dict[str, Any] = field(default_factory=dict)
