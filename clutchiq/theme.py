"""Centralized visual theme for the ClutchIQ interface."""

from __future__ import annotations


BACKGROUND = "#090909"
SURFACE = "#121212"
SURFACE_HOVER = "#1c1c1c"
YELLOW = "#f5c400"
YELLOW_HOVER = "#ffd52e"
TEXT_PRIMARY = "#f5f5f5"
TEXT_MUTED = "#9b9b9b"
BORDER = "#282828"


def build_stylesheet() -> str:
    """Build the global black-and-yellow Qt stylesheet."""
    return f"""
        QWidget {{
            background-color: {BACKGROUND};
            color: {TEXT_PRIMARY};
            font-family: "Segoe UI", "Arial", sans-serif;
            font-size: 14px;
        }}

        QMainWindow {{
            background-color: {BACKGROUND};
        }}

        QFrame#sidebar {{
            background-color: {SURFACE};
            border-right: 1px solid {BORDER};
        }}

        QLabel#brandMark {{
            color: {YELLOW};
            font-size: 25px;
            font-weight: 800;
            letter-spacing: 1px;
        }}

        QLabel#brandTagline {{
            color: {TEXT_MUTED};
            font-size: 11px;
            font-weight: 600;
        }}

        QPushButton#navigationButton {{
            background-color: transparent;
            border: none;
            border-left: 3px solid transparent;
            border-radius: 0;
            color: {TEXT_MUTED};
            font-size: 14px;
            font-weight: 600;
            padding: 13px 18px;
            text-align: left;
        }}

        QPushButton#navigationButton:hover {{
            background-color: {SURFACE_HOVER};
            color: {TEXT_PRIMARY};
        }}

        QPushButton#navigationButton[active="true"] {{
            background-color: {SURFACE_HOVER};
            border-left-color: {YELLOW};
            color: {YELLOW};
        }}

        QLabel#welcomeEyebrow {{
            color: {YELLOW};
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 2px;
        }}

        QLabel#welcomeTitle {{
            color: {TEXT_PRIMARY};
            font-size: 38px;
            font-weight: 700;
        }}

        QLabel#welcomeSubtitle {{
            color: {TEXT_MUTED};
            font-size: 15px;
        }}

        QFrame#accentLine {{
            background-color: {YELLOW};
            border: none;
        }}

        QStatusBar {{
            background-color: {BACKGROUND};
            border-top: 1px solid {BORDER};
            color: {TEXT_MUTED};
            font-size: 12px;
        }}
    """
