"""Matches library page."""

from __future__ import annotations

from datetime import datetime
from functools import partial

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QPushButton, QScrollArea, QVBoxLayout, QWidget

from clutchiq.history.models import ImportResult, PersistedImportRecord
from clutchiq.history.service import DemoHistoryService
from clutchiq.widgets.components import AppCard, AppEyebrow, AppSubtitle, AppTitle


class MatchCardButton(QPushButton):
    def __init__(self, record: PersistedImportRecord, on_open_details, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._record = record
        self._on_open_details = on_open_details

    def mouseDoubleClickEvent(self, event) -> None:
        self._on_open_details(self._record)
        super().mouseDoubleClickEvent(event)


class MatchesPage(QWidget):
    def __init__(
        self,
        history_service: DemoHistoryService,
        navigate_to_match_details: callable | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._history_service = history_service
        self._navigate_to_match_details = navigate_to_match_details
        self._selected_record_id: str | None = None

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(28, 28, 28, 28)
        self._root.setSpacing(16)
        self._root.addWidget(AppEyebrow("MATCH LIBRARY"))
        self._root.addWidget(AppTitle("Matches"))
        self._root.addWidget(AppSubtitle("Read-only library of successful demo imports."))

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(12)
        self._scroll.setWidget(self._content)
        self._root.addWidget(self._scroll)
        self._root.addStretch(1)

        self.refresh()

    def showEvent(self, event) -> None:
        self.refresh()
        super().showEvent(event)

    def refresh(self) -> None:
        self._clear_layout(self._content_layout)
        summary = self._history_service.load_summary()
        records = [record for record in summary.records if record.result == ImportResult.SUCCESS]
        if not summary.is_available:
            self._content_layout.addWidget(self._empty_state("History unavailable", "Unable to read persisted imports."))
            return
        if not records:
            self._content_layout.addWidget(self._empty_state("No successful imports yet", "Import a demo to populate the match library."))
            return
        for record in records:
            self._content_layout.addWidget(self._match_row(record))
        self._content_layout.addStretch(1)

    def _match_row(self, record: PersistedImportRecord) -> QWidget:
        card = MatchCardButton(record, self._open_details)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setCheckable(True)
        card.setChecked(record.id == self._selected_record_id)
        card.setFlat(True)
        card.setStyleSheet(
            "QPushButton { text-align: left; border: 1px solid #3A3320; border-radius: 14px; background: #171717; padding: 14px 16px; color: #F5F5F5; }"
            "QPushButton:hover { border-color: #B8941E; background: #1C1A12; }"
            "QPushButton:checked { border-color: #F4C542; background: #221D0E; }"
        )
        imported_at = self._format_local_time(record.imported_at_utc)
        final_score = self._format_final_score(record)
        winning_side = record.analysis_summary.winning_side if record.analysis_summary is not None else "Unknown"
        total_rounds = str(record.analysis_summary.total_rounds if record.analysis_summary is not None else 0)
        card.setText(
            f"{record.source_name}\n"
            f"Imported: {imported_at}   |   Final score: {final_score}   |   Winner: {winning_side}   |   Rounds: {total_rounds}   |   Status: Success"
        )
        card.clicked.connect(partial(self._open_details, record))
        return card

    def _open_details(self, record: PersistedImportRecord) -> None:
        self._selected_record_id = record.id
        if self._navigate_to_match_details is not None:
            self._navigate_to_match_details(record)
        else:
            self.refresh()

    def _empty_state(self, title: str, message: str) -> QWidget:
        card = AppCard(alt=True)
        layout = QVBoxLayout(card)
        layout.addWidget(AppTitle(title))
        layout.addWidget(AppSubtitle(message))
        return card

    def _format_local_time(self, imported_at_utc: str) -> str:
        dt = datetime.fromisoformat(imported_at_utc)
        return dt.astimezone().strftime("%b %d, %Y %I:%M %p")

    def _format_final_score(self, record: PersistedImportRecord) -> str:
        if record.analysis_summary is None:
            return "0-0"
        return f"{record.analysis_summary.ct_rounds}-{record.analysis_summary.t_rounds}"

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.setParent(None)
            if child_layout is not None:
                self._clear_layout(child_layout)
