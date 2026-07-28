"""Replay state service facade."""

from __future__ import annotations

from dataclasses import dataclass

from clutchiq.timeline_engine.models import Tick, TimelineId, TimelineMetadata
from clutchiq.timeline_engine.ports import TimelineReader
from clutchiq.replay_state.models import ReplayState
from clutchiq.replay_state.ports import ReplaySession, ReplayStateSource
from clutchiq.replay_state.reducer import replay_to_tick
from clutchiq.replay_state.validation import validate_replay_tick


@dataclass(frozen=True, slots=True)
class ReplayStateService:
    source: ReplayStateSource

    def open(self, timeline_id: TimelineId) -> ReplaySession:
        return _TimelineReplaySession(reader=self.source.open(timeline_id), timeline_id=timeline_id)


@dataclass(frozen=True, slots=True)
class _TimelineReplaySession(ReplaySession):
    reader: TimelineReader
    timeline_id: TimelineId

    @property
    def metadata(self) -> TimelineMetadata:
        return self.reader.metadata

    def state_at(self, tick: Tick) -> ReplayState:
        validate_replay_tick(tick)
        return replay_to_tick(self.reader, tick, timeline_id=self.timeline_id)
