"""Primary content view for the ClutchIQ application."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


SECTION_DESCRIPTIONS: dict[str, str] = {
    "Dashboard": "Your competitive performance hub is ready.",
    "Matches": "Review your match history and results.",
    "Replay": "Analyze key moments from your latest games.",
    "AI Coach": "Turn gameplay data into smarter decisions.",
    "Settings": "Configure ClutchIQ to fit your workflow.",
}


class DashboardPage(QWidget):
    """Show the welcome message and context for the selected section."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Construct the centered welcome view."""
        super().__init__(parent)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(72, 56, 72, 56)
        outer_layout.setSpacing(0)
        outer_layout.addStretch(2)

        content_layout = QVBoxLayout()
        content_layout.setSpacing(14)

        self._eyebrow = QLabel("DASHBOARD", self)
        self._eyebrow.setObjectName("welcomeEyebrow")
        content_layout.addWidget(self._eyebrow)

        title = QLabel("Welcome to ClutchIQ", self)
        title.setObjectName("welcomeTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        content_layout.addWidget(title)

        accent_line = QFrame(self)
        accent_line.setObjectName("accentLine")
        accent_line.setFixedSize(64, 4)
        content_layout.addWidget(accent_line)

        self._subtitle = QLabel(SECTION_DESCRIPTIONS["Dashboard"], self)
        self._subtitle.setObjectName("welcomeSubtitle")
        self._subtitle.setWordWrap(True)
        content_layout.addWidget(self._subtitle)

        outer_layout.addLayout(content_layout)
        outer_layout.addStretch(3)

    def set_section(self, section: str) -> None:
        """Update the contextual copy for a navigation section."""
        if section not in SECTION_DESCRIPTIONS:
            raise ValueError(f"Unknown section: {section}")
        self._eyebrow.setText(section.upper())
        self._subtitle.setText(SECTION_DESCRIPTIONS[section])
