from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from clutchiq.timeline_engine.models import Participant, TimelineEvent, TimelineImport, TimelineMetadata


def test_timeline_models_are_frozen() -> None:
    metadata = TimelineMetadata()
    participant = Participant(participant_id=1)
    event = TimelineEvent(event_id="e1", tick=1, sequence=0, kind="kill.recorded")
    timeline = TimelineImport(metadata=metadata, participants=(participant,), events=(event,))

    with pytest.raises(FrozenInstanceError):
        metadata.schema_version = 2  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        participant.name = "alice"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        event.kind = "other"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        timeline.raw = {}  # type: ignore[misc]


def test_timeline_raw_payloads_are_independent_dicts() -> None:
    metadata_raw = {"source": "demo"}
    participant_raw = {"id": 1}
    event_raw = {"tick": 1}

    metadata = TimelineMetadata(raw=metadata_raw)
    participant = Participant(participant_id=1, raw=participant_raw)
    event = TimelineEvent(event_id="e1", tick=1, sequence=0, kind="event.recorded", raw=event_raw)

    assert metadata.raw is metadata_raw
    assert participant.raw is participant_raw
    assert event.raw is event_raw
