"""System-tray entry point for the settings and runtime controls."""

from __future__ import annotations

from PyQt6.QtGui import QAction, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon


def _make_icon() -> QIcon:
    """Draw a simple icon so the executable has no icon-file dependency."""
    pixmap = QPixmap(32, 32)
    pixmap.fill()
    painter = QPainter(pixmap)
    painter.drawEllipse(4, 4, 24, 24)
    painter.end()
    return QIcon(pixmap)


class TrayIcon(QSystemTrayIcon):
    def __init__(self, on_toggle, on_select_region, on_settings, on_quit) -> None:
        super().__init__(_make_icon())
        self.setToolTip("waen — screen translation glasses")

        menu = QMenu()
        for label, handler in (
            ("Start / stop", on_toggle),
            ("Select region…", on_select_region),
            ("Settings…", on_settings),
        ):
            action = QAction(label, menu)
            action.triggered.connect(handler)
            menu.addAction(action)
        menu.addSeparator()
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(on_quit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)
        self._menu = menu
