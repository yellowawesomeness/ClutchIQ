"""Timeline engine service facade."""

from __future__ import annotations

from dataclasses import dataclass

from clutchiq.timeline_engine.models import TimelineId, TimelineImport
from clutchiq.timeline_engine.ports import TimelineRepository


@dataclass(frozen=True, slots=True)
class TimelineEngine:
    repository: TimelineRepository

    def import_timeline(self, timeline: TimelineImport) -> TimelineId:
        return self.repository.save(timeline)

    def open(self, timeline_id: TimelineId):
        return self.repository.open(timeline_id)
