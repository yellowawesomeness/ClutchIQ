"""Application entry point for ClutchIQ."""

from __future__ import annotations

from clutchiq.app import create_application
from clutchiq.window import MainWindow


def main() -> int:
    """Create and run the ClutchIQ desktop application."""
    application = create_application()
    window = MainWindow()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
