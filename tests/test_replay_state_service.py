from __future__ import annotations

from dataclasses import dataclass

from clutchiq.replay_state.service import ReplayStateService
from clutchiq.timeline_engine.models import Participant, TimelineEvent, TimelineImport, TimelineMetadata
from clutchiq.timeline_engine.repository import InMemoryTimelineRepository


@dataclass(frozen=True, slots=True)
class _Source:
    repository: InMemoryTimelineRepository

    def open(self, timeline_id):
        return self.repository.open(timeline_id)


def _service():
    repo = InMemoryTimelineRepository()
    timeline_id = repo.save(
        TimelineImport(
            metadata=TimelineMetadata(map_name="de_dust2"),
            participants=(Participant(participant_id=1, name="alice"),),
            events=(
                TimelineEvent(event_id="e1", tick=10, sequence=0, kind="event.recorded"),
                TimelineEvent(event_id="e2", tick=20, sequence=0, kind="event.recorded"),
            ),
        )
    )
    return ReplayStateService(source=_Source(repo)), timeline_id


def test_state_at_before_first_event_is_empty_but_stable() -> None:
    service, timeline_id = _service()
    session = service.open(timeline_id)

    first = session.state_at(0)
    second = session.state_at(0)

    assert first == second
    assert first.snapshot.tick == 0
    assert first.snapshot.applied_event_count == 0
    assert first.applied_events == ()
    assert first.snapshot.provenance.timeline_id == timeline_id
    assert first.snapshot.provenance.timeline_schema_version == 1
    assert first.snapshot.provenance.ruleset_version == "v1"


def test_state_at_exact_event_tick_includes_that_event() -> None:
    service, timeline_id = _service()
    session = service.open(timeline_id)

    state = session.state_at(10)

    assert state.snapshot.tick == 10
    assert state.snapshot.applied_event_count == 1
    assert [event.event_id for event in state.applied_events] == ["e1"]
    assert state.snapshot.provenance.timeline_id == timeline_id


def test_state_at_between_events_includes_prior_events_only() -> None:
    service, timeline_id = _service()
    session = service.open(timeline_id)

    state = session.state_at(15)

    assert state.snapshot.tick == 15
    assert state.snapshot.applied_event_count == 1
    assert [event.event_id for event in state.applied_events] == ["e1"]
    assert state.snapshot.provenance.timeline_id == timeline_id


def test_state_at_after_last_event_includes_all_events() -> None:
    service, timeline_id = _service()
    session = service.open(timeline_id)

    state = session.state_at(999)

    assert state.snapshot.tick == 999
    assert state.snapshot.applied_event_count == 2
    assert [event.event_id for event in state.applied_events] == ["e1", "e2"]
    assert state.snapshot.provenance.timeline_id == timeline_id


def test_repeated_queries_are_deterministic() -> None:
    service, timeline_id = _service()
    session = service.open(timeline_id)

    first = session.state_at(20)
    second = session.state_at(20)

    assert first == second
    assert first.snapshot == second.snapshot
    assert first.snapshot.provenance == second.snapshot.provenance
