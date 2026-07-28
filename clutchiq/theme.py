"""Global theme manager and QSS for the ClutchIQ desktop shell."""

from __future__ import annotations

from dataclasses import dataclass

BACKGROUND = "#0D0D0D"
SURFACE = "#161616"
SURFACE_ALT = "#202020"
BORDER = "#303030"
PRIMARY_TEXT = "#F5F5F5"
SECONDARY_TEXT = "#A0A0A0"
PRIMARY_ACCENT = "#FFD400"
ACCENT_HOVER = "#FFE45C"


@dataclass(frozen=True, slots=True)
class Theme:
    background: str = BACKGROUND
    surface: str = SURFACE
    surface_alt: str = SURFACE_ALT
    border: str = BORDER
    primary_text: str = PRIMARY_TEXT
    secondary_text: str = SECONDARY_TEXT
    primary_accent: str = PRIMARY_ACCENT
    accent_hover: str = ACCENT_HOVER


class ThemeManager:
    """Centralized theme access and stylesheet generation."""

    def __init__(self, theme: Theme | None = None) -> None:
        self._theme = theme or Theme()

    @property
    def theme(self) -> Theme:
        return self._theme

    def stylesheet(self) -> str:
        return build_stylesheet(self._theme)


def build_stylesheet(theme: Theme | None = None) -> str:
    theme = theme or Theme()
    return f"""
        * {{
            font-family: "Segoe UI";
            font-size: 14px;
            color: {theme.primary_text};
        }}

        QWidget {{
            background: {theme.background};
        }}

        QMainWindow {{
            background: {theme.background};
        }}

        QFrame#ShellSidebar {{
            background: {theme.surface};
            border-right: 1px solid {theme.border};
        }}

        QFrame#ShellContent {{
            background: {theme.background};
        }}

        QFrame#Card, QFrame#SurfaceAltCard {{
            border: 1px solid {theme.border};
            border-radius: 16px;
        }}

        QFrame#Card {{
            background: {theme.surface};
        }}

        QFrame#SurfaceAltCard {{
            background: {theme.surface_alt};
        }}

        QLabel#AppBrand {{
            color: {theme.primary_accent};
            font-size: 24px;
            font-weight: 800;
            letter-spacing: 1px;
        }}

        QLabel#AppSubtitle {{
            color: {theme.secondary_text};
            font-size: 11px;
        }}

        QLabel#SectionEyebrow {{
            color: {theme.primary_accent};
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 2px;
        }}

        QLabel#PageTitle {{
            color: {theme.primary_text};
            font-size: 26px;
            font-weight: 700;
        }}

        QLabel#PageSubtitle {{
            color: {theme.secondary_text};
            font-size: 13px;
        }}

        QPushButton[role="nav"] {{
            background: transparent;
            border: 0;
            border-left: 3px solid transparent;
            color: {theme.secondary_text};
            padding: 12px 16px;
            text-align: left;
        }}

        QPushButton[role="nav"]:hover {{
            background: {theme.surface_alt};
            color: {theme.primary_text};
        }}

        QPushButton[role="nav"][active="true"] {{
            background: {theme.surface_alt};
            border-left-color: {theme.primary_accent};
            color: {theme.primary_accent};
        }}

        QPushButton[role="primary"] {{
            background: {theme.primary_accent};
            color: #111111;
            border: 0;
            border-radius: 12px;
            padding: 10px 16px;
            font-weight: 700;
        }}

        QPushButton[role="primary"]:hover {{
            background: {theme.accent_hover};
        }}

        QPushButton[role="secondary"] {{
            background: {theme.surface_alt};
            color: {theme.primary_text};
            border: 1px solid {theme.border};
            border-radius: 12px;
            padding: 10px 16px;
            font-weight: 700;
        }}

        QPushButton[role="secondary"]:hover {{
            border-color: {theme.primary_accent};
        }}

        QProgressBar {{
            background: {theme.surface_alt};
            border: 1px solid {theme.border};
            border-radius: 10px;
            text-align: center;
            color: {theme.primary_text};
            height: 20px;
        }}

        QProgressBar::chunk {{
            background: {theme.primary_accent};
            border-radius: 10px;
        }}

        QStatusBar {{
            background: {theme.background};
            border-top: 1px solid {theme.border};
            color: {theme.secondary_text};
        }}
    """
