from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QPushButton

from clutchiq.demo_analysis.analyzer import AnalysisEngine
from clutchiq.demo_ingest.service import DemoIngestService
from clutchiq.history.models import AnalysisSummary, DemoImportResult, ImportResult, ImportStage
from clutchiq.history.service import DemoHistoryService
from clutchiq.widgets.pages.import_demo import DemoImportOutcome, ImportDemoController
from clutchiq.widgets.pages.matches import MatchesPage


class DummyParser:
    def parse(self, data: bytes) -> str:
        return f"parsed:{len(data)}"


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_matches_page_loads_successful_imports(qapp: QApplication, tmp_path: Path) -> None:
    service = DemoHistoryService(tmp_path / "demo_history.json")
    service.record_import(
        DemoImportResult(
            id="1",
            imported_at_utc=datetime(2024, 1, 2, 15, 30, tzinfo=timezone.utc),
            source_path=Path("demo1.dem"),
            source_name="demo1.dem",
            result=ImportResult.SUCCESS,
            parse_stage=ImportStage.ANALYZE,
            analysis_summary=AnalysisSummary(
                total_rounds=30,
                ct_rounds=16,
                t_rounds=14,
                winning_side="CT",
                rounds_with_known_winner=30,
            ),
        )
    )
    service.record_import(
        DemoImportResult(
            id="2",
            imported_at_utc=datetime(2024, 1, 3, 15, 30, tzinfo=timezone.utc),
            source_path=Path("demo2.dem"),
            source_name="demo2.dem",
            result=ImportResult.FAILURE,
            parse_stage=ImportStage.INGEST,
            analysis_summary=None,
            error_type="ValueError",
            error_message="bad file",
        )
    )

    page = MatchesPage(service)
    buttons = page.findChildren(QPushButton)

    assert any("demo1.dem" in button.text() for button in buttons)
    assert any("Final score: 16-14" in button.text() for button in buttons)
    assert any("Winner: CT" in button.text() for button in buttons)
    assert not any("demo2.dem" in button.text() for button in buttons)


def test_import_success_callback_refreshes_dashboard(qapp: QApplication, tmp_path: Path) -> None:
    class FakeView:
        def __init__(self) -> None:
            self.finished = 0

        def on_import_finished(self, path: Path, result) -> None:
            self.finished += 1

    class FakeHistory:
        def __init__(self) -> None:
            self.recorded = 0

        def record_import(self, result) -> None:
            self.recorded += 1

    view = FakeView()
    history = FakeHistory()
    calls: list[str] = []
    controller = ImportDemoController(view, DemoIngestService(parser=DummyParser()), history, AnalysisEngine(), on_import_success=lambda *_: calls.append("refresh"))
    outcome = DemoImportOutcome(
        result=DemoImportResult(
            id="1",
            imported_at_utc=datetime.now(timezone.utc),
            source_path=Path("demo.dem"),
            source_name="demo.dem",
            result=ImportResult.SUCCESS,
            parse_stage=ImportStage.ANALYZE,
            analysis_summary=AnalysisSummary(1, 1, 0, "CT", 1),
        ),
        rounds=(),
    )

    controller._on_finished(outcome)

    assert history.recorded == 1
    assert view.finished == 1
    assert calls == ["refresh"]
