from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from clutchiq.demo_analysis.analyzer import AnalysisEngine
from clutchiq.demo_ingest.models import DemoRound
from clutchiq.demo_ingest.service import DemoIngestService
from clutchiq.history.models import AnalysisSummary, DemoImportResult, ImportResult, ImportStage
from clutchiq.history.service import DemoHistoryService
from clutchiq.widgets.pages.import_demo import DemoImportOutcome
from clutchiq.window import MainWindow
from clutchiq.widgets.components.navigation import Page


class DummyParser:
    def parse(self, data: bytes) -> str:
        return f"parsed:{len(data)}"


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_import_opens_new_uuid_even_when_filename_matches_existing_record(qapp: QApplication, tmp_path: Path) -> None:
    history = DemoHistoryService(tmp_path / "demo_history.json")
    window = MainWindow(DemoIngestService(parser=DummyParser()), history_service=history, analysis_engine=AnalysisEngine())

    first = DemoImportResult(
        id="",
        imported_at_utc=datetime(2024, 1, 1, 15, 30, tzinfo=timezone.utc),
        source_path=Path("demo.dem"),
        source_name="demo.dem",
        result=ImportResult.SUCCESS,
        parse_stage=ImportStage.ANALYZE,
        analysis_summary=AnalysisSummary(18, 9, 9, "CT", 18),
    )
    history.record_import(first)

    outcome = DemoImportOutcome(
        result=DemoImportResult(
            id="",
            imported_at_utc=datetime(2024, 1, 2, 15, 30, tzinfo=timezone.utc),
            source_path=Path("demo.dem"),
            source_name="demo.dem",
            result=ImportResult.SUCCESS,
            parse_stage=ImportStage.ANALYZE,
            analysis_summary=AnalysisSummary(19, 10, 9, "CT", 19),
        ),
        rounds=tuple(DemoRound(round_number=index + 1) for index in range(19)),
    )

    window.pages[Page.IMPORT_DEMO]._controller._on_finished(outcome)
    persisted_second = history.load_summary().records[-1]

    assert window.stack.currentWidget() is window.pages[Page.MATCH_DETAILS]
    assert window.pages[Page.MATCHES]._selected_record_id == persisted_second.id
    assert window.pages[Page.MATCH_DETAILS]._record is not None
    assert window.pages[Page.MATCH_DETAILS]._record.id == persisted_second.id
    assert len(window.pages[Page.MATCH_DETAILS]._rounds) == 19
    assert len(window._loaded_match_store.get_rounds(persisted_second.id)) == 19
    assert len(window._loaded_match_store.get_rounds(first.id)) == 0
