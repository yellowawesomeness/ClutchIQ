from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QListWidget, QPushButton

from clutchiq.demo_ingest.models import DemoRound
from clutchiq.demo_ingest.service import DemoIngestService
from clutchiq.history.models import AnalysisSummary, DemoImportResult, ImportResult, ImportStage
from clutchiq.history.service import DemoHistoryService
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


def test_match_card_opens_details_and_back(qapp: QApplication, tmp_path: Path) -> None:
    history = DemoHistoryService(tmp_path / "demo_history.json")
    history.record_import(
        DemoImportResult(
            id="1",
            imported_at_utc=datetime(2024, 1, 2, 15, 30, tzinfo=timezone.utc),
            source_path=Path("demo1.dem"),
            source_name="demo1.dem",
            result=ImportResult.SUCCESS,
            parse_stage=ImportStage.ANALYZE,
            analysis_summary=AnalysisSummary(30, 16, 14, "CT", 30),
        )
    )

    window = MainWindow(DemoIngestService(parser=DummyParser()), history_service=history)
    details_page = window.pages[Page.MATCH_DETAILS]
    details_page.set_record(
        history.load_summary().records[0],
        back_callback=lambda: None,
        rounds=(
            DemoRound(round_number=1, winner_team="CT", start_tick=1, end_tick=100, score_ct=1, score_t=0),
        ),
    )

    labels = {label.text() for label in details_page.findChildren(QLabel)}
    assert any(text.startswith("Filename: demo1.dem") for text in labels)
    assert any(text.startswith("Final score: 16-14") for text in labels)
    assert any(text.startswith("Winning side: CT") for text in labels)
    assert any("Round Browser" in text for text in labels)

    rounds_list = details_page.findChildren(QListWidget)[0]
    assert rounds_list.count() == 1
    assert "Round 1" in rounds_list.item(0).text()


def test_round_browser_highlights_selected_round(qapp: QApplication, tmp_path: Path) -> None:
    history = DemoHistoryService(tmp_path / "demo_history.json")
    history.record_import(
        DemoImportResult(
            id="1",
            imported_at_utc=datetime(2024, 1, 2, 15, 30, tzinfo=timezone.utc),
            source_path=Path("demo1.dem"),
            source_name="demo1.dem",
            result=ImportResult.SUCCESS,
            parse_stage=ImportStage.ANALYZE,
            analysis_summary=AnalysisSummary(30, 16, 14, "CT", 30),
        )
    )

    window = MainWindow(DemoIngestService(parser=DummyParser()), history_service=history)
    details_page = window.pages[Page.MATCH_DETAILS]
    details_page.set_record(
        history.load_summary().records[0],
        back_callback=lambda: None,
        rounds=(
            DemoRound(round_number=1, winner_team="CT", start_tick=1, end_tick=100, score_ct=1, score_t=0),
            DemoRound(round_number=2, winner_team="T", start_tick=101, end_tick=200, score_ct=1, score_t=1),
        ),
    )

    rounds_list = details_page.findChildren(QListWidget)[0]
    rounds_list.setCurrentRow(1)
    assert rounds_list.currentRow() == 1
    assert rounds_list.item(1).isSelected()


def test_match_card_opens_details_and_back_navigation(qapp: QApplication, tmp_path: Path) -> None:
    history = DemoHistoryService(tmp_path / "demo_history.json")
    history.record_import(
        DemoImportResult(
            id="1",
            imported_at_utc=datetime(2024, 1, 2, 15, 30, tzinfo=timezone.utc),
            source_path=Path("demo1.dem"),
            source_name="demo1.dem",
            result=ImportResult.SUCCESS,
            parse_stage=ImportStage.ANALYZE,
            analysis_summary=AnalysisSummary(30, 16, 14, "CT", 30),
        )
    )

    window = MainWindow(DemoIngestService(parser=DummyParser()), history_service=history)
    window.set_page(Page.MATCHES)

    card = next(button for button in window.pages[Page.MATCHES].findChildren(QPushButton) if "demo1.dem" in button.text())
    QTest.mouseClick(card, Qt.MouseButton.LeftButton)

    details_page = window.pages[Page.MATCH_DETAILS]
    assert window.stack.currentWidget() is details_page
    back_button = next(button for button in details_page.findChildren(QPushButton) if button.text() == "Back to Matches")
    QTest.mouseClick(back_button, Qt.MouseButton.LeftButton)
    assert window.stack.currentWidget() is window.pages[Page.MATCHES]
