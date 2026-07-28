"""Read-only replay page."""

from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from clutchiq.demo_ingest.models import DemoRound
from clutchiq.history.models import PersistedImportRecord
from clutchiq.widgets.components import AppCard, AppEyebrow, AppSubtitle, AppTitle


class ReplayPage(QWidget):
    def __init__(self, back_callback: Callable[[], None] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._back_callback = back_callback
        self._record: PersistedImportRecord | None = None
        self._round: DemoRound | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)
        layout.addWidget(AppEyebrow("REPLAY WORKSPACE"))
        layout.addWidget(AppTitle("Replay"))
        layout.addWidget(AppSubtitle("Read-only replay positioned at the selected round start tick."))
        card = AppCard()
        self._card_layout = QVBoxLayout(card)
        self._card_layout.addWidget(QLabel("No replay loaded."))
        self._back_button = QPushButton("Back to Match Details")
        self._back_button.clicked.connect(self._on_back)
        self._card_layout.addWidget(self._back_button)
        layout.addWidget(card)
        layout.addStretch(1)

    def set_round(self, record: PersistedImportRecord, round_: DemoRound, back_callback: Callable[[], None]) -> None:
        self._record = record
        self._round = round_
        self._back_callback = back_callback
        self._refresh()

    def _refresh(self) -> None:
        self._clear_layout(self._card_layout)
        if self._record is None or self._round is None:
            self._card_layout.addWidget(QLabel("No replay loaded."))
        else:
            start_tick = self._round.start_tick if self._round.start_tick is not None else "Unknown"
            self._card_layout.addWidget(QLabel(f"Match: {self._record.source_name}"))
            self._card_layout.addWidget(QLabel(f"Round: {self._round.round_number}"))
            self._card_layout.addWidget(QLabel(f"Start tick: {start_tick}"))
        self._card_layout.addWidget(self._back_button)

    def _on_back(self) -> None:
        if self._back_callback is not None:
            self._back_callback()

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
