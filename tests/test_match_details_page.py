from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from clutchiq.demo_analysis.models import WinningSide
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
            analysis_summary=AnalysisSummary(30, 16, 14, WinningSide.CT.value, 30),
        )
    )

    window = MainWindow(DemoIngestService(parser=DummyParser()), history_service=history)
    window.set_page(Page.MATCHES)

    card = next(button for button in window.pages[Page.MATCHES].findChildren(QPushButton) if "demo1.dem" in button.text())
    QTest.mouseClick(card, Qt.MouseButton.LeftButton)

    details_page = window.pages[Page.MATCH_DETAILS]
    assert window.stack.currentWidget() is details_page
    labels = {label.text() for label in details_page.findChildren(QLabel)}
    assert any(text.startswith("Filename: demo1.dem") for text in labels)
    assert any(text.startswith("Final score: 16-14") for text in labels)
    assert any(text.startswith("Winning side: CT") for text in labels)

    back_button = next(button for button in details_page.findChildren(QPushButton) if button.text() == "Back to Matches")
    QTest.mouseClick(back_button, Qt.MouseButton.LeftButton)
    assert window.stack.currentWidget() is window.pages[Page.MATCHES]
