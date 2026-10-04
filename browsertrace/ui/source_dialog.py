from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import theme
from ..models import SourceProfile
from ..parsing import detect_profiles, resolve_source

BROWSER_ICONS = {
    "chrome": "#F4C430",
    "edge": "#3AA0A6",
    "firefox": "#E08537",
    "chromium": "#7A828C",
}


def _browser_color(browser: str) -> str:
    return BROWSER_ICONS.get(browser, theme.MUTED)


class _ProfileListItem(QWidget):
    def __init__(self, profile: SourceProfile, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(10)
        dot = QLabel("●")
        dot.setStyleSheet(f"color:{_browser_color(profile.browser)}; font-size:12px;")
        text_col = QVBoxLayout()
        text_col.setSpacing(0)
        name = QLabel(profile.label)
        path = QLabel(profile.root or (profile.history_file or profile.places_file))
        path.setProperty("dimmed", True)
        path.setStyleSheet("font-size:10px;")
        text_col.addWidget(name)
        text_col.addWidget(path)
        lay.addWidget(dot)
        lay.addLayout(text_col, 1)


class SourceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Source — BrowserTrace")
        self.setMinimumSize(760, 520)
        self._manual_folder = ""
        self._manual_files = []
        self._profiles = []
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(12)

        head = QVBoxLayout()
        head.setSpacing(2)
        title = QLabel("Select a source to analyze")
        title.setObjectName("PageTitle")
        sub = QLabel("Choose an auto-detected browser profile, a profile folder, or individual artifact files.")
        sub.setObjectName("PageSub")
        head.addWidget(title)
        head.addWidget(sub)
        root.addLayout(head)

        self.list = QListWidget()
        self.list.setSpacing(2)
        self.list.itemDoubleClicked.connect(self._accept)
        profiles = detect_profiles()
        self._profiles = profiles
        if not profiles:
            item = QListWidgetItem("No installed profiles detected on this machine.")
            item.setFlags(Qt.ItemIsEnabled)
            self.list.addItem(item)
        for p in profiles:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, p)
            available = p.has_history
            item.setIcon(QIcon())
            self.list.addItem(item)
            self.list.setItemWidget(item, _ProfileListItem(p))
            if not available:
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)

        manual_card = QFrame()
        manual_card.setProperty("card", True)
        mc = QVBoxLayout(manual_card)
        mc.setContentsMargins(14, 12, 14, 12)
        mc.setSpacing(8)
        mc_title = QLabel("MANUAL SELECTION")
        mc_title.setObjectName("SectionCaption")
        mc.addWidget(mc_title)
        btn_row = QHBoxLayout()
        self.btn_folder = QPushButton("Choose Profile Folder…")
        self.btn_files = QPushButton("Open Artifact Files…")
        self.btn_folder.clicked.connect(self._pick_folder)
        self.btn_files.clicked.connect(self._pick_files)
        btn_row.addWidget(self.btn_folder)
        btn_row.addWidget(self.btn_files)
        btn_row.addStretch(1)
        mc.addLayout(btn_row)
        self.manual_note = QLabel("No manual selection yet.")
        self.manual_note.setProperty("muted", True)
        self.manual_note.setWordWrap(True)
        mc.addWidget(self.manual_note)
        root.addWidget(self.list, 1)
        root.addWidget(manual_card)

        scope = QHBoxLayout()
        scope.setSpacing(14)
        scope.addWidget(QLabel("Parse:"))
        self.ch_history = QCheckBox("History")
        self.ch_downloads = QCheckBox("Downloads")
        self.ch_bookmarks = QCheckBox("Bookmarks")
        for box in (self.ch_history, self.ch_downloads, self.ch_bookmarks):
            box.setChecked(True)
            scope.addWidget(box)
        scope.addStretch(1)
        root.addLayout(scope)

        buttons = QHBoxLayout()
        note = QLabel("All processing runs locally and offline. Credentials are never accessed.")
        note.setProperty("dimmed", True)
        buttons.addWidget(note, 1)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        self.btn_ok = QPushButton("Analyze")
        self.btn_ok.setObjectName("primary")
        self.btn_ok.clicked.connect(self._accept)
        buttons.addWidget(btn_cancel)
        buttons.addWidget(self.btn_ok)
        root.addLayout(buttons)

    def _pick_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Choose a browser profile folder")
        if not path:
            return
        self._manual_folder = path
        self._manual_files = []
        self.list.clearSelection()
        self.manual_note.setText(f"Folder: {path}")

    def _pick_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Choose browser artifact files",
            "",
            "Browser artifacts (*.sqlite *.db *.json History Bookmarks places.sqlite);;All files (*)",
        )
        if not paths:
            return
        self._manual_files = paths
        self._manual_folder = ""
        self.list.clearSelection()
        self.manual_note.setText("Files:\n" + "\n".join(paths))

    def sections(self) -> tuple:
        return (self.ch_history.isChecked(), self.ch_downloads.isChecked(), self.ch_bookmarks.isChecked())

    def resolve(self):
        if self._manual_folder:
            return resolve_source(folder=self._manual_folder)
        if self._manual_files:
            return resolve_source(files=self._manual_files)
        item = self.list.currentItem()
        if item and item.data(Qt.UserRole):
            profile = item.data(Qt.UserRole)
            return resolve_source(profile=profile)
        return None

    def _accept(self, *_):
        if self.resolve() is None:
            QMessageBox.information(self, "Select a source", "Choose a detected profile, a folder, or artifact files.")
            return
        self.accept()