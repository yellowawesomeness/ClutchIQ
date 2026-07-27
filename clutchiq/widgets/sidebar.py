"""Sidebar navigation widget for ClutchIQ."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget


NAVIGATION_ITEMS: tuple[str, ...] = (
    "Dashboard",
    "Matches",
    "Replay",
    "AI Coach",
    "Settings",
)


class Sidebar(QFrame):
    """Display the ClutchIQ brand and primary navigation controls."""

    navigation_requested = Signal(str)

    def __init__(
        self,
        items: Sequence[str] = NAVIGATION_ITEMS,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize navigation buttons for the supplied item names."""
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(236)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self._buttons: dict[str, QPushButton] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 30, 0, 24)
        layout.setSpacing(4)

        brand = QLabel("CLUTCHIQ", self)
        brand.setObjectName("brandMark")
        brand.setContentsMargins(24, 0, 24, 0)
        layout.addWidget(brand)

        tagline = QLabel("PLAY SMARTER", self)
        tagline.setObjectName("brandTagline")
        tagline.setContentsMargins(25, 0, 24, 24)
        layout.addWidget(tagline)

        for item in items:
            button = self._create_navigation_button(item)
            self._buttons[item] = button
            layout.addWidget(button)

        layout.addStretch(1)

        version_label = QLabel("CLUTCHIQ  •  DESKTOP", self)
        version_label.setObjectName("brandTagline")
        version_label.setContentsMargins(24, 0, 24, 0)
        layout.addWidget(version_label)

        if items:
            self.set_active_item(items[0])

    def _create_navigation_button(self, item: str) -> QPushButton:
        """Create a consistently configured navigation button."""
        button = QPushButton(item, self)
        button.setObjectName("navigationButton")
        button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        button.setFixedHeight(48)
        button.setProperty("active", False)
        button.clicked.connect(
            lambda checked=False, selected_item=item: self._request_navigation(
                selected_item
            )
        )
        return button

    def _request_navigation(self, item: str) -> None:
        """Activate and emit the selected navigation item."""
        self.set_active_item(item)
        self.navigation_requested.emit(item)

    def set_active_item(self, item: str) -> None:
        """Visually mark one navigation item as active."""
        if item not in self._buttons:
            raise ValueError(f"Unknown navigation item: {item}")

        for name, button in self._buttons.items():
            button.setProperty("active", name == item)
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()
