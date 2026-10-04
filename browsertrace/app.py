from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from . import __version__
from .resources import icon_path
from .ui import MainWindow, apply


def main() -> int:
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, False)
    app = QApplication(sys.argv)
    app.setApplicationName("BrowserTrace")
    app.setApplicationDisplayName("BrowserTrace")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("BrowserTrace")
    app.setWindowIcon(icon_path())
    apply(app)
    window = MainWindow()
    window.show()
    if "--pick-source" in sys.argv:
        window.load_source()
    return app.exec()