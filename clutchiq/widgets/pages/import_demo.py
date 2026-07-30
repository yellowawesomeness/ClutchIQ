"""Import Demo page, controller, and worker."""
from __future__ import annotations
import logging
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import QFileDialog, QLabel, QVBoxLayout, QWidget
from clutchiq.demo_analysis.analyzer import AnalysisEngine
from clutchiq.demo_ingest.models import Cs2Demo, DemoRound
from clutchiq.demo_ingest.service import DemoIngestService
from clutchiq.history.models import AnalysisSummary, DemoImportResult, ImportResult, ImportStage
from clutchiq.history.service import DemoHistoryService
from clutchiq.timeline_engine.adapters import cs2demo_to_timeline_import
from clutchiq.timeline_engine.models import TimelineEvent
from clutchiq.widgets.components import AppButton, AppCard, AppEyebrow, AppSubtitle, AppTitle, ProgressBar, StatusBanner
LOGGER = logging.getLogger(__name__)
@dataclass(frozen=True, slots=True)
class DemoImportOutcome:
    result: DemoImportResult
    rounds: tuple[DemoRound, ...]
    timeline_events: tuple[TimelineEvent, ...] = ()
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
    def __init__(self, ingest_service: DemoIngestService, analysis_engine: AnalysisEngine, source_path: Path) -> None:
        super().__init__(); self._ingest_service, self._analysis_engine, self._source_path = ingest_service, analysis_engine, source_path; self.signals = DemoImportWorkerSignals()
    def run(self) -> None:
        self.signals.started.emit(self._source_path); current_stage = ImportStage.INGEST
        try:
            demo = self._ingest_service.ingest_path(self._source_path); current_stage = ImportStage.ANALYZE; analysis = self._analysis_engine.analyze(demo); match = analysis.match
            result = DemoImportResult(id=str(uuid4()), imported_at_utc=datetime.now(timezone.utc), source_path=self._source_path, source_name=self._source_path.name, result=ImportResult.SUCCESS, parse_stage=ImportStage.ANALYZE, analysis_summary=AnalysisSummary(total_rounds=match.total_rounds, ct_rounds=match.final_score.ct_rounds, t_rounds=match.final_score.t_rounds, winning_side=str(match.winning_side), rounds_with_known_winner=match.rounds_with_known_winner, map_name=getattr(match, "map_name", None) or getattr(demo, "map_name", None)))
            timeline_events = cs2demo_to_timeline_import(demo).events if isinstance(demo, Cs2Demo) else ()
        except Exception as exc: self.signals.failed.emit(DemoImportFailure(self._source_path, current_stage, type(exc).__name__, str(exc)))
        else: self.signals.finished.emit(DemoImportOutcome(result, tuple(demo.rounds), timeline_events))
class ImportDemoController(QObject):
    def __init__(self, view: "ImportDemoPage", ingest_service: DemoIngestService, history_service: DemoHistoryService, analysis_engine: AnalysisEngine, on_import_success: Callable[[DemoImportResult, tuple[DemoRound, ...], tuple[TimelineEvent, ...]], None] | None = None) -> None:
        super().__init__(view if isinstance(view, QObject) else None); self._view, self._ingest_service, self._history_service, self._analysis_engine, self._on_import_success = view, ingest_service, history_service, analysis_engine, on_import_success; self._pool = QThreadPool.globalInstance()
    def choose_and_import(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(self._view, "Select Demo File", "", "Demo Files (*.dem);;All Files (*)")
        if file_name: self.import_demo(Path(file_name))
    def import_demo(self, path: Path) -> None:
        worker = DemoImportWorker(self._ingest_service, self._analysis_engine, path); worker.signals.started.connect(self._view.on_import_started); worker.signals.finished.connect(self._on_finished); worker.signals.failed.connect(self._on_failed); self._pool.start(worker)
    def _on_finished(self, outcome: object) -> None:
        if not isinstance(outcome, DemoImportOutcome): return
        result = outcome.result if outcome.result.id else replace(outcome.result, id=str(uuid4()))
        try: self._history_service.record_import(result)
        except Exception: LOGGER.exception("Failed to persist demo import history for %s", result.source_name)
        self._view.on_import_finished(result.source_path, result)
        if self._on_import_success is not None: self._on_import_success(result, outcome.rounds, outcome.timeline_events)
    def _on_failed(self, failure_payload: object) -> None:
        if not isinstance(failure_payload, DemoImportFailure): return
        result = DemoImportResult(id=str(uuid4()), imported_at_utc=datetime.now(timezone.utc), source_path=failure_payload.source_path, source_name=failure_payload.source_path.name, result=ImportResult.FAILURE, parse_stage=failure_payload.stage, error_type=failure_payload.error_type, error_message=failure_payload.error_message)
        try: self._history_service.record_import(result)
        except Exception: LOGGER.exception("Failed to persist failed demo import history for %s", result.source_name)
        self._view.on_import_failed(result.source_path, result.error_message or "Import failed")
class ImportDemoPage(QWidget):
    def __init__(self, ingest_service: DemoIngestService, history_service: DemoHistoryService, analysis_engine: AnalysisEngine, on_import_success: Callable[[DemoImportResult, tuple[DemoRound, ...], tuple[TimelineEvent, ...]], None] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent); self._controller = ImportDemoController(self, ingest_service, history_service, analysis_engine, on_import_success=on_import_success)
        layout = QVBoxLayout(self); layout.setContentsMargins(28, 28, 28, 28); layout.setSpacing(16); layout.addWidget(AppEyebrow("DEMO IMPORT")); layout.addWidget(AppTitle("Import Demo")); layout.addWidget(AppSubtitle("Runs demo ingestion in a background worker so the UI stays responsive."))
        self._card = AppCard(); card_layout = QVBoxLayout(self._card); card_layout.setSpacing(12); self._status = StatusBanner("Select a demo to begin."); self._progress = ProgressBar(); self._progress.setVisible(False); self._import_button = AppButton("Choose Demo", role="primary"); self._import_button.clicked.connect(self._controller.choose_and_import)
        card_layout.addWidget(QLabel("Select a Counter-Strike 2 .dem replay file to analyze.")); card_layout.addWidget(self._import_button); card_layout.addWidget(self._progress); card_layout.addWidget(self._status); layout.addWidget(self._card); layout.addStretch(1)
    def on_import_started(self, path: Path) -> None:
        self._import_button.setEnabled(False); self._progress.setVisible(True); self._progress.setRange(0, 0); self._status.show_message(f"Importing {path.name}…")
    def on_import_finished(self, path: Path, result: DemoImportResult) -> None:
        self._import_button.setEnabled(True); self._progress.setVisible(False); self._status.show_message(f"Imported {path.name}")
    def on_import_failed(self, path: Path, message: str) -> None:
        self._import_button.setEnabled(True); self._progress.setVisible(False); self._status.show_message(f"Failed to import {path.name}: {message}", tone="error")
