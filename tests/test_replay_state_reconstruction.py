from __future__ import annotations

from dataclasses import dataclass

import pytest

from clutchiq.replay_state.reducer import replay_to_tick
from clutchiq.timeline_engine.models import Participant, TimelineEvent, TimelineImport, TimelineMetadata
from clutchiq.timeline_engine.query import EventPage
from clutchiq.timeline_engine.repository import InMemoryTimelineRepository


def _reader():
    repo = InMemoryTimelineRepository()
    timeline_id = repo.save(
        TimelineImport(
            metadata=TimelineMetadata(map_name="de_dust2"),
            participants=(Participant(participant_id=1, name="alice"),),
            events=(
                TimelineEvent(event_id="e1", tick=1, sequence=0, kind="event.recorded"),
                TimelineEvent(event_id="e2", tick=3, sequence=0, kind="event.recorded"),
            ),
        )
    )
    return repo.open(timeline_id), timeline_id


def test_state_at_includes_events_up_to_requested_tick() -> None:
    reader, _ = _reader()
    state = replay_to_tick(reader, 3)

    assert state.snapshot.tick == 3
    assert [event.event_id for event in state.applied_events] == ["e1", "e2"]


def test_state_at_preserves_requested_tick_when_no_event_occurs_there() -> None:
    reader, _ = _reader()
    state = replay_to_tick(reader, 2)

    assert state.snapshot.tick == 2
    assert [event.event_id for event in state.applied_events] == ["e1"]


def test_reconstruction_is_deterministic() -> None:
    reader, _ = _reader()

    first = replay_to_tick(reader, 3)
    second = replay_to_tick(reader, 3)

    assert first == second


@dataclass(frozen=True, slots=True)
class _CyclingReader:
    metadata: TimelineMetadata = TimelineMetadata()

    def participants(self):
        return ()

    def events(self, query):
        if query.cursor is None:
            return EventPage(items=(), next_cursor="A")
        if query.cursor == "A":
            return EventPage(items=(), next_cursor="A")
        raise AssertionError("unexpected cursor")


def test_replay_to_tick_rejects_unchanged_cursor_cycle() -> None:
    reader = _CyclingReader()

    with pytest.raises(ValueError, match="pagination cursor cycle detected"):
        replay_to_tick(reader, 3)


@dataclass(frozen=True, slots=True)
class _NonconsecutiveCyclingReader:
    metadata: TimelineMetadata = TimelineMetadata()

    def participants(self):
        return ()

    def events(self, query):
        if query.cursor is None:
            return EventPage(items=(), next_cursor="A")
        if query.cursor == "A":
            return EventPage(items=(), next_cursor="B")
        if query.cursor == "B":
            return EventPage(items=(), next_cursor="A")
        raise AssertionError("unexpected cursor")


def test_replay_to_tick_rejects_nonconsecutive_cursor_cycle() -> None:
    reader = _NonconsecutiveCyclingReader()

    with pytest.raises(ValueError, match="pagination cursor cycle detected"):
        replay_to_tick(reader, 3)
