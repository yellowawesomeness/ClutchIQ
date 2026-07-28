"""Read-only match details page."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from clutchiq.demo_analysis.models import WinningSide
from clutchiq.demo_ingest.models import DemoRound
from clutchiq.history.models import PersistedImportRecord
from clutchiq.widgets.components import AppCard, AppEyebrow, AppSubtitle, AppTitle


class MatchDetailsPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._record: PersistedImportRecord | None = None
        self._rounds: tuple[DemoRound, ...] = ()
        self._back_callback: callable | None = None
        self._selected_round_index: int | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(16)
        root.addWidget(AppEyebrow("MATCH DETAILS"))
        root.addWidget(AppTitle("Match Details"))
        root.addWidget(AppSubtitle("Read-only view of a completed demo import."))

        self._card = AppCard()
        self._card_layout = QVBoxLayout(self._card)
        self._card_layout.setContentsMargins(20, 20, 20, 20)
        self._card_layout.setSpacing(12)
        self._card_layout.addWidget(QLabel("Select a match to view details."))
        root.addWidget(self._card)

        self._rounds_card = AppCard()
        self._rounds_layout = QVBoxLayout(self._rounds_card)
        self._rounds_layout.setContentsMargins(20, 20, 20, 20)
        self._rounds_layout.setSpacing(12)
        self._rounds_layout.addWidget(QLabel("Round Browser"))
        self._rounds_list = QListWidget()
        self._rounds_list.currentRowChanged.connect(self._on_round_selected)
        self._rounds_layout.addWidget(self._rounds_list)
        root.addWidget(self._rounds_card)
        root.addStretch(1)

    def set_record(self, record: PersistedImportRecord, back_callback: callable, rounds: tuple[DemoRound, ...] = ()) -> None:
        self._record = record
        self._rounds = rounds
        self._back_callback = back_callback
        self._selected_round_index = None
        self._refresh()

    def _refresh(self) -> None:
        self._clear_layout(self._card_layout)
        self._rounds_list.clear()
        record = self._record
        if record is None:
            self._card_layout.addWidget(QLabel("No match selected."))
            self._rounds_list.addItem(QListWidgetItem("No round data available."))
            return

        summary = record.analysis_summary
        details = [
            ("Filename", record.source_name),
            ("Map", getattr(summary, "map_name", None) or "Unknown"),
            ("Import time", self._format_local_time(record.imported_at_utc)),
            ("Final score", self._format_final_score(record)),
            ("Winning side", self._format_winning_side(summary.winning_side if summary else None)),
            ("Total rounds", str(summary.total_rounds if summary else 0)),
            ("Status", record.result.value.title()),
        ]
        for label, value in details:
            self._card_layout.addWidget(QLabel(f"{label}: {value}"))

        back = QPushButton("Back to Matches")
        back.clicked.connect(self._on_back)
        self._card_layout.addWidget(back)
        self._card_layout.addWidget(QFrame())

        if not self._rounds:
            self._rounds_list.addItem(QListWidgetItem("No round data available."))
            self._rounds_list.setEnabled(False)
            return

        self._rounds_list.setEnabled(True)
        for round_ in self._rounds:
            self._rounds_list.addItem(QListWidgetItem(self._format_round(round_)))
        if self._rounds_list.count():
            self._rounds_list.setCurrentRow(0)

    def _on_back(self) -> None:
        if self._back_callback is not None:
            self._back_callback()

    def _on_round_selected(self, row: int) -> None:
        self._selected_round_index = row if row >= 0 else None
        for index in range(self._rounds_list.count()):
            item = self._rounds_list.item(index)
            is_selected = index == self._selected_round_index
            item.setSelected(is_selected)
            item.setBackground(Qt.GlobalColor.yellow if is_selected else Qt.GlobalColor.transparent)

    def _format_local_time(self, imported_at_utc: str) -> str:
        dt = datetime.fromisoformat(imported_at_utc)
        return dt.astimezone().strftime("%b %d, %Y %I:%M %p")

    def _format_final_score(self, record: PersistedImportRecord) -> str:
        if record.analysis_summary is None:
            return "0-0"
        return f"{record.analysis_summary.ct_rounds}-{record.analysis_summary.t_rounds}"

    def _format_winning_side(self, winning_side: str | None) -> str:
        if not winning_side:
            return "Unknown"
        normalized = winning_side.split(".")[-1].replace("_", " ").strip()
        if normalized.upper() in {"CT", "T"}:
            return normalized.upper()
        return normalized.title()

    def _format_round(self, round_: DemoRound) -> str:
        score_ct = round_.score_ct if round_.score_ct is not None else "?"
        score_t = round_.score_t if round_.score_t is not None else "?"
        ticks = (
            f"{round_.start_tick}-{round_.end_tick}"
            if round_.start_tick is not None and round_.end_tick is not None
            else "Unknown ticks"
        )
        return f"Round {round_.round_number}: winner={self._format_winning_side(round_.winner_team)} score={score_ct}-{score_t} ticks={ticks}"

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.setParent(None)
            if child_layout is not None:
                self._clear_layout(child_layout)
