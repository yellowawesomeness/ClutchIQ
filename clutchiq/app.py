"""Qt application setup for ClutchIQ."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from clutchiq import __version__
from clutchiq.theme import build_stylesheet


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
