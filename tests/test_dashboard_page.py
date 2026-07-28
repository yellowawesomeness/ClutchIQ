from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from clutchiq.history.models import AnalysisSummary, DashboardSummary, ImportResult, ImportStage, PersistedImportRecord, RecentDemoEntry
from clutchiq.widgets.pages.dashboard import DashboardPage


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class DummyHistoryService:
    def __init__(self, summary: DashboardSummary) -> None:
        self.summary = summary

    def load_summary(self) -> DashboardSummary:
        return self.summary


def test_dashboard_renders_empty_state(qapp: QApplication) -> None:
    summary = DashboardSummary(
        is_available=True,
        is_empty=True,
        import_status="No imports yet",
        total_demos_imported=0,
        total_matches=0,
        last_import_time="No imports yet",
        recent_demos=(),
        records=(),
    )
    page = DashboardPage(DummyHistoryService(summary), lambda: None, lambda: None)

    assert page.banner is not None


def test_dashboard_renders_unavailable_state(qapp: QApplication) -> None:
    summary = DashboardSummary(
        is_available=False,
        is_empty=True,
        import_status="Import history unavailable",
        total_demos_imported=0,
        total_matches=0,
        last_import_time="Unavailable",
        recent_demos=(),
        records=(),
    )
    page = DashboardPage(DummyHistoryService(summary), lambda: None, lambda: None)

    assert page.banner is not None


def test_dashboard_renders_populated_summary(qapp: QApplication) -> None:
    record = PersistedImportRecord(
        id="1",
        imported_at_utc="2026-07-25T12:00:00+00:00",
        source_path="C:/demos/test.dem",
        source_name="test.dem",
        result=ImportResult.SUCCESS,
        parse_stage=ImportStage.ANALYZE,
        analysis_summary=AnalysisSummary(
            total_rounds=24,
            ct_rounds=13,
            t_rounds=11,
            winning_side="CT",
            rounds_with_known_winner=24,
        ),
        error_type=None,
        error_message=None,
    )
    recent = RecentDemoEntry(
        id="1",
        source_name="test.dem",
        imported_at_utc="2026-07-25T12:00:00+00:00",
        result=ImportResult.SUCCESS,
        parse_stage=ImportStage.ANALYZE,
        winning_side="CT",
    )
    summary = DashboardSummary(
        is_available=True,
        is_empty=False,
        import_status="Last import succeeded: test.dem",
        total_demos_imported=1,
        total_matches=1,
        last_import_time="2026-07-25T12:00:00+00:00",
        recent_demos=(recent,),
        records=(record,),
    )

    page = DashboardPage(DummyHistoryService(summary), lambda: None, lambda: None)

    assert page.banner is not None
