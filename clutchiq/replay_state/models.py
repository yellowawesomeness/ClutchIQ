"""Frozen replay state models."""

from __future__ import annotations

from dataclasses import dataclass

from clutchiq.demo_ingest.models import DemoRound
from clutchiq.history.models import PersistedImportRecord
from clutchiq.timeline_engine.models import Participant, Tick, TimelineEvent, TimelineId, TimelineMetadata


@dataclass(frozen=True, slots=True)
class ReplayProvenance:
    timeline_id: TimelineId | None
    timeline_schema_version: int
    ruleset_version: str


@dataclass(frozen=True, slots=True)
class ReplaySnapshot:
    tick: Tick
    provenance: ReplayProvenance
    applied_event_count: int


@dataclass(frozen=True, slots=True)
class ReplayState:
    snapshot: ReplaySnapshot
    metadata: TimelineMetadata
    participants: tuple[Participant, ...]
    applied_events: tuple[TimelineEvent, ...]


@dataclass(frozen=True, slots=True)
class ReplayViewModel:
    record: PersistedImportRecord
    round: DemoRound

    @property
    def source_name(self) -> str:
        return self.record.source_name

    @property
    def round_number(self) -> int:
        return self.round.round_number

    @property
    def start_tick(self) -> int | None:
        return self.round.start_tick

    @property
    def end_tick(self) -> int | None:
        return self.round.end_tick

    @property
    def score_ct(self) -> int | None:
        return self.round.score_ct

    @property
    def score_t(self) -> int | None:
        return self.round.score_t

    @property
    def winner_team(self) -> str | None:
        return self.round.winner_team
