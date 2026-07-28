from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from clutchiq.history.models import AnalysisSummary, DemoImportResult, ImportResult, ImportStage
from clutchiq.history.service import DemoHistoryError, DemoHistoryService


def test_record_import_and_load_summary(tmp_path: Path) -> None:
    service = DemoHistoryService(tmp_path / "demo_history.json")
    result = DemoImportResult(
        id="1",
        imported_at_utc=datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc),
        source_path=Path("C:/demos/match.dem"),
        source_name="match.dem",
        result=ImportResult.SUCCESS,
        parse_stage=ImportStage.ANALYZE,
        analysis_summary=AnalysisSummary(
            total_rounds=24,
            ct_rounds=13,
            t_rounds=11,
            winning_side="CT",
            rounds_with_known_winner=24,
        ),
    )

    service.record_import(result)
    summary = service.load_summary()

    assert summary.is_available is True
    assert summary.is_empty is False
    assert summary.total_demos_imported == 1
    assert summary.total_matches == 1
    assert summary.last_import_time == "2026-07-25T12:00:00+00:00"
    assert summary.recent_demos[-1].source_name == "match.dem"
    assert summary.recent_demos[-1].result == ImportResult.SUCCESS


def test_record_failed_import_and_summary(tmp_path: Path) -> None:
    service = DemoHistoryService(tmp_path / "demo_history.json")
    result = DemoImportResult(
        id="2",
        imported_at_utc=datetime(2026, 7, 25, 12, 5, tzinfo=timezone.utc),
        source_path=Path("C:/demos/bad.dem"),
        source_name="bad.dem",
        result=ImportResult.FAILURE,
        parse_stage=ImportStage.INGEST,
        error_type="DemoReadError",
        error_message="Could not read demo file.",
    )

    service.record_import(result)
    summary = service.load_summary()

    assert summary.is_available is True
    assert summary.is_empty is False
    assert summary.total_demos_imported == 0
    assert summary.total_matches == 0
    assert summary.recent_demos[-1].result == ImportResult.FAILURE
    assert summary.import_status == "Last import failed: bad.dem"


def test_missing_history_returns_empty_summary(tmp_path: Path) -> None:
    service = DemoHistoryService(tmp_path / "demo_history.json")
    summary = service.load_summary()

    assert summary.is_available is True
    assert summary.is_empty is True
    assert summary.total_demos_imported == 0
    assert summary.recent_demos == ()


def test_corrupt_history_returns_unavailable_summary(tmp_path: Path) -> None:
    path = tmp_path / "demo_history.json"
    path.write_text("{not valid json", encoding="utf-8")
    service = DemoHistoryService(path)

    summary = service.load_summary()

    assert summary.is_available is False
    assert summary.import_status == "Import history unavailable"


def test_record_import_raises_on_write_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service = DemoHistoryService(tmp_path / "demo_history.json")
    result = DemoImportResult(
        id="3",
        imported_at_utc=datetime(2026, 7, 25, 12, 10, tzinfo=timezone.utc),
        source_path=Path("C:/demos/locked.dem"),
        source_name="locked.dem",
        result=ImportResult.SUCCESS,
        parse_stage=ImportStage.ANALYZE,
        analysis_summary=AnalysisSummary(
            total_rounds=1,
            ct_rounds=1,
            t_rounds=0,
            winning_side="CT",
            rounds_with_known_winner=1,
        ),
    )

    def fail(*args, **kwargs):  # noqa: ANN001, ANN002
        raise OSError("disk full")

    monkeypatch.setattr(service, "_atomic_write", fail)

    with pytest.raises(DemoHistoryError):
        service.record_import(result)
