"""Qt application setup for ClutchIQ."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from clutchiq import __version__
from clutchiq.demo_analysis.analyzer import AnalysisEngine
from clutchiq.demo_ingest import Cs2DemoParser
from clutchiq.demo_ingest.service import DemoIngestService
from clutchiq.history.service import DemoHistoryService
from clutchiq.theme import build_stylesheet
from clutchiq.window import MainWindow


def create_application() -> QApplication:
    """Return the configured QApplication, creating it when necessary."""
    existing_application = QApplication.instance()
    if existing_application is not None:
        if not isinstance(existing_application, QApplication):
            raise RuntimeError("A non-GUI Qt application already exists.")
        return existing_application

    application = QApplication(sys.argv)
    application.setApplicationName("ClutchIQ")
    application.setApplicationDisplayName("ClutchIQ")
    application.setApplicationVersion(__version__)
    application.setOrganizationName("ClutchIQ")
    application.setStyle("Fusion")
    application.setStyleSheet(build_stylesheet())
    return application


def main(argv: list[str] | None = None) -> int:
    _ = argv
    application = create_application()
    ingest_service = DemoIngestService(parser=Cs2DemoParser())
    history_service = DemoHistoryService()
    analysis_engine = AnalysisEngine()
    window = MainWindow(ingest_service, history_service, analysis_engine)
    window.show()
    return application.exec()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
