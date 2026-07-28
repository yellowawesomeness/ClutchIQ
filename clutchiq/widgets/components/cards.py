"""Reusable card containers for the ClutchIQ desktop shell."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QWidget


class AppCard(QFrame):
    def __init__(self, parent: QWidget | None = None, alt: bool = False) -> None:
        super().__init__(parent)
        self.setObjectName("SurfaceAltCard" if alt else "Card")
        self.setFrameShape(QFrame.Shape.NoFrame)
