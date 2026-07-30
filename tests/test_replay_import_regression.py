from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtWidgets import QApplication, QLabel

from clutchiq.demo_analysis.analyzer import AnalysisEngine
from clutchiq.demo_ingest.models import DemoRound
from clutchiq.demo_ingest.service import DemoIngestService
from clutchiq.history.models import AnalysisSummary, DemoImportResult, ImportResult, ImportStage
from clutchiq.history.service import DemoHistoryService
from clutchiq.widgets.components.navigation import Page
from clutchiq.window import MainWindow


class DummyParser:
    def parse(self, data: bytes) -> str:
        return "parsed"


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _result() -> DemoImportResult:
    return DemoImportResult(
        id="match-1", imported_at_utc=datetime(2024, 1, 1, tzinfo=timezone.utc), source_path=Path("real.dem"),
        source_name="real.dem", result=ImportResult.SUCCESS, parse_stage=ImportStage.ANALYZE,
        analysis_summary=AnalysisSummary(2, 1, 1, "CT", 2, map_name="de_mirage"),
    )


def test_imported_match_replay_loads_first_playable_round_and_preserves_map(tmp_path: Path) -> None:
    _app()
    history = DemoHistoryService(tmp_path / "history.json")
    window = MainWindow(DemoIngestService(parser=DummyParser()), history_service=history, analysis_engine=AnalysisEngine())
    history.record_import(_result())
    record = history.load_summary().records[-1]
    rounds = (DemoRound(round_number=0), DemoRound(round_number=1, start_tick=100, end_tick=200, score_ct=1, score_t=0, winner_team="CT"))

    window._cache_loaded_match(_result(), rounds)
    window._navigate(Page.REPLAY)

    replay = window.pages[Page.REPLAY]
    details = window.pages[Page.MATCH_DETAILS]
    assert window.stack.currentWidget() is replay
    assert replay._view_model is not None
    assert replay._view_model.round_number == 1
    assert replay._metadata_label.text() == "Match: real.dem"
    assert replay._tick_label.text() == "Tick: 100"
    assert details._record is not None
    assert details._record.id == record.id
    labels = [widget.text() for widget in (details._card_layout.itemAt(index).widget() for index in range(details._card_layout.count())) if isinstance(widget, QLabel)]
    assert "Map: de_mirage" in labels
    assert details._rounds_list.count() == 1


def test_round_without_scores_uses_intentional_placeholder_not_question_mark(tmp_path: Path) -> None:
    _app()
    history = DemoHistoryService(tmp_path / "history.json")
    history.record_import(_result())
    record = history.load_summary().records[-1]
    window = MainWindow(DemoIngestService(parser=DummyParser()), history_service=history, analysis_engine=AnalysisEngine())
    window._open_match_details(record)
    details = window.pages[Page.MATCH_DETAILS]
    details.set_record(record, lambda: None, rounds=(DemoRound(round_number=1),))
    assert "score=Unavailable-Unavailable" in details._rounds_list.item(0).text()
