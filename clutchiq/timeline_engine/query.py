"""Timeline query models."""

from __future__ import annotations

from dataclasses import dataclass, field

from clutchiq.timeline_engine.models import Clutch, ClutchDetectionConfig, EventKind, Tick, TimelineEvent, TimelineId, Trade, TradeDetectionConfig

Cursor = str


@dataclass(frozen=True, slots=True)
class EventQuery:
    """Minimal event query."""

    start_tick: Tick | None = None
    end_tick: Tick | None = None
    kinds: tuple[EventKind, ...] | None = None
    limit: int | None = None
    cursor: Cursor | None = None


@dataclass(frozen=True, slots=True)
class EventPage:
    """Page of events."""

    items: tuple[TimelineEvent, ...]
    next_cursor: Cursor | None = None


@dataclass(frozen=True, slots=True)
class TradeQuery:
    """A request to detect trades in one stored timeline."""

    timeline_id: TimelineId
    config: TradeDetectionConfig = field(default_factory=TradeDetectionConfig)
    round_numbers: tuple[int, ...] | None = None


@dataclass(frozen=True, slots=True)
class TradeResult:
    """Detected trades and the number of safely ignored source records."""

    trades: tuple[Trade, ...]
    skipped_unknown: int = 0
    skipped_conflicting: int = 0
    skipped_duplicate: int = 0
    skipped_malformed: int = 0


@dataclass(frozen=True, slots=True)
class ClutchQuery:
    """A request to detect clutches in one stored timeline."""

    timeline_id: TimelineId
    config: ClutchDetectionConfig = field(default_factory=ClutchDetectionConfig)
    round_numbers: tuple[int, ...] | None = None


@dataclass(frozen=True, slots=True)
class ClutchResult:
    """Detected clutches and the number of safely ignored source records."""

    clutches: tuple[Clutch, ...]
    skipped_unknown: int = 0
    skipped_conflicting: int = 0
    skipped_duplicate: int = 0
    skipped_malformed: int = 0
