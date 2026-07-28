"""Reusable icon provider for the ClutchIQ desktop shell."""

from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QByteArray, QBuffer, QIODevice
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap

from clutchiq.theme import PRIMARY_ACCENT, PRIMARY_TEXT, SECONDARY_TEXT


class IconName(str, Enum):
    DASHBOARD = "dashboard"
    IMPORT = "import"
    MATCHES = "matches"
    REPLAY = "replay"
    ANALYTICS = "analytics"
    SETTINGS = "settings"
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    FOLDER = "folder"
    PLAY = "play"


class IconProvider:
    """Simple professional icon provider built from vector shapes."""

    @staticmethod
    def icon(name: IconName, color: str = PRIMARY_ACCENT, size: int = 20) -> QIcon:
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor(0, 0, 0, 0))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor(color))
        painter.setBrush(QColor(color))

        if name == IconName.DASHBOARD:
            painter.drawRect(3, 3, 6, 6)
            painter.drawRect(11, 3, 6, 6)
            painter.drawRect(3, 11, 6, 6)
            painter.drawRect(11, 11, 6, 6)
        elif name == IconName.IMPORT:
            painter.drawRect(4, 12, 12, 3)
            painter.drawRect(8, 4, 4, 8)
            painter.drawRect(6, 7, 8, 2)
        elif name == IconName.MATCHES:
            painter.drawRect(4, 4, 4, 12)
            painter.drawRect(12, 4, 4, 12)
            painter.drawRect(8, 8, 4, 4)
        elif name == IconName.REPLAY:
            painter.drawEllipse(4, 4, 12, 12)
            painter.fillRect(9, 6, 2, 5, QColor(0, 0, 0, 0))
        elif name == IconName.ANALYTICS:
            painter.drawRect(4, 12, 3, 4)
            painter.drawRect(9, 9, 3, 7)
            painter.drawRect(14, 6, 3, 10)
        elif name == IconName.SETTINGS:
            painter.drawEllipse(7, 7, 6, 6)
            painter.drawRect(9, 2, 2, 4)
            painter.drawRect(9, 14, 2, 4)
            painter.drawRect(2, 9, 4, 2)
            painter.drawRect(14, 9, 4, 2)
        elif name == IconName.INFO:
            painter.drawEllipse(8, 3, 4, 4)
            painter.drawRect(9, 8, 2, 9)
        elif name == IconName.SUCCESS:
            painter.drawRect(4, 9, 3, 2)
            painter.drawRect(7, 12, 3, 2)
            painter.drawRect(10, 9, 6, 2)
        elif name == IconName.WARNING:
            painter.drawRect(9, 5, 2, 8)
            painter.drawRect(9, 15, 2, 2)
        elif name == IconName.FOLDER:
            painter.drawRect(3, 7, 14, 9)
            painter.drawRect(3, 5, 6, 3)
        elif name == IconName.PLAY:
            painter.drawRect(5, 4, 3, 12)
            painter.drawRect(8, 6, 3, 8)
            painter.drawRect(11, 8, 3, 4)
        painter.end()
        return QIcon(pixmap)
