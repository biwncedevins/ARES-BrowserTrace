from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.timeforge import TimeForge
from ...models import Severity
from .. import theme
from ..widgets.panels import StatCard


class OverviewPage(QWidget):
    def __init__(self, session, on_navigate, parent=None):
        super().__init__(parent)
        self.session = session
        self.on_navigate = on_navigate
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 18)
        root.setSpacing(14)

        head = QVBoxLayout()
        head.setSpacing(2)
        t = QLabel("Overview")
        t.setObjectName("PageTitle")
        sub = QLabel("Case summary, source details and the most important findings.")
        sub.setObjectName("PageSub")
        head.addWidget(t)
        head.addWidget(sub)
        root.addLayout(head)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(10)
        self.cards = {}
        for label in ("Events", "Visits", "Downloads", "Bookmarks", "Domains", "Findings"):
            card = StatCard(label)
            self.cards[label.lower()] = card
            stats_row.addWidget(card)
        root.addLayout(stats_row)

        grid = QGridLayout()
        grid.setSpacing(12)

        source_card = QFrame()
        source_card.setProperty("card", True)
        sc_lay = QVBoxLayout(source_card)
        sc_lay.setContentsMargins(16, 12, 16, 12)
        sc_lay.setSpacing(6)
        sc_title = QLabel("SOURCE")
        sc_title.setObjectName("SectionCaption")
        self.source_label = QLabel("No source loaded")
        self.source_label.setObjectName("PageTitle")
        self.source_detail = QLabel("Select a browser profile or artifact files to begin.")
        self.source_detail.setProperty("muted", True)
        self.source_detail.setWordWrap(True)
        self.warning_list = QLabel("")
        self.warning_list.setProperty("muted", True)
        self.warning_list.setWordWrap(True)
        self.warning_list.hide()
        self.source_files = QLabel("")
        self.source_files.setObjectName("SectionCaption")
        self.source_files.setWordWrap(True)
        sc_lay.addWidget(sc_title)
        sc_lay.addWidget(self.source_label)
        sc_lay.addWidget(self.source_detail)
        sc_lay.addWidget(self.source_files)
        sc_lay.addWidget(self.warning_list)
        grid.addWidget(source_card, 0, 0)

        proc_card = QFrame()
        proc_card.setProperty("card", True)
        pl = QVBoxLayout(proc_card)
        pl.setContentsMargins(16, 12, 16, 12)
        pl.setSpacing(6)
        pt = QLabel("PROCESSING")
        pt.setObjectName("SectionCaption")
        self.proc_duration = QLabel("—")
        self.proc_duration.setObjectName("PageTitle")
        self.proc_range = QLabel("Time range unknown")
        self.proc_range.setProperty("muted", True)
        self.proc_note = QLabel("All parsing, timestamp normalization, grouping and heuristics ran "
                                "locally on this machine. No data left the device and no credentials "
                                "were accessed.")
        self.proc_note.setProperty("muted", True)
        self.proc_note.setWordWrap(True)
        pl.addWidget(pt)
        pl.addWidget(self.proc_duration)
        pl.addWidget(self.proc_range)
        pl.addWidget(self.proc_note)
        grid.addWidget(proc_card, 0, 1)

        find_card = QFrame()
        find_card.setProperty("card", True)
        fl = QVBoxLayout(find_card)
        fl.setContentsMargins(16, 12, 16, 12)
        fl.setSpacing(8)
        ft = QLabel("TOP FINDINGS")
        ft.setObjectName("SectionCaption")
        fl.addWidget(ft)
        self.findings_table = QTableWidget(0, 4)
        self.findings_table.setHorizontalHeaderLabels(["Severity", "Category", "Title", "Domain"])
        self.findings_table.setShowGrid(False)
        self.findings_table.verticalHeader().setVisible(False)
        self.findings_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.findings_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.findings_table.setSelectionMode(QTableWidget.SingleSelection)
        self.findings_table.horizontalHeader().setStretchLastSection(True)
        self.findings_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.findings_table.verticalHeader().setDefaultSectionSize(24)
        self.findings_table.setMaximumHeight(300)
        self.findings_table.doubleClicked.connect(self.open_findings)
        fl.addWidget(self.findings_table)
        grid.addWidget(find_card, 1, 0, 1, 2)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        root.addLayout(grid, 1)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        btn_timeline = QPushButton("Open Timeline")
        btn_timeline.setObjectName("primary")
        btn_findings = QPushButton("Open Findings")
        btn_timeline.clicked.connect(lambda: self.on_navigate("timeline"))
        btn_findings.clicked.connect(lambda: self.on_navigate("findings"))
        actions.addWidget(btn_timeline)
        actions.addWidget(btn_findings)
        actions.addStretch(1)
        root.addLayout(actions)

    def set_session(self, session):
        self.session = session
        stats = session.stats or {}
        mapping = {
            "events": stats.get("total", 0),
            "visits": stats.get("visits", 0),
            "downloads": stats.get("downloads", 0),
            "bookmarks": stats.get("bookmarks", 0),
            "domains": stats.get("domains", 0),
            "findings": len(session.findings),
        }
        for key, value in mapping.items():
            card = self.cards.get(key)
            if card:
                card.set_value(value)
        source = session.source
        if source:
            self.source_label.setText(source.label)
            parts = []
            if source.history_file:
                parts.append(source.history_file)
            if source.is_firefox:
                parts = [source.history_file]
            if not source.is_firefox and source.bookmarks_file:
                parts.append(source.bookmarks_file)
            self.source_detail.setText(source.origin or "manual selection")
            self.source_files.setText(" · ".join(parts) or "No files")
        else:
            self.source_label.setText("No source loaded")
            self.source_detail.setText("Select a browser profile or artifact files to begin.")
            self.source_files.setText("")
        if session.warnings:
            self.warning_list.setText("; ".join(session.warnings))
            self.warning_list.show()
        else:
            self.warning_list.hide()
        if session.time_min and session.time_max:
            self.proc_range.setText(
                f"{TimeForge.iso_utc(session.time_min)}  →  {TimeForge.iso_utc(session.time_max)}"
            )
        else:
            self.proc_range.setText("No timestamped events in range")
        self.proc_duration.setText(f"{session.load_duration_s:.2f}s to analyze")
        self._fill_findings()

    def _fill_findings(self):
        table = self.findings_table
        rows = sorted(self.session.findings, key=lambda f: (-f.severity.rank, f.id))
        table.setRowCount(len(rows))
        for r, f in enumerate(rows):
            sev = QTableWidgetItem(f.severity.label)
            sev.setForeground(QColor(theme.severity_color(f.severity.value)))
            category = QTableWidgetItem(f.category)
            category.setForeground(QColor(theme.MUTED))
            title = QTableWidgetItem(f.title)
            domain = QTableWidgetItem(f.domain)
            for col, item in ((0, sev), (1, category), (2, title), (3, domain)):
                table.setItem(r, col, item)

    def open_findings(self, *_):
        self.on_navigate("findings")

    def refresh_display(self):
        pass