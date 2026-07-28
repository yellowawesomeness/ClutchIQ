from __future__ import annotations

import pytest

from clutchiq.timeline_engine.models import TimelineEvent
from clutchiq.timeline_engine.query import EventPage, EventQuery
from clutchiq.timeline_engine.repository import InMemoryTimelineRepository
from clutchiq.timeline_engine.models import Participant, TimelineImport, TimelineMetadata


def test_event_query_boundaries_and_limit_validation() -> None:
    repo = InMemoryTimelineRepository()
    timeline_id = repo.save(
        TimelineImport(
            metadata=TimelineMetadata(),
            participants=(),
            events=(TimelineEvent(event_id="e1", tick=1, sequence=0, kind="event.recorded"),),
        )
    )
    reader = repo.open(timeline_id)

    with pytest.raises(ValueError):
        reader.events(EventQuery(start_tick=-1))
    with pytest.raises(ValueError):
        reader.events(EventQuery(end_tick=-1))
    with pytest.raises(ValueError):
        reader.events(EventQuery(start_tick=5, end_tick=4))
    with pytest.raises(ValueError):
        reader.events(EventQuery(limit=0))


def test_event_page_is_imported_and_constructible() -> None:
    page = EventPage(items=())
    assert page.items == ()
