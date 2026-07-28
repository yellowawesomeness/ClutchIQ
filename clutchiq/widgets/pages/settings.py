"""Settings placeholder page."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from clutchiq.widgets.components import AppCard, AppEyebrow, AppSubtitle, AppTitle


class SettingsPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)
        layout.addWidget(AppEyebrow("CONFIGURATION"))
        layout.addWidget(AppTitle("Settings"))
        layout.addWidget(AppSubtitle("Application preferences and UI options."))
        card = AppCard()
        card_layout = QVBoxLayout(card)
        card_layout.addWidget(QLabel("Placeholder content for the Settings page."))
        layout.addWidget(card)
        layout.addStretch(1)
