"""Reusable buttons for the ClutchIQ desktop shell."""

from __future__ import annotations

from PySide6.QtWidgets import QPushButton, QWidget


class AppButton(QPushButton):
    def __init__(self, text: str, role: str = "secondary", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setProperty("role", role)
