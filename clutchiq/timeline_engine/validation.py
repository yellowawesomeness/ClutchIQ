"""Validation helpers for timeline imports."""

from __future__ import annotations

from collections.abc import Mapping

from clutchiq.timeline_engine.models import TimelineImport


def validate_timeline_import(timeline: TimelineImport) -> None:
    if timeline is None:
        raise ValueError("timeline import is required")

    if not isinstance(timeline.metadata.raw, Mapping):
        raise TypeError("timeline metadata raw payload must be a mapping")

    if not isinstance(timeline.participants, tuple):
        raise TypeError("timeline participants must be a tuple")
    if not isinstance(timeline.events, tuple):
        raise TypeError("timeline events must be a tuple")

    event_ids: set[str] = set()
    for participant in timeline.participants:
        if participant.participant_id < 0:
            raise ValueError("participant_id must be non-negative")
        if not isinstance(participant.raw, Mapping):
            raise TypeError("participant raw payload must be a mapping")

    for event in timeline.events:
        if not event.event_id:
            raise ValueError("event_id must be a non-empty string")
        if event.event_id in event_ids:
            raise ValueError(f"duplicate event_id: {event.event_id}")
        event_ids.add(event.event_id)
        if event.tick < 0:
            raise ValueError("event tick must be non-negative")
        if event.sequence < 0:
            raise ValueError("event sequence must be non-negative")
        if not event.kind:
            raise ValueError("event kind must be a non-empty string")
        if not isinstance(event.raw, Mapping):
            raise TypeError("event raw payload must be a mapping")
