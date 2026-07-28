from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from clutchiq.demo_ingest.service import DemoIngestService
from clutchiq.theme import ACCENT_HOVER, BACKGROUND, BORDER, PRIMARY_ACCENT, PRIMARY_TEXT, SECONDARY_TEXT, SURFACE, SURFACE_ALT, ThemeManager, build_stylesheet
from clutchiq.window import MainWindow
from clutchiq.widgets.components.navigation import Page


class DummyParser:
    def parse(self, data: bytes) -> str:
        return f"parsed:{len(data)}"


class DummyIngestService(DemoIngestService[str]):
    pass


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_theme_palette_exact() -> None:
    assert BACKGROUND == "#0D0D0D"
    assert SURFACE == "#161616"
    assert SURFACE_ALT == "#202020"
    assert BORDER == "#303030"
    assert PRIMARY_TEXT == "#F5F5F5"
    assert SECONDARY_TEXT == "#A0A0A0"
    assert PRIMARY_ACCENT == "#FFD400"
    assert ACCENT_HOVER == "#FFE45C"


def test_stylesheet_contains_required_colors() -> None:
    stylesheet = build_stylesheet()
    for color in [BACKGROUND, SURFACE, SURFACE_ALT, BORDER, PRIMARY_TEXT, SECONDARY_TEXT, PRIMARY_ACCENT, ACCENT_HOVER]:
        assert color in stylesheet


def test_main_window_uses_page_enum(qapp: QApplication) -> None:
    service = DemoIngestService(parser=DummyParser())
    window = MainWindow(service)
    assert window.pages[Page.DASHBOARD] is not None
    assert window.pages[Page.IMPORT_DEMO] is not None
    assert window.pages[Page.MATCHES] is not None
    assert window.pages[Page.MATCH_DETAILS] is not None
    assert window.pages[Page.REPLAY] is not None
    assert window.pages[Page.ANALYTICS] is not None
    assert window.pages[Page.SETTINGS] is not None


def test_theme_manager_returns_stylesheet() -> None:
    manager = ThemeManager()
    assert PRIMARY_ACCENT in manager.stylesheet()
