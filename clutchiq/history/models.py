"""Typed demo import history models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path


class ImportResult(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class ImportStage(str, Enum):
    INGEST = "ingest"
    ANALYZE = "analyze"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class AnalysisSummary:
    total_rounds: int
    ct_rounds: int
    t_rounds: int
    winning_side: str
    rounds_with_known_winner: int


@dataclass(frozen=True, slots=True)
class DemoImportResult:
    id: str
    imported_at_utc: datetime
    source_path: Path | None
    source_name: str
    result: ImportResult
    parse_stage: ImportStage
    analysis_summary: AnalysisSummary | None = None
    error_type: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class PersistedImportRecord:
    id: str
    imported_at_utc: str
    source_path: str | None
    source_name: str
    result: ImportResult
    parse_stage: ImportStage
    analysis_summary: AnalysisSummary | None
    error_type: str | None
    error_message: str | None


@dataclass(frozen=True, slots=True)
class RecentDemoEntry:
    id: str
    source_name: str
    imported_at_utc: str
    result: ImportResult
    parse_stage: ImportStage
    winning_side: str | None


@dataclass(frozen=True, slots=True)
class DashboardSummary:
    is_available: bool
    is_empty: bool
    import_status: str
    total_demos_imported: int
    total_matches: int
    last_import_time: str
    recent_demos: tuple[RecentDemoEntry, ...]
    records: tuple[PersistedImportRecord, ...] = ()
