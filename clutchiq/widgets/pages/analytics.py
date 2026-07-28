"""Analytics placeholder page."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from clutchiq.widgets.components import AppCard, AppEyebrow, AppSubtitle, AppTitle


class AnalyticsPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)
        layout.addWidget(AppEyebrow("INSIGHTS"))
        layout.addWidget(AppTitle("Analytics"))
        layout.addWidget(AppSubtitle("Performance graphs and insight surfaces."))
        card = AppCard()
        card_layout = QVBoxLayout(card)
        card_layout.addWidget(QLabel("Placeholder content for the Analytics page."))
        layout.addWidget(card)
        layout.addStretch(1)
