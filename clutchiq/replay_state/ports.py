"""Ports for replay state reconstruction."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from clutchiq.timeline_engine.models import Tick, TimelineId, TimelineMetadata
from clutchiq.timeline_engine.ports import TimelineReader
from clutchiq.replay_state.models import ReplayState


@runtime_checkable
class ReplayStateSource(Protocol):
    def open(self, timeline_id: TimelineId) -> TimelineReader:
        ...


@runtime_checkable
class ReplaySession(Protocol):
    @property
    def metadata(self) -> TimelineMetadata:
        ...

    def state_at(self, tick: Tick) -> ReplayState:
        ...
