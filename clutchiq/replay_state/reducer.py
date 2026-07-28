"""Deterministic replay reconstruction."""

from __future__ import annotations

from dataclasses import replace

from clutchiq.timeline_engine.models import Participant, Tick, TimelineEvent, TimelineId, TimelineMetadata
from clutchiq.timeline_engine.query import EventQuery
from clutchiq.timeline_engine.ports import TimelineReader
from clutchiq.replay_state.models import ReplayProvenance, ReplaySnapshot, ReplayState
from clutchiq.replay_state.validation import validate_replay_tick


def initial_replay_state(
    metadata: TimelineMetadata,
    participants: tuple[Participant, ...],
    tick: Tick,
    timeline_id: TimelineId | None,
) -> ReplayState:
    validate_replay_tick(tick)
    provenance = ReplayProvenance(
        timeline_id=timeline_id,
        timeline_schema_version=metadata.schema_version,
        ruleset_version="v1",
    )
    snapshot = ReplaySnapshot(tick=tick, provenance=provenance, applied_event_count=0)
    return ReplayState(
        snapshot=snapshot,
        metadata=metadata,
        participants=participants,
        applied_events=(),
    )


def apply_event(state: ReplayState, event: TimelineEvent) -> ReplayState:
    applied_events = state.applied_events + (event,)
    snapshot = ReplaySnapshot(
        tick=state.snapshot.tick,
        provenance=state.snapshot.provenance,
        applied_event_count=len(applied_events),
    )
    return ReplayState(
        snapshot=snapshot,
        metadata=state.metadata,
        participants=state.participants,
        applied_events=applied_events,
    )


def replay_to_tick(reader: TimelineReader, tick: Tick, timeline_id: TimelineId | None = None) -> ReplayState:
    validate_replay_tick(tick)
    state = initial_replay_state(
        reader.metadata,
        reader.participants(),
        tick=tick,
        timeline_id=timeline_id,
    )
    for event in _fetch_all_events(reader, tick):
        state = apply_event(state, event)
    return state


def _fetch_all_events(reader: TimelineReader, tick: Tick) -> tuple[TimelineEvent, ...]:
    query = EventQuery(end_tick=tick + 1)
    items: list[TimelineEvent] = []
    cursor = None
    seen_cursors: set[str | None] = {None}

    while True:
        page = reader.events(query if cursor is None else replace(query, cursor=cursor))
        items.extend(page.items)
        if page.next_cursor is None:
            break
        if page.next_cursor in seen_cursors:
            raise ValueError("pagination cursor cycle detected")
        if page.next_cursor == cursor:
            raise ValueError("pagination cursor did not advance")
        seen_cursors.add(page.next_cursor)
        cursor = page.next_cursor

    return tuple(items)
