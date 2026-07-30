"""Timeline engine service facade."""

from __future__ import annotations

from dataclasses import dataclass

from clutchiq.timeline_engine.clutches import detect_clutches
from clutchiq.timeline_engine.models import TimelineId, TimelineImport
from clutchiq.timeline_engine.ports import TimelineRepository
from clutchiq.timeline_engine.query import ClutchQuery, ClutchResult, EventQuery, TradeQuery, TradeResult
from clutchiq.timeline_engine.trades import detect_trades


@dataclass(frozen=True, slots=True)
class TimelineEngine:
    repository: TimelineRepository

    def import_timeline(self, timeline: TimelineImport) -> TimelineId:
        return self.repository.save(timeline)

    def open(self, timeline_id: TimelineId):
        return self.repository.open(timeline_id)

    def detect_trades(self, query: TradeQuery) -> TradeResult:
        """Return trades for a stored timeline using its canonical event stream."""
        reader = self.repository.open(query.timeline_id)
        return detect_trades(reader.events(EventQuery()).items, query)

    def detect_clutches(self, query: ClutchQuery) -> ClutchResult:
        """Return successful clutches for a stored timeline's canonical event stream."""
        reader = self.repository.open(query.timeline_id)
        return detect_clutches(reader.events(EventQuery()).items, query)
