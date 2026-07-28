"""Timeline query models."""

from __future__ import annotations

from dataclasses import dataclass

from clutchiq.timeline_engine.models import EventKind, Tick, TimelineEvent

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
