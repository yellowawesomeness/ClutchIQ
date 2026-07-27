"""Main window composition for ClutchIQ."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStatusBar, QWidget

from clutchiq.widgets.dashboard import DashboardPage
from clutchiq.widgets.sidebar import Sidebar


class MainWindow(QMainWindow):
    """Top-level ClutchIQ window containing navigation and main content."""

    def __init__(self) -> None:
        """Configure and assemble the 1280 by 720 main window."""
        super().__init__()
        self.setWindowTitle("ClutchIQ")
        self.resize(1280, 720)
        self.setMinimumSize(960, 600)

        central_widget = QWidget(self)
        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._sidebar = Sidebar(parent=central_widget)
        self._dashboard = DashboardPage(parent=central_widget)

        layout.addWidget(self._sidebar)
        layout.addWidget(self._dashboard, 1)
        self.setCentralWidget(central_widget)

        status_bar = QStatusBar(self)
        status_bar.setSizeGripEnabled(False)
        status_bar.showMessage("Ready")
        self.setStatusBar(status_bar)

        self._sidebar.navigation_requested.connect(self._navigate_to)

    def _navigate_to(self, section: str) -> None:
        """Reflect the selected sidebar section in the content area."""
        self._dashboard.set_section(section)
        self.statusBar().showMessage(section)
