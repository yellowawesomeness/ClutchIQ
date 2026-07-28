from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from clutchiq.demo_analysis.analyzer import AnalysisEngine
from clutchiq.history.models import AnalysisSummary, DemoImportResult, ImportResult, ImportStage
from clutchiq.widgets.pages.import_demo import DemoImportFailure, DemoImportOutcome, DemoImportWorker, ImportDemoController


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class DummyDemo:
    pass


class DummyIngestService:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail

    def ingest_path(self, path: Path) -> DummyDemo:
        if self.should_fail:
            raise RuntimeError("read failed")
        return DummyDemo()


class DummyAnalysisEngine:
    class Match:
        total_rounds = 2
        rounds_with_known_winner = 2

        class FinalScore:
            ct_rounds = 1
            t_rounds = 1

        final_score = FinalScore()
        winning_side = "CT"

    class Result:
        def __init__(self) -> None:
            self.match = DummyAnalysisEngine.Match()

    def analyze(self, demo: DummyDemo) -> "DummyAnalysisEngine.Result":  # noqa: ARG002
        return self.Result()


class DummyHistoryService:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.records: list[DemoImportResult] = []

    def record_import(self, result: DemoImportResult) -> None:
        if self.should_fail:
            raise RuntimeError("history failed")
        self.records.append(result)


class DummyView:
    def __init__(self) -> None:
        self.started: list[Path] = []
        self.finished: list[tuple[Path, DemoImportResult]] = []
        self.failed: list[tuple[Path, str]] = []

    def on_import_started(self, path: Path) -> None:
        self.started.append(path)

    def on_import_finished(self, path: Path, result: DemoImportResult) -> None:
        self.finished.append((path, result))

    def on_import_failed(self, path: Path, error: str) -> None:
        self.failed.append((path, error))


def test_worker_emits_typed_success_outcome(qapp: QApplication) -> None:
    worker = DemoImportWorker(DummyIngestService(), DummyAnalysisEngine(), Path("C:/demos/test.dem"))
    payloads: list[object] = []
    worker.signals.finished.connect(payloads.append)
    worker.run()

    assert len(payloads) == 1
    assert isinstance(payloads[0], DemoImportOutcome)
    assert payloads[0].result.result == ImportResult.SUCCESS
    assert payloads[0].result.parse_stage == ImportStage.ANALYZE
    assert payloads[0].result.imported_at_utc.tzinfo is not None


def test_controller_records_success_and_calls_view_once(qapp: QApplication) -> None:
    view = DummyView()
    history = DummyHistoryService()
    controller = ImportDemoController(view, DummyIngestService(), history, DummyAnalysisEngine())

    outcome = DemoImportOutcome(
        result=DemoImportResult(
            id="1",
            imported_at_utc=datetime.now(timezone.utc),
            source_path=Path("C:/demos/test.dem"),
            source_name="test.dem",
            result=ImportResult.SUCCESS,
            parse_stage=ImportStage.ANALYZE,
            analysis_summary=AnalysisSummary(
                total_rounds=2,
                ct_rounds=1,
                t_rounds=1,
                winning_side="CT",
                rounds_with_known_winner=2,
            ),
        )
    )

    controller._on_finished(outcome)

    assert len(view.finished) == 1
    assert history.records == [outcome.result]


def test_controller_records_failed_import_and_calls_view(qapp: QApplication) -> None:
    view = DummyView()
    history = DummyHistoryService()
    controller = ImportDemoController(view, DummyIngestService(), history, DummyAnalysisEngine())

    failure = DemoImportFailure(
        source_path=Path("C:/demos/bad.dem"),
        stage=ImportStage.INGEST,
        error_type="RuntimeError",
        error_message="read failed",
    )

    controller._on_failed(failure)

    assert len(view.failed) == 1
    assert history.records[0].result == ImportResult.FAILURE
    assert history.records[0].parse_stage == ImportStage.INGEST


def test_controller_ignores_history_write_failure(qapp: QApplication) -> None:
    view = DummyView()
    history = DummyHistoryService(should_fail=True)
    controller = ImportDemoController(view, DummyIngestService(), history, DummyAnalysisEngine())

    outcome = DemoImportOutcome(
        result=DemoImportResult(
            id="1",
            imported_at_utc=datetime.now(timezone.utc),
            source_path=Path("C:/demos/test.dem"),
            source_name="test.dem",
            result=ImportResult.SUCCESS,
            parse_stage=ImportStage.ANALYZE,
            analysis_summary=AnalysisSummary(
                total_rounds=2,
                ct_rounds=1,
                t_rounds=1,
                winning_side="CT",
                rounds_with_known_winner=2,
            ),
        )
    )

    controller._on_finished(outcome)

    assert len(view.finished) == 1
