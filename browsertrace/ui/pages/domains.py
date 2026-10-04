from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ..widgets.tables import DomainsTableModel, EventTableModel
from ..widgets.panels import KeyValuePanel


class DomainsPage(QWidget):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.domain_model = DomainsTableModel(session, self)
        self.event_model = EventTableModel(session, self)
        self.event_model.set_columns(["time", "type", "detail", "url"])
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 18)
        root.setSpacing(12)

        head = QVBoxLayout()
        head.setSpacing(2)
        t = QLabel("Domains")
        t.setObjectName("PageTitle")
        sub = QLabel("Activity grouped by domain. Select a domain to inspect its events below.")
        sub.setObjectName("PageSub")
        head.addWidget(t)
        head.addWidget(sub)
        self.count_label = QLabel("")
        self.count_label.setObjectName("PageSub")
        head.addWidget(self.count_label)
        root.addLayout(head)

        split = QSplitter(Qt.Horizontal)
        left = QTableView()
        left.setModel(self.domain_model)
        left.setSortingEnabled(True)
        left.setSelectionBehavior(QTableView.SelectRows)
        left.setSelectionMode(QTableView.SingleSelection)
        left.setShowGrid(False)
        left.verticalHeader().setVisible(False)
        left.horizontalHeader().setStretchLastSection(True)
        left.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        left.verticalHeader().setDefaultSectionSize(26)
        left.horizontalHeader().resizeSection(0, 220)
        left.selectionModel().currentChanged.connect(self._domain_selected)

        right = QSplitter(Qt.Vertical)

        bottom_table = QTableView()
        bottom_table.setModel(self.event_model)
        bottom_table.setSortingEnabled(True)
        bottom_table.setSelectionBehavior(QTableView.SelectRows)
        bottom_table.setSelectionMode(QTableView.SingleSelection)
        bottom_table.setShowGrid(False)
        bottom_table.verticalHeader().setVisible(False)
        bottom_table.horizontalHeader().setStretchLastSection(True)
        bottom_table.verticalHeader().setDefaultSectionSize(26)
        bottom_table.doubleClicked.connect(self._copy_url)

        self.detail = KeyValuePanel()

        right.addWidget(bottom_table)
        right.addWidget(self.detail)
        right.setStretchFactor(0, 2)
        right.setStretchFactor(1, 1)
        right.setSizes([320, 220])

        split.addWidget(left)
        split.addWidget(right)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 2)
        split.setSizes([420, 820])
        root.addWidget(split, 1)

        bottom_table.selectionModel().currentChanged.connect(lambda cur, prev: self._show_event(cur))

    def set_session(self, session):
        self.session = session
        self.domain_model.session = session
        self.event_model.session = session
        self.domain_model.set_domains(session.domains or [])
        self.event_model.set_events(list(session.events) if session else [])
        self.event_model.apply_filter()
        self.count_label.setText(f"{len(session.domains or [])} domains")
        self.detail.clear()
        self.detail.set_header("No domain selected", "Select a domain to view its aggregated metrics.")

    def _domain_selected(self, current, *_):
        row = self.domain_model.domain_at_row(current.row())
        if row is None:
            return
        events = [e for e in self.session.events if e.domain == row.domain]
        self.event_model.set_events(events)
        self.event_model.apply_filter()
        self.detail.set_header(row.domain, f"{row.total} events total")
        self.detail.add_row("Visits", str(row.visits))
        self.detail.add_row("Downloads", str(row.downloads))
        self.detail.add_row("Bookmarks", str(row.bookmarks))
        self.detail.add_row("First seen", self.session.display_time(row.first_seen))
        self.detail.add_row("Last seen", self.session.display_time(row.last_seen))
        span = f"{row.days_span:.1f} days" if row.days_span else "—"
        self.detail.add_row("Span", span)
        self.detail.add_row("Sources", "; ".join(row.sources))

    def _show_event(self, current):
        if not current.isValid():
            return
        ev = self.event_model.event_at_row(current.row())
        if ev is None:
            return
        self.detail.set_header(f"{ev.kind.label.upper()} event", ev.id)
        self.detail.add_row("Time", self.session.display_time(ev.timestamp))
        self.detail.add_row("Domain", ev.domain or "—")
        self.detail.add_row("Detail", ev.detail or ev.title or ev.url or "—")
        self.detail.add_row("URL", ev.url or ev.target_path or "—")

    def _copy_url(self, index):
        ev = self.event_model.event_at_row(index.row())
        if ev and ev.url:
            from PySide6.QtWidgets import QApplication

            QApplication.clipboard().setText(ev.url)

    def refresh_display(self):
        self.domain_model.set_domains(self.session.domains or [])
        self.event_model.refresh_display()