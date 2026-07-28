"""Reusable typography widgets for the ClutchIQ desktop shell."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QWidget


class AppEyebrow(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("SectionEyebrow")


class AppTitle(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("PageTitle")


class AppSubtitle(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("PageSubtitle")
        self.setWordWrap(True)
