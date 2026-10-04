from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ...models import Severity
from ..widgets.panels import KeyValuePanel, SeverityBadge
from ..widgets.tables import FindingsTableModel


class FindingsPage(QWidget):
    def __init__(self, session, on_locate, parent=None):
        super().__init__(parent)
        self.session = session
        self.on_locate = on_locate
        self.model = FindingsTableModel(self)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 18)
        root.setSpacing(12)

        head = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        t = QLabel("Findings")
        t.setObjectName("PageTitle")
        sub = QLabel("Forensic heuristics flagged the following behaviors in the artifact set.")
        sub.setObjectName("PageSub")
        title_col.addWidget(t)
        title_col.addWidget(sub)
        head.addLayout(title_col)
        head.addStretch(1)

        self.severity = QComboBox()
        self.severity.addItem("All severities", None)
        for s in (Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO):
            self.severity.addItem(s.value.title(), s.value)
        self.severity.setFixedWidth(160)
        self.severity.currentIndexChanged.connect(self._apply_filter)
        self.count_label = QLabel("")
        self.count_label.setObjectName("PageSub")
        head.addWidget(self.severity)
        head.addWidget(self.count_label)
        root.addLayout(head)

        splitter = QSplitter(Qt.Horizontal)
        table = QTableView()
        table.setModel(self.model)
        table.setSortingEnabled(True)
        table.setSelectionBehavior(QTableView.SelectRows)
        table.setSelectionMode(QTableView.SingleSelection)
        table.setShowGrid(False)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        table.horizontalHeader().resizeSection(0, 88)
        table.verticalHeader().setDefaultSectionSize(28)
        table.selectionModel().currentChanged.connect(lambda cur, prev: self._show_detail(cur))

        self.detail = KeyValuePanel()

        splitter.addWidget(table)
        splitter.addWidget(self.detail)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([940, 400])
        root.addWidget(splitter, 1)

    def set_session(self, session):
        self.session = session
        self._apply_filter()

    def _apply_filter(self, *_):
        sev = self.severity.currentData()
        findings = session_findings = self.session.findings
        rows = [f for f in session_findings if sev is None or f.severity.value == sev]
        rows.sort(key=lambda f: (-f.severity.rank, f.id))
        self.model.set_findings(rows)
        self.count_label.setText(f"{len(rows)} findings")
        self.detail.clear()
        self.detail.set_header("No finding selected", "Select a finding to review its description and related events.")

    def _show_detail(self, index):
        if not index.isValid():
            return
        f = self.model.finding_at_row(index.row())
        if f is None:
            return
        self.current_finding = f
        self.detail.set_header(f"{f.category}", f"{f.title}")
        badge = SeverityBadge(f.severity.value)
        self._append_widget(badge)
        label = QLabel(f.detail or "")
        label.setWordWrap(True)
        self._append_widget(label)
        self.detail.add_separator()
        self.detail.add_row("Domain", f.domain or "—")
        self.detail.add_row("Events flagged", str(len(f.event_ids)) + (f"  (count: {f.count})" if f.count > 1 else ""))
        if f.timestamps:
            self.detail.add_row("First timestamp", self.session.display_time(f.timestamps[0]))
        if f.event_ids:
            self.detail.add_separator()
            self.detail.add_row("Related events", ", ".join(f.event_ids[:30]))
        btn = QPushButton("Locate in Timeline")
        btn.clicked.connect(self._locate)
        btn.setEnabled(bool(f.event_ids))
        self._append_widget(btn)

    def _append_widget(self, w):
        lay = self.detail._inner
        lay.insertWidget(max(0, lay.count() - 1), w)
        lay.addSpacing(8)
        self.detail._rows.append(w)

    def _locate(self):
        f = getattr(self, "current_finding", None)
        if f and f.event_ids and self.on_locate:
            self.on_locate(f.event_ids[0])

    def refresh_display(self):
        self._apply_filter()