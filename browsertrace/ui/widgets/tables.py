from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor, QFont

from .. import theme
from ...core.format import human_size
from ...models import Event, EventKind, Finding


def _epoch(dt_maybe) -> float:
    if dt_maybe is None:
        return 0.0
    return dt_maybe.timestamp()


class EventTableModel(QAbstractTableModel):
    """Flat filtered table over a list of Timeline events."""

    COLUMNS = [
        ("time", "Time"),
        ("type", "Type"),
        ("domain", "Domain"),
        ("detail", "Detail"),
        ("title", "Title"),
        ("profile", "Browser"),
        ("url", "URL"),
        ("visits", "Visits"),
        ("transition", "Transition"),
        ("file", "File"),
        ("path", "Target Path"),
        ("size", "Size"),
        ("state", "State"),
        ("folder", "Folder"),
    ]
    MONO_KEYS = {"time", "domain", "url", "path", "file", "profile"}
    NUMERIC_KEYS = {"visits", "size"}

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self._all: list = []
        self._rows: list = []
        self._visible_keys: list = None
        self._severity_map: dict = {}
        self.query = ""
        self.kind: EventKind | None = None
        self.domain: str | None = None
        self.time_from = None
        self.time_to = None

    def set_columns(self, keys: list) -> None:
        self._visible_keys = keys
        self._severity_map.clear()
        if self.session and self.session.findings:
            for f in self.session.findings:
                for eid in f.event_ids:
                    self._severity_map[eid] = f.severity.value

    def set_events(self, events: list) -> None:
        self.beginResetModel()
        self._all = sorted(
            list(events),
            key=lambda e: (e.timestamp.timestamp() if e.timestamp else 0.0, e.id),
            reverse=True,
        )
        self._rows = list(range(len(self._all)))
        self.endResetModel()

    def sort(self, column, order=Qt.AscendingOrder) -> None:
        if not self._rows:
            return
        key = self._visible_keys[column]

        def value(ev: Event):
            if key == "time":
                return _epoch(ev.timestamp)
            if key == "size":
                return ev.total_bytes
            if key == "visits":
                return ev.visit_count
            if key == "type":
                return ev.kind.value
            if key == "domain":
                return ev.domain.lower()
            return self._display(ev, key).lower()

        self.beginResetModel()
        self._rows.sort(key=lambda r: value(self._all[r]), reverse=(order == Qt.DescendingOrder))
        self.endResetModel()

    def apply_filter(self) -> None:
        self.beginResetModel()
        q = self.query.lower().strip()
        self._rows = [
            i for i, ev in enumerate(self._all)
            if self._matches(ev, q)
        ]
        self.endResetModel()

    def refresh_display(self) -> None:
        if not self._rows:
            return
        top_left = self.index(0, 0)
        bottom_right = self.index(len(self._rows) - 1, self.columnCount() - 1)
        self.dataChanged.emit(top_left, bottom_right, [])

    def _matches(self, ev: Event, q: str) -> bool:
        if self.kind is not None and ev.kind != self.kind:
            return False
        if self.domain and ev.domain != self.domain:
            return False
        if ev.timestamp is not None:
            t = _epoch(ev.timestamp)
            if self.time_from is not None and t < self.time_from:
                return False
            if self.time_to is not None and t > self.time_to:
                return False
        elif self.time_from is not None or self.time_to is not None:
            return False
        if q:
            hay = " ".join([
                str(ev.domain), str(ev.title), str(ev.url), str(ev.file_name),
                str(ev.target_path), str(ev.folder_path), str(ev.transition),
                str(ev.state), ev.kind.value,
            ]).lower()
            if q not in hay:
                return False
        return True

    def event_at_row(self, row: int) -> Event | None:
        if 0 <= row < len(self._rows):
            return self._all[self._rows[row]]
        return None

    # ---- Qt model interface ----
    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self._visible_keys or [])

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            key = self._visible_keys[section]
            label = dict(self.COLUMNS)[key]
            return label.upper()
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        ev = self.event_at_row(index.row())
        if ev is None:
            return None
        key = self._visible_keys[index.column()]
        if role == Qt.DisplayRole:
            return self._display(ev, key)
        if role == Qt.FontRole and key in self.MONO_KEYS:
            font = QFont("Consolas")
            font.setPointSize(9)
            return font
        if role == Qt.ForegroundRole:
            return self._foreground(ev, key)
        if role == Qt.ToolTipRole:
            text = self._display(ev, key)
            return text if text and len(text) > 40 else None
        return None

    def _display(self, ev: Event, key: str):
        if key == "time":
            return self.session.display_time(ev.timestamp)
        if key == "type":
            return ev.kind.label
        if key == "domain":
            return ev.domain or "—"
        if key == "detail":
            return ev.detail or "—"
        if key == "title":
            return ev.title or "—"
        if key == "profile":
            return f"{ev.browser} · {ev.profile}"
        if key == "url":
            return ev.url or "—"
        if key == "visits":
            return str(ev.visit_count)
        if key == "transition":
            return ev.transition or "—"
        if key == "file":
            return ev.file_name or "—"
        if key == "path":
            return ev.target_path or ev.referrer or "—"
        if key == "size":
            return human_size(ev.total_bytes) or "—"
        if key == "state":
            return ev.state or "—"
        if key == "folder":
            return ev.folder_path or "—"
        return ""

    def _foreground(self, ev: Event, key: str):
        sev = self._severity_map.get(ev.id)
        if key == "type":
            return QColor(theme.KIND_COLORS.get(ev.kind.value, theme.TEXT))
        if key == "domain" and sev and sev != "info":
            return QColor(theme.severity_color(sev))
        if key in ("file", "path") and ev.kind == EventKind.DOWNLOAD and ev.state not in ("", "COMPLETE"):
            return QColor(theme.SEV_MEDIUM)
        if ev.timestamp is None and key == "time":
            return QColor(theme.DIM)
        return None


class FilterProxy:
    """Helper shared by pages to keep one filter model + count label in sync."""

    def __init__(self, model: EventTableModel):
        self.model = model

    def apply(self, query="", kind=None, domain=None, time_from=None, time_to=None):
        self.model.query = query
        self.model.kind = kind
        self.model.domain = domain
        self.model.time_from = time_from
        self.model.time_to = time_to
        self.model.apply_filter()
        return self.model.rowCount()


class FindingsTableModel(QAbstractTableModel):
    COLUMNS = ["severity", "category", "title", "domain", "time", "count"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.findings = []

    def set_findings(self, findings: list) -> None:
        self.beginResetModel()
        self.findings = list(findings)
        self.endResetModel()

    def finding_at_row(self, row: int):
        if 0 <= row < len(self.findings):
            return self.findings[row]
        return None

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.findings)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.COLUMNS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.COLUMNS[section].upper()
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        f = self.finding_at_row(index.row())
        if f is None:
            return None
        key = self.COLUMNS[index.column()]
        if role == Qt.DisplayRole:
            if key == "severity":
                return f.severity.label
            if key == "category":
                return f.category
            if key == "title":
                return f.title
            if key == "domain":
                return f.domain or "—"
            if key == "time":
                return f.timestamps[0].strftime("%Y-%m-%d %H:%M:%S UTC") if f.timestamps else "—"
            if key == "count":
                return str(f.count)
        if role == Qt.FontRole and key in ("domain", "time"):
            font = QFont("Consolas")
            font.setPointSize(9)
            return font
        if role == Qt.ForegroundRole:
            if key == "severity":
                return QColor(theme.severity_color(f.severity.value))
            if key == "domain" and f.domain:
                color = theme.severity_color(f.severity.value)
                return QColor(color if f.severity.value != "info" else theme.MUTED)
            if key == "title":
                return QColor(theme.severity_color(f.severity.value))
        return None


class DomainsTableModel(QAbstractTableModel):
    COLUMNS = ("domain", "events", "visits", "downloads", "bookmarks", "first", "last")

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.domains = []

    def set_domains(self, domains: list) -> None:
        self.beginResetModel()
        self.domains = list(domains)
        self.endResetModel()

    def domain_at_row(self, row: int):
        if 0 <= row < len(self.domains):
            return self.domains[row]
        return None

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.domains)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.COLUMNS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            names = {"events": "Events", "visits": "Visits", "downloads": "Downl.",
                     "bookmarks": "Bmarks", "first": "First Seen (UTC)", "last": "Last Seen (UTC)"}
            return names.get(self.COLUMNS[section], self.COLUMNS[section]).upper()
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self.domain_at_row(index.row())
        if row is None:
            return None
        key = self.COLUMNS[index.column()]
        if role == Qt.DisplayRole:
            if key == "domain":
                return row.domain
            if key == "events":
                return str(row.total)
            if key == "visits":
                return str(row.visits)
            if key == "downloads":
                return str(row.downloads)
            if key == "bookmarks":
                return str(row.bookmarks)
            if key == "first":
                return self.session.display_time(row.first_seen)
            if key == "last":
                return self.session.display_time(row.last_seen)
        if role == Qt.FontRole and key == "domain":
            font = QFont("Consolas")
            font.setPointSize(9)
            return font
        if role == Qt.ForegroundRole:
            if key == "domain":
                if row.downloads:
                    return QColor(theme.SEV_MEDIUM)
                if row.total >= 50:
                    return QColor(theme.TEXT)
                return QColor(theme.SEV_LOW)
            if key in ("first", "last"):
                return QColor(theme.MUTED)
        return None