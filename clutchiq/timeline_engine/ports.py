"""Ports for timeline engine storage and reading."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from clutchiq.timeline_engine.models import Participant, TimelineId, TimelineImport, TimelineMetadata
from clutchiq.timeline_engine.query import EventPage, EventQuery


@runtime_checkable
class TimelineReader(Protocol):
    @property
    def metadata(self) -> TimelineMetadata:
        ...

    def participants(self) -> tuple[Participant, ...]:
        ...

    def events(self, query: EventQuery) -> EventPage:
        ...


@runtime_checkable
class TimelineRepository(Protocol):
    def save(self, timeline: TimelineImport) -> TimelineId:
        ...

    def open(self, timeline_id: TimelineId) -> TimelineReader:
        ...
