"""In-memory timeline repository."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from clutchiq.timeline_engine.models import Participant, TimelineEvent, TimelineId, TimelineImport, TimelineMetadata
from clutchiq.timeline_engine.ports import TimelineReader, TimelineRepository
from clutchiq.timeline_engine.query import EventPage, EventQuery
from clutchiq.timeline_engine.validation import validate_timeline_import


def _copy_raw(value: dict[str, Any]) -> dict[str, Any]:
    return dict(value)


def _cursor_from_index(index: int) -> str:
    return f"idx:{index}"


def _index_from_cursor(cursor: str) -> int:
    if not cursor.startswith("idx:"):
        raise ValueError("invalid cursor format")
    try:
        index = int(cursor.removeprefix("idx:"))
    except ValueError as exc:
        raise ValueError("invalid cursor format") from exc
    if index < 0:
        raise ValueError("cursor index must be non-negative")
    return index


@dataclass(frozen=True, slots=True)
class _InMemoryTimelineReader:
    metadata: TimelineMetadata
    _participants: tuple[Participant, ...]
    _events: tuple[TimelineEvent, ...]

    def participants(self) -> tuple[Participant, ...]:
        return self._participants

    def events(self, query: EventQuery) -> EventPage:
        if query.start_tick is not None and query.start_tick < 0:
            raise ValueError("start_tick must be non-negative")
        if query.end_tick is not None and query.end_tick < 0:
            raise ValueError("end_tick must be non-negative")
        if query.start_tick is not None and query.end_tick is not None and query.start_tick > query.end_tick:
            raise ValueError("start_tick must be less than or equal to end_tick")
        if query.limit is not None and query.limit <= 0:
            raise ValueError("limit must be positive")

        events = self._events
        if query.start_tick is not None:
            events = tuple(event for event in events if event.tick >= query.start_tick)
        if query.end_tick is not None:
            events = tuple(event for event in events if event.tick < query.end_tick)
        if query.kinds is not None:
            allowed = set(query.kinds)
            events = tuple(event for event in events if event.kind in allowed)

        start_index = 0
        if query.cursor is not None:
            start_index = _index_from_cursor(query.cursor)
            if start_index > len(events):
                return EventPage(items=(), next_cursor=None)

        limited = events[start_index:]
        next_cursor = None
        if query.limit is not None:
            limited = limited[: query.limit]
            if start_index + len(limited) < len(events):
                next_cursor = _cursor_from_index(start_index + len(limited))
        return EventPage(items=limited, next_cursor=next_cursor)


@dataclass(slots=True)
class InMemoryTimelineRepository(TimelineRepository):
    _store: dict[TimelineId, _InMemoryTimelineReader] = field(default_factory=dict)
    _counter: int = 0

    def save(self, timeline: TimelineImport) -> TimelineId:
        validate_timeline_import(timeline)
        self._counter += 1
        timeline_id = f"timeline-{self._counter:06d}"

        participants = tuple(
            Participant(
                participant_id=participant.participant_id,
                name=participant.name,
                steam_id=participant.steam_id,
                team=participant.team,
                side=participant.side,
                raw=_copy_raw(participant.raw),
            )
            for participant in timeline.participants
        )
        events = tuple(
            sorted(
                (
                    TimelineEvent(
                        event_id=event.event_id,
                        tick=event.tick,
                        sequence=event.sequence,
                        kind=event.kind,
                        round_number=event.round_number,
                        participant_id=event.participant_id,
                        raw=_copy_raw(event.raw),
                    )
                    for event in timeline.events
                ),
                key=lambda event: (event.tick, event.sequence, event.event_id),
            )
        )
        metadata = TimelineMetadata(
            schema_version=timeline.metadata.schema_version,
            source_name=timeline.metadata.source_name,
            source_digest=timeline.metadata.source_digest,
            map_name=timeline.metadata.map_name,
            tick_rate=timeline.metadata.tick_rate,
            raw=_copy_raw(timeline.metadata.raw),
        )
        self._store[timeline_id] = _InMemoryTimelineReader(
            metadata=metadata,
            _participants=participants,
            _events=events,
        )
        return timeline_id

    def open(self, timeline_id: TimelineId) -> TimelineReader:
        try:
            return self._store[timeline_id]
        except KeyError as exc:
            raise KeyError(f"unknown timeline_id: {timeline_id}") from exc
