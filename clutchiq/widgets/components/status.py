"""Reusable status banner for the ClutchIQ desktop shell."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from clutchiq.theme import PRIMARY_ACCENT, PRIMARY_TEXT
from clutchiq.widgets.components.cards import AppCard


class StatusBanner(AppCard):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent, alt=True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        self._icon = QLabel("i", self)
        self._icon.setStyleSheet(f"color: {PRIMARY_ACCENT}; font-weight: 900;")
        self._label = QLabel(text, self)
        self._label.setWordWrap(True)
        self._label.setStyleSheet(f"color: {PRIMARY_TEXT};")

        layout.addWidget(self._icon)
        layout.addWidget(self._label, 1)

    def set_text(self, text: str) -> None:
        self._label.setText(text)

    def show_message(self, text: str) -> None:
        self.set_text(text)
