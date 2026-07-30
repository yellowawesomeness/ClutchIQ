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


@dataclass(frozen=True, slots=True)
class TradeDetectionConfig:
    """Rules used to identify a retaliation trade."""

    window_ticks: int = 128

    def __post_init__(self) -> None:
        if isinstance(self.window_ticks, bool) or not isinstance(self.window_ticks, int) or self.window_ticks < 0:
            raise ValueError("window_ticks must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class Trade:
    """Two one-to-one matched kill events comprising a trade."""

    death_event_id: str
    retaliation_event_id: str
    round_number: int
    original_killer_player_id: int
    original_victim_player_id: int
    death_tick: Tick
    retaliation_tick: Tick


@dataclass(frozen=True, slots=True)
class ClutchDetectionConfig:
    """Rules used to identify a clutch entry."""

    minimum_opponents: int = 1

    def __post_init__(self) -> None:
        if isinstance(self.minimum_opponents, bool) or not isinstance(self.minimum_opponents, int) or self.minimum_opponents < 1:
            raise ValueError("minimum_opponents must be a positive integer")


@dataclass(frozen=True, slots=True)
class Clutch:
    """A successful transition to one surviving player followed by a round win."""

    round_number: int
    survivor_player_id: int
    survivor_team: int
    opponents_at_start: int
    start_event_id: str
    start_tick: Tick
    outcome_event_id: str
    outcome_tick: Tick
