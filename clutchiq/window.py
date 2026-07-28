"""Main application shell for ClutchIQ."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QStatusBar, QWidget

from clutchiq.demo_analysis.analyzer import AnalysisEngine
from clutchiq.demo_ingest import Cs2DemoParser
from clutchiq.demo_ingest.service import DemoIngestService
from clutchiq.history.models import PersistedImportRecord
from clutchiq.history.service import DemoHistoryService
from clutchiq.widgets.components.navigation import IconName, NavigationButton, Page, SidebarNavigation
from clutchiq.widgets.pages.analytics import AnalyticsPage
from clutchiq.widgets.pages.dashboard import DashboardPage
from clutchiq.widgets.pages.import_demo import ImportDemoPage
from clutchiq.widgets.pages.match_details import MatchDetailsPage
from clutchiq.widgets.pages.matches import MatchesPage
from clutchiq.widgets.pages.replay import ReplayPage
from clutchiq.widgets.pages.settings import SettingsPage


class MainWindow(QMainWindow):
    def __init__(
        self,
        ingest_service: DemoIngestService,
        history_service: DemoHistoryService | None = None,
        analysis_engine: AnalysisEngine | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("ClutchIQ")
        self.resize(1440, 900)
        self.setMinimumSize(1100, 700)

        history_service = history_service or DemoHistoryService()
        analysis_engine = analysis_engine or AnalysisEngine()

        central = QWidget(self)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.stack = QStackedWidget(central)
        self.pages = {
            Page.DASHBOARD: DashboardPage(history_service=history_service, navigate_to_import_demo=lambda: self.set_page(Page.IMPORT_DEMO), navigate_to_matches=lambda: self.set_page(Page.MATCHES)),
            Page.IMPORT_DEMO: ImportDemoPage(ingest_service, history_service, analysis_engine, on_import_success=lambda: self.pages[Page.DASHBOARD].refresh()),
            Page.MATCHES: MatchesPage(history_service=history_service, navigate_to_match_details=self._open_match_details),
            Page.MATCH_DETAILS: MatchDetailsPage(),
            Page.REPLAY: ReplayPage(),
            Page.ANALYTICS: AnalyticsPage(),
            Page.SETTINGS: SettingsPage(),
        }
        for page in self.pages.values():
            self.stack.addWidget(page)

        self.sidebar = SidebarNavigation(central)
        self._nav_buttons: dict[Page, NavigationButton] = {}
        nav_items = [
            (Page.DASHBOARD, "Dashboard", IconName.DASHBOARD),
            (Page.IMPORT_DEMO, "Import Demo", IconName.IMPORT),
            (Page.MATCHES, "Matches", IconName.MATCHES),
            (Page.REPLAY, "Replay", IconName.REPLAY),
            (Page.ANALYTICS, "Analytics", IconName.ANALYTICS),
            (Page.SETTINGS, "Settings", IconName.SETTINGS),
        ]
        for page, text, icon in nav_items:
            button = NavigationButton(text, page, icon)
            button.clicked.connect(lambda _=False, p=page: self.set_page(p))
            self._nav_buttons[page] = button
            self.sidebar.add_button(button)

        root.addWidget(self.sidebar)
        root.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        status = QStatusBar(self)
        status.setSizeGripEnabled(False)
        status.showMessage("Ready")
        self.setStatusBar(status)

        self.set_page(Page.DASHBOARD)

    def _open_match_details(self, record: PersistedImportRecord) -> None:
        details_page = self.pages[Page.MATCH_DETAILS]
        details_page.set_record(record, back_callback=lambda: self.set_page(Page.MATCHES))
        self.set_page(Page.MATCH_DETAILS)

    def set_page(self, page: Page) -> None:
        self.stack.setCurrentWidget(self.pages[page])
        self.sidebar.set_active(page)
        self.statusBar().showMessage(page.value.replace("_", " ").title())
