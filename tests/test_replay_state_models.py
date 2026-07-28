from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from clutchiq.replay_state.models import ReplayProvenance, ReplaySnapshot, ReplayState
from clutchiq.timeline_engine.models import Participant, TimelineEvent, TimelineMetadata


def test_replay_models_are_frozen() -> None:
    provenance = ReplayProvenance(timeline_id=None, timeline_schema_version=1, ruleset_version="v1")
    snapshot = ReplaySnapshot(tick=10, provenance=provenance, applied_event_count=0)
    metadata = TimelineMetadata()
    participant = Participant(participant_id=1)
    event = TimelineEvent(event_id="e1", tick=1, sequence=0, kind="event.recorded")
    state = ReplayState(
        snapshot=snapshot,
        metadata=metadata,
        participants=(participant,),
        applied_events=(event,),
    )

    with pytest.raises(FrozenInstanceError):
        provenance.ruleset_version = "v2"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        snapshot.tick = 11  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        state.metadata = TimelineMetadata()  # type: ignore[misc]


def test_replay_state_preserves_values() -> None:
    provenance = ReplayProvenance(timeline_id="timeline-000001", timeline_schema_version=1, ruleset_version="v1")
    snapshot = ReplaySnapshot(tick=42, provenance=provenance, applied_event_count=3)
    metadata = TimelineMetadata(map_name="de_dust2")
    participant = Participant(participant_id=7, name="alice")
    event = TimelineEvent(event_id="e1", tick=1, sequence=0, kind="event.recorded")

    state = ReplayState(
        snapshot=snapshot,
        metadata=metadata,
        participants=(participant,),
        applied_events=(event,),
    )

    assert state.snapshot.tick == 42
    assert state.snapshot.provenance.timeline_id == "timeline-000001"
    assert state.participants[0].name == "alice"
    assert state.applied_events[0].event_id == "e1"
