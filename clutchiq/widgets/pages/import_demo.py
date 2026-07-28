"""Import Demo page, controller, and worker."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from collections.abc import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from clutchiq.demo_analysis.analyzer import AnalysisEngine
from clutchiq.demo_ingest.service import DemoIngestService
from clutchiq.history.models import AnalysisSummary, DemoImportResult, ImportResult, ImportStage
from clutchiq.history.service import DemoHistoryError, DemoHistoryService
from clutchiq.widgets.components import AppButton, AppCard, AppEyebrow, AppSubtitle, AppTitle, ProgressBar, StatusBanner

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DemoImportOutcome:
    result: DemoImportResult


@dataclass(frozen=True, slots=True)
class DemoImportFailure:
    source_path: Path
    stage: ImportStage
    error_type: str
    error_message: str


class DemoImportWorkerSignals(QObject):
    started = Signal(Path)
    finished = Signal(object)
    failed = Signal(object)


class DemoImportWorker(QRunnable):
    def __init__(
        self,
        ingest_service: DemoIngestService,
        analysis_engine: AnalysisEngine,
        source_path: Path,
    ) -> None:
        super().__init__()
        self._ingest_service = ingest_service
        self._analysis_engine = analysis_engine
        self._source_path = source_path
        self.signals = DemoImportWorkerSignals()

    def run(self) -> None:
        self.signals.started.emit(self._source_path)
        current_stage = ImportStage.INGEST
        try:
            demo = self._ingest_service.ingest_path(self._source_path)
            current_stage = ImportStage.ANALYZE
            analysis = self._analysis_engine.analyze(demo)
            match = analysis.match
            result = DemoImportResult(
                id=str(uuid4()),
                imported_at_utc=datetime.now(timezone.utc),
                source_path=self._source_path,
                source_name=self._source_path.name,
                result=ImportResult.SUCCESS,
                parse_stage=ImportStage.ANALYZE,
                analysis_summary=AnalysisSummary(
                    total_rounds=match.total_rounds,
                    ct_rounds=match.final_score.ct_rounds,
                    t_rounds=match.final_score.t_rounds,
                    winning_side=str(match.winning_side),
                    rounds_with_known_winner=match.rounds_with_known_winner,
                ),
            )
        except Exception as exc:  # noqa: BLE001
            failure = DemoImportFailure(
                source_path=self._source_path,
                stage=current_stage,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            self.signals.failed.emit(failure)
        else:
            self.signals.finished.emit(DemoImportOutcome(result=result))


class ImportDemoController(QObject):
    def __init__(
        self,
        view: "ImportDemoPage",
        ingest_service: DemoIngestService,
        history_service: DemoHistoryService,
        analysis_engine: AnalysisEngine,
        on_import_success: Callable[[], None] | None = None,
    ) -> None:
        parent = view if isinstance(view, QObject) else None
        super().__init__(parent)
        self._view = view
        self._ingest_service = ingest_service
        self._history_service = history_service
        self._analysis_engine = analysis_engine
        self._on_import_success = on_import_success
        self._pool = QThreadPool.globalInstance()

    def choose_and_import(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(self._view, "Select Demo File", "", "Demo Files (*.dem);;All Files (*)")
        if file_name:
            self.import_demo(Path(file_name))

    def import_demo(self, path: Path) -> None:
        worker = DemoImportWorker(
            ingest_service=self._ingest_service,
            analysis_engine=self._analysis_engine,
            source_path=path,
        )
        worker.signals.started.connect(self._view.on_import_started)
        worker.signals.finished.connect(self._on_finished)
        worker.signals.failed.connect(self._on_failed)
        self._pool.start(worker)

    def _on_finished(self, outcome: object) -> None:
        if not isinstance(outcome, DemoImportOutcome):
            return
        try:
            self._history_service.record_import(outcome.result)
        except Exception:
            LOGGER.exception("Failed to persist demo import history for %s", outcome.result.source_name)
        self._view.on_import_finished(outcome.result.source_path, outcome.result)
        if self._on_import_success is not None:
            self._on_import_success()

    def _on_failed(self, failure_payload: object) -> None:
        if not isinstance(failure_payload, DemoImportFailure):
            return
        result = DemoImportResult(
            id=str(uuid4()),
            imported_at_utc=datetime.now(timezone.utc),
            source_path=failure_payload.source_path,
            source_name=failure_payload.source_path.name,
            result=ImportResult.FAILURE,
            parse_stage=failure_payload.stage,
            error_type=failure_payload.error_type,
            error_message=failure_payload.error_message,
        )
        try:
            self._history_service.record_import(result)
        except Exception:
            LOGGER.exception("Failed to persist failed demo import history for %s", result.source_name)
        self._view.on_import_failed(result.source_path, result.error_message or "Import failed")


class ImportDemoPage(QWidget):
    def __init__(
        self,
        ingest_service: DemoIngestService,
        history_service: DemoHistoryService,
        analysis_engine: AnalysisEngine,
        on_import_success: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = ImportDemoController(
            self,
            ingest_service,
            history_service,
            analysis_engine,
            on_import_success=on_import_success,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        layout.addWidget(AppEyebrow("DEMO IMPORT"))
        layout.addWidget(AppTitle("Import Demo"))
        layout.addWidget(AppSubtitle("Runs demo ingestion in a background worker so the UI stays responsive."))

        self.banner = StatusBanner("Select a demo file to begin.")
        layout.addWidget(self.banner)

        card = AppCard(alt=True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)

        row = QHBoxLayout()
        self.choose_button = AppButton("Choose Demo File", role="primary")
        self.choose_button.clicked.connect(self._controller.choose_and_import)
        row.addWidget(self.choose_button)
        row.addStretch(1)

        self.progress = ProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.status = QLabel("Idle")

        card_layout.addLayout(row)
        card_layout.addWidget(self.progress)
        card_layout.addWidget(self.status)
        layout.addWidget(card)
        layout.addStretch(1)

    def on_import_started(self, path: Path) -> None:
        self.choose_button.setEnabled(False)
        self.progress.setVisible(True)
        self.status.setText(f"Processing {path.name}...")
        self.banner.set_text(f"Import started for {path.name}")

    def on_import_finished(self, path: Path, result: DemoImportResult) -> None:
        self.choose_button.setEnabled(True)
        self.progress.setVisible(False)
        self.status.setText(f"Imported {path.name}")
        self.banner.set_text(f"Import completed: {path.name}")

    def on_import_failed(self, path: Path, error: str) -> None:
        self.choose_button.setEnabled(True)
        self.progress.setVisible(False)
        self.status.setText(f"Import failed: {path.name}")
        self.banner.set_text(f"Import failed: {error}")
