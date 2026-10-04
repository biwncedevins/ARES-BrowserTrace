from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import QDateTime, QDate, QTime

from ...core.format import human_size
from ...models import Event, EventKind
from ..widgets.tables import EventTableModel, FilterProxy
from ..widgets.panels import KeyValuePanel, SeverityBadge

COLUMN_SET = {
    "timeline": ["time", "type", "domain", "detail", "profile"],
    "history": ["time", "domain", "title", "visits", "transition", "url"],
    "downloads": ["time", "domain", "file", "state", "size", "path"],
    "bookmarks": ["time", "domain", "title", "folder", "url"],
}


class FilterBar(QWidget):
    def __init__(self, session, kinds, with_times: bool, parent=None):
        super().__init__(parent)
        self.session = session
        self.kinds = kinds
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search URL, domain, title, file…")
        self.search.setClearButtonEnabled(True)
        self.search.setFixedWidth(280)
        lay.addWidget(self.search)

        if kinds:
            self.kind = QComboBox()
            self.kind.addItem("All types", None)
            for k in kinds:
                self.kind.addItem(k.label.title(), k.value)
            lay.addWidget(self.kind)
        else:
            self.kind = None

        self.domain = QComboBox()
        self.domain.setEditable(True)
        self.domain.setInsertPolicy(QComboBox.NoInsert)
        self.domain.setMinimumWidth(150)
        self.domain.addItem("All domains", None)
        lay.addWidget(self.domain)

        self.from_check = None
        self.to_check = None
        self.from_dt = None
        self.to_dt = None
        if with_times:
            self.from_check = QCheckBox("From")
            self.to_check = QCheckBox("To")
            self.from_dt = self._make_dt()
            self.to_dt = self._make_dt()
            lay.addWidget(self.from_check)
            lay.addWidget(self.from_dt)
            lay.addWidget(self.to_check)
            lay.addWidget(self.to_dt)
            for box, dt in ((self.from_check, self.from_dt), (self.to_check, self.to_dt)):
                box.toggled.connect(dt.setEnabled)
                dt.setEnabled(False)

        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setObjectName("primary")
        self.clear_btn = QPushButton("Clear")
        lay.addStretch(1)
        lay.addWidget(self.apply_btn)
        lay.addWidget(self.clear_btn)

        self.search.returnPressed.connect(self.apply_handler)
        self.apply_btn.clicked.connect(self.apply_handler)
        self.clear_btn.clicked.connect(self.clear_handler)

    def _make_dt(self) -> QDateTimeEdit:
        dt = QDateTimeEdit()
        dt.setCalendarPopup(True)
        dt.setDisplayFormat("dd MMM yyyy HH:mm")
        dt.setDateTime(QDateTime(QDate.currentDate().addDays(-1), QTime(0, 0)))
        return dt

    def set_time_defaults(self):
        lo = self.session.time_min
        hi = self.session.time_max
        if lo is not None:
            self.from_dt.setDateTime(QDateTime.fromSecsSinceEpoch(int(lo.timestamp()) - 3600))
        if hi is not None:
            self.to_dt.setDateTime(QDateTime.fromSecsSinceEpoch(int(hi.timestamp()) + 3600))

    def apply_handler(self):
        pass

    def clear_handler(self):
        self.search.clear()
        if self.kind is not None:
            self.kind.setCurrentIndex(0)
        self.domain.setCurrentIndex(0)
        if self.from_check:
            self.from_check.setChecked(False)
        if self.to_check:
            self.to_check.setChecked(False)
        self.apply_handler()

    def selected_kind(self):
        if self.kind is None or self.kind.currentIndex() <= 0:
            return None
        value = self.kind.currentData()
        if not value:
            return None
        try:
            return EventKind(value)
        except ValueError:
            return None

    def selected_domain(self):
        dom = self.domain.currentText().strip()
        return dom or None

    def bounds(self):
        t_from = None
        t_to = None
        if self.from_check and self.from_check.isChecked():
            t_from = float(self.from_dt.dateTime().toSecsSinceEpoch())
        if self.to_check and self.to_check.isChecked():
            t_to = float(self.to_dt.dateTime().toSecsSinceEpoch())
        return t_from, t_to

    def fill_domains(self):
        current = self.domain.currentText()
        self.domain.blockSignals(True)
        self.domain.clear()
        self.domain.addItem("All domains", None)
        for row in self.session.domains:
            self.domain.addItem(row.domain)
        self.domain.setCurrentText(current or "")
        self.domain.blockSignals(False)


class ArtifactPage(QWidget):
    TITLE = ""

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.model = EventTableModel(session, self)
        self.model.set_columns(COLUMN_SET[self.COLUMN_KEY])
        self.engine = FilterProxy(self.model)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 18)
        root.setSpacing(12)

        head = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        t = QLabel(self.TITLE)
        t.setObjectName("PageTitle")
        sub = QLabel(self.SUBTITLE)
        sub.setObjectName("PageSub")
        title_col.addWidget(t)
        title_col.addWidget(sub)
        head.addLayout(title_col)
        head.addStretch(1)
        self.count_label = QLabel("")
        self.count_label.setObjectName("PageSub")
        head.addWidget(self.count_label)
        root.addLayout(head)

        self.filter = self._make_filter()
        root.addWidget(self.filter)

        splitter = QSplitter(Qt.Horizontal)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setHighlightSections(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.verticalHeader().setDefaultSectionSize(26)
        self.table.setAlternatingRowColors(False)
        self.table.setWordWrap(False)
        self.table.doubleClicked.connect(self._on_double_click)

        self.detail = KeyValuePanel()
        splitter.addWidget(self.table)
        splitter.addWidget(self.detail)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([860, 380])
        root.addWidget(splitter, 1)

        self.filter.apply_handler = self._apply
        self.filter.clear_handler = self._clear
        self.table.selectionModel().currentChanged.connect(lambda cur, prev: self._show_detail(cur))

    # -- hooks ------------------------------------------------------------
    def _make_filter(self) -> FilterBar:
        return FilterBar(self.session, self.KINDS, self.WITH_TIMES)

    def _apply(self):
        self.engine.apply(
            query=self.filter.search.text(),
            kind=self.filter.selected_kind(),
            domain=self.filter.selected_domain(),
            time_from=self.filter.bounds()[0],
            time_to=self.filter.bounds()[1],
        )
        self._update_count()

    def _clear(self):
        self.engine.apply()
        self._update_count()

    def _update_count(self):
        total = self.model.rowCount()
        self.count_label.setText(f"{total:,} events")

    # -- session ----------------------------------------------------------
    def set_session(self, session):
        self.session = session
        self.model.session = session
        self.model.set_columns(COLUMN_SET[self.COLUMN_KEY])
        events = [e for e in session.events if e.kind in self.KINDS] if self.KINDS else list(session.events)
        self.model.set_events(events or [])
        self.filter.fill_domains()
        self.filter.set_time_defaults()
        self._clear()
        self.detail.clear()
        self.detail.set_header("No selection", "Select an event row to inspect its artifact details.")

    def refresh_display(self):
        self.model.refresh_display()
        idx = self.table.currentIndex()
        if idx.isValid():
            self._show_detail(idx)
        self._update_count()

    def _show_detail(self, index):
        if not index.isValid():
            return
        ev = self.model.event_at_row(index.row())
        if ev is None:
            return
        self.detail.set_header(f"{ev.kind.label} event", ev.id)
        self.detail.add_row("Time", f"{self.session.display_time(ev.timestamp)}"
                            + ("  (no timestamp recorded)" if ev.timestamp is None else ""))
        self.detail.add_row("Browser", f"{ev.browser} / {ev.profile}")
        self.detail.add_row("Domain", ev.domain or "—")
        if ev.kind == EventKind.VISIT:
            self.detail.add_row("Title", ev.title or "—")
            self.detail.add_row("URL", ev.url or "—")
            self.detail.add_row("Transition", ev.transition or "—")
            self.detail.add_row("Visit count", str(ev.visit_count))
            self.detail.add_row("From visit", ev.from_visit or "—")
        elif ev.kind == EventKind.DOWNLOAD:
            self.detail.add_row("Source URL", ev.url or "—")
            self.detail.add_row("Referrer", ev.referrer or "—")
            self.detail.add_row("File name", ev.file_name or "—")
            self.detail.add_row("Target path", ev.target_path or "—")
            self.detail.add_row("State", ev.state or "—")
            self.detail.add_row("Danger type", ev.danger_type or "—")
            self.detail.add_row("Size", human_size(ev.total_bytes)
                                + (f"  (received {human_size(ev.received_bytes)})" if ev.received_bytes else ""))
            self.detail.add_row("MIME", ev.mime_type or "—")
        elif ev.kind == EventKind.BOOKMARK:
            self.detail.add_row("Title", ev.title or "—")
            self.detail.add_row("URL", ev.url or "—")
            self.detail.add_row("Folder", ev.folder_path or "—")
        if ev.flags:
            self.detail.add_separator()
            for fid in ev.flags:
                finding = self._finding_by_id(fid)
                if finding:
                    badge = SeverityBadge(finding.severity.value)
                    self.detail._inner.insertWidget(max(0, self.detail._inner.count() - 1), badge)
                    lbl = QLabel(finding.title)
                    lbl.setWordWrap(True)
                    self.detail._inner.insertWidget(max(0, self.detail._inner.count() - 1), lbl)
                    self.detail._inner.addSpacing(6)
                    self.detail._rows.extend([badge, lbl])

    def _finding_by_id(self, fid):
        for f in self.session.findings:
            if f.id == fid:
                return f
        return None

    def _on_double_click(self, index):
        ev = self.model.event_at_row(index.row())
        if ev and ev.url:
            QApplication.clipboard().setText(ev.url)
            self.count_label.setText("URL copied to clipboard")

    def search_event(self, event_id: str) -> bool:
        self._clear()
        self.model.apply_filter()
        for row in range(self.model.rowCount()):
            ev = self.model.event_at_row(row)
            if ev and ev.id == event_id:
                self.table.selectRow(row)
                self.table.scrollTo(self.model.index(row, 0))
                self._show_detail(self.model.index(row, 0))
                return True
        ev = next((e for e in self.session.events if e.id == event_id), None)
        if ev:
            self.filter.search.setText(ev.url if ev.url else ev.title)
            self._apply()
        return False


class TimelinePage(ArtifactPage):
    TITLE = "Timeline"
    SUBTITLE = "Unified chronological view of visits, downloads and bookmark activity."
    COLUMN_KEY = "timeline"
    KINDS = [EventKind.VISIT, EventKind.DOWNLOAD, EventKind.BOOKMARK]
    WITH_TIMES = True


class HistoryPage(ArtifactPage):
    TITLE = "History"
    SUBTITLE = "Visited URLs, titles, transition types and per-URL visit counts."
    COLUMN_KEY = "history"
    KINDS = [EventKind.VISIT]
    WITH_TIMES = True


class DownloadsPage(ArtifactPage):
    TITLE = "Downloads"
    SUBTITLE = "Download records with source URLs, target paths, states and sizes."
    COLUMN_KEY = "downloads"
    KINDS = [EventKind.DOWNLOAD]
    WITH_TIMES = True


class BookmarksPage(ArtifactPage):
    TITLE = "Bookmarks"
    SUBTITLE = "Saved bookmarks with folder structure and creation times."
    COLUMN_KEY = "bookmarks"
    KINDS = [EventKind.BOOKMARK]
    WITH_TIMES = True