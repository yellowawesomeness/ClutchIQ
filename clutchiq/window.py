"""Main application shell for ClutchIQ."""

from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QStatusBar, QWidget

from clutchiq.demo_analysis.analyzer import AnalysisEngine
from clutchiq.demo_ingest import Cs2DemoParser
from clutchiq.demo_ingest.models import DemoRound
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


@dataclass
class LoadedMatchStore:
    _rounds_by_record_id: dict[str, tuple[DemoRound, ...]] = field(default_factory=dict)

    def set_rounds(self, record_id: str, rounds: tuple[DemoRound, ...]) -> None:
        self._rounds_by_record_id[record_id] = rounds

    def get_rounds(self, record_id: str) -> tuple[DemoRound, ...]:
        return self._rounds_by_record_id.get(record_id, ())


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
        self._loaded_match_store = LoadedMatchStore()
        self._active_match_record: PersistedImportRecord | None = None

        central = QWidget(self)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.stack = QStackedWidget(central)
        self.pages = {
            Page.DASHBOARD: DashboardPage(history_service=history_service, navigate_to_import_demo=lambda: self.set_page(Page.IMPORT_DEMO), navigate_to_matches=lambda: self.set_page(Page.MATCHES)),
            Page.IMPORT_DEMO: ImportDemoPage(ingest_service, history_service, analysis_engine, on_import_success=self._cache_loaded_match),
            Page.MATCHES: MatchesPage(history_service=history_service, navigate_to_match_details=self._open_match_details),
            Page.MATCH_DETAILS: MatchDetailsPage(),
            Page.REPLAY: ReplayPage(back_callback=self._back_to_match_details),
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

    def _cache_loaded_match(self, record, rounds: tuple[DemoRound, ...]) -> None:
        self._loaded_match_store.set_rounds(record.id, rounds)
        self.pages[Page.DASHBOARD].refresh()

    def _open_match_details(self, record: PersistedImportRecord, selected_round_index: int | None = None) -> None:
        self._active_match_record = record
        details_page = self.pages[Page.MATCH_DETAILS]
        details_page.set_record(
            record,
            back_callback=lambda: self.set_page(Page.MATCHES),
            open_replay_callback=lambda round_: self._open_replay(record, round_),
            rounds=self._loaded_match_store.get_rounds(record.id),
            selected_round_index=selected_round_index,
        )
        self.set_page(Page.MATCH_DETAILS)

    def _open_replay(self, record: PersistedImportRecord, round_: DemoRound) -> None:
        details_page = self.pages[Page.MATCH_DETAILS]
        selected_round_index = details_page.selected_round_index()
        replay_page = self.pages[Page.REPLAY]
        replay_page.set_round(
            record=record,
            round_=round_,
            back_callback=lambda: self._back_to_match_details(selected_round_index),
        )
        self._active_match_record = record
        self.set_page(Page.REPLAY)

    def _back_to_match_details(self, selected_round_index: int | None = None) -> None:
        if self._active_match_record is None:
            return
        details_page = self.pages[Page.MATCH_DETAILS]
        details_page.set_record(
            self._active_match_record,
            back_callback=lambda: self.set_page(Page.MATCHES),
            open_replay_callback=lambda round_: self._open_replay(self._active_match_record, round_),
            rounds=self._loaded_match_store.get_rounds(self._active_match_record.id),
            selected_round_index=selected_round_index,
        )
        self.set_page(Page.MATCH_DETAILS)

    def set_page(self, page: Page) -> None:
        self.stack.setCurrentWidget(self.pages[page])
        self.sidebar.set_active(page)
        self.statusBar().showMessage(page.value.replace("_", " ").title())
