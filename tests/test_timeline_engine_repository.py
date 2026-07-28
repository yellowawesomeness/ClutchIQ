from __future__ import annotations

import pytest

from clutchiq.timeline_engine.models import Participant, TimelineEvent, TimelineImport, TimelineMetadata
from clutchiq.timeline_engine.query import EventQuery
from clutchiq.timeline_engine.repository import InMemoryTimelineRepository


def _timeline() -> TimelineImport:
    return TimelineImport(
        metadata=TimelineMetadata(map_name="de_dust2"),
        participants=(Participant(participant_id=1, name="alice"),),
        events=(
            TimelineEvent(event_id="e2", tick=2, sequence=1, kind="kill.recorded", raw={"x": 2}),
            TimelineEvent(event_id="e1", tick=1, sequence=0, kind="round.recorded", raw={"x": 1}),
            TimelineEvent(event_id="e3", tick=2, sequence=0, kind="event.recorded", raw={"x": 3}),
        ),
        raw={"source": "demo"},
    )


def test_repository_saves_and_opens_timelines() -> None:
    repo = InMemoryTimelineRepository()
    timeline_id = repo.save(_timeline())

    assert timeline_id == "timeline-000001"
    reader = repo.open(timeline_id)
    assert reader.metadata.map_name == "de_dust2"
    assert reader.participants()[0].name == "alice"


def test_repository_orders_events_by_tick_sequence_and_event_id() -> None:
    repo = InMemoryTimelineRepository()
    reader = repo.open(repo.save(_timeline()))

    assert [event.event_id for event in reader.events(EventQuery()).items] == ["e1", "e3", "e2"]


def test_repository_filters_events_by_tick_range_and_kind() -> None:
    repo = InMemoryTimelineRepository()
    reader = repo.open(repo.save(_timeline()))

    page = reader.events(EventQuery(start_tick=2, end_tick=3, kinds=("kill.recorded",)))
    assert [event.event_id for event in page.items] == ["e2"]


def test_repository_cursor_paging_is_deterministic() -> None:
    repo = InMemoryTimelineRepository()
    reader = repo.open(repo.save(_timeline()))

    first_page = reader.events(EventQuery(limit=2))
    assert [event.event_id for event in first_page.items] == ["e1", "e3"]
    assert first_page.next_cursor == "idx:2"

    second_page = reader.events(EventQuery(limit=2, cursor=first_page.next_cursor))
    assert [event.event_id for event in second_page.items] == ["e2"]
    assert second_page.next_cursor is None


def test_repository_rejects_duplicate_event_ids() -> None:
    repo = InMemoryTimelineRepository()
    timeline = TimelineImport(
        metadata=TimelineMetadata(),
        events=(
            TimelineEvent(event_id="dup", tick=1, sequence=0, kind="event.recorded"),
            TimelineEvent(event_id="dup", tick=2, sequence=0, kind="event.recorded"),
        ),
    )

    with pytest.raises(ValueError):
        repo.save(timeline)
