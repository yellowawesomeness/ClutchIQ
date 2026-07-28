"""Dashboard page."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from clutchiq.history.models import DashboardSummary
from clutchiq.history.service import DemoHistoryService
from clutchiq.widgets.components import AppButton, AppCard, AppEyebrow, AppSubtitle, AppTitle, StatusBanner


class DashboardPage(QWidget):
    def __init__(
        self,
        history_service: DemoHistoryService,
        navigate_to_import_demo,
        navigate_to_matches,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._history_service = history_service
        self._navigate_to_import_demo = navigate_to_import_demo
        self._navigate_to_matches = navigate_to_matches

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(28, 28, 28, 28)
        self._root.setSpacing(16)

        self._root.addWidget(AppEyebrow("CONTROL CENTER"))
        self._root.addWidget(AppTitle("Dashboard"))
        self._root.addWidget(AppSubtitle("Overview, recent imports, and quick access to core workflows."))

        self.banner = StatusBanner("Loading dashboard data...")
        self._root.addWidget(self.banner)

        self._stats_row = QHBoxLayout()
        self._root.addLayout(self._stats_row)

        self._body_row = QHBoxLayout()
        self._root.addLayout(self._body_row)

        self.refresh()

    def refresh(self) -> None:
        self.render_summary(self._history_service.load_summary())

    def render_summary(self, summary: DashboardSummary) -> None:
        self._clear_layout(self._stats_row)
        self._clear_layout(self._body_row)

        if not summary.is_available:
            self.banner.set_text("Dashboard data is unavailable.")
            self._body_row.addWidget(self._empty_state("Import history unavailable", "The history file could not be read."))
            return

        self.banner.set_text(summary.import_status)

        self._stats_row.addWidget(self._metric_card("Total Demos Imported", str(summary.total_demos_imported)))
        self._stats_row.addWidget(self._metric_card("Total Matches", str(summary.total_matches)))
        self._stats_row.addWidget(self._metric_card("Last Import Time", summary.last_import_time))
        self._stats_row.addWidget(self._metric_card("Import Status", summary.import_status))

        quick_actions = AppCard(alt=True)
        quick_layout = QVBoxLayout(quick_actions)
        quick_layout.setContentsMargins(20, 20, 20, 20)
        quick_layout.addWidget(AppTitle("Quick Actions"))

        action_row = QHBoxLayout()
        import_button = AppButton("Import Demo", role="primary")
        import_button.clicked.connect(self._navigate_to_import_demo)
        matches_button = AppButton("Open Matches", role="secondary")
        matches_button.clicked.connect(self._navigate_to_matches)
        action_row.addWidget(import_button)
        action_row.addWidget(matches_button)
        action_row.addStretch(1)
        quick_layout.addLayout(action_row)
        self._body_row.addWidget(quick_actions)

        recent_card = AppCard()
        recent_layout = QVBoxLayout(recent_card)
        recent_layout.setContentsMargins(20, 20, 20, 20)
        recent_layout.addWidget(AppTitle("Recent Imported Demos"))

        if summary.is_empty:
            recent_layout.addWidget(self._empty_state("No demos imported yet", "Use Import Demo to populate the dashboard."))
            self._body_row.addWidget(self._empty_state("No demos exist", "Import your first demo to see dashboard metrics."))
        else:
            for record in summary.recent_demos:
                recent_layout.addWidget(
                    QLabel(f"{record.source_name}  •  {record.imported_at_utc}  •  {record.result.value.title()}")
                )

        self._body_row.addWidget(recent_card)

    def _metric_card(self, label: str, value: str) -> QWidget:
        card = AppCard(alt=True)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        title = QLabel(label)
        title.setStyleSheet("color: #A0A0A0;")
        value_label = QLabel(value)
        value_label.setWordWrap(True)
        value_label.setStyleSheet("color: #F5F5F5; font-size: 18px; font-weight: 700;")
        layout.addWidget(title)
        layout.addWidget(value_label)
        return card

    def _empty_state(self, title: str, message: str) -> QWidget:
        card = AppCard(alt=True)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.addWidget(AppTitle(title))
        layout.addWidget(AppSubtitle(message))
        return card

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.setParent(None)
            if child_layout is not None:
                self._clear_layout(child_layout)
