"""Reusable navigation widgets for the ClutchIQ desktop shell."""

from __future__ import annotations

from enum import Enum

from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget

from clutchiq.widgets.components.buttons import AppButton
from clutchiq.widgets.components.icons import IconName, IconProvider


class Page(str, Enum):
    DASHBOARD = "dashboard"
    IMPORT_DEMO = "import_demo"
    MATCHES = "matches"
    MATCH_DETAILS = "match_details"
    REPLAY = "replay"
    ANALYTICS = "analytics"
    SETTINGS = "settings"


class NavigationButton(AppButton):
    def __init__(self, text: str, page: Page, icon: IconName, parent: QWidget | None = None) -> None:
        super().__init__(text, role="nav", parent=parent)
        self.page = page
        self.setIcon(IconProvider.icon(icon))


class SidebarNavigation(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ShellSidebar")
        self._buttons: dict[Page, NavigationButton] = {}
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 20, 20, 20)
        self._layout.setSpacing(10)

    def add_button(self, button: NavigationButton) -> None:
        self._buttons[button.page] = button
        self._layout.addWidget(button)

    def set_active(self, page: Page) -> None:
        for item_page, button in self._buttons.items():
            button.setProperty("active", item_page == page)
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()
