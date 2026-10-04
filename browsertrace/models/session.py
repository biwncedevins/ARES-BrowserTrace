from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from .findings import Severity


class Session(QObject):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.source = None
        self.events: list = []
        self.findings: list = []
        self.warnings: list = []
        self.domains: list = []
        self.stats: dict = {}
        self.event_severity: dict = {}
        self.time_min = None
        self.time_max = None
        self.display_local: bool = False
        self.load_duration_s: float = 0.0

    @classmethod
    def from_result(cls, result, parent=None) -> "Session":
        session = cls(parent)
        session.source = result.source
        session.events = result.events
        session.findings = result.findings
        session.warnings = result.warnings
        session.stats = result.stats
        session.domains = result.domains
        session.load_duration_s = result.duration_s
        times = [e.timestamp for e in result.events if e.timestamp is not None]
        session.time_min = min(times) if times else None
        session.time_max = max(times) if times else None
        for f in result.findings:
            for event_id in f.event_ids:
                session.event_severity[event_id] = f.severity.value
        return session

    def request_refresh(self) -> None:
        self.changed.emit()

    def display_time(self, ts) -> str:
        from ..core.timeforge import TimeForge

        if ts is None:
            return "—"
        if self.display_local:
            return TimeForge.display_local(ts)
        return TimeForge.display_utc(ts)

    def finding_count(self, at_least: Severity) -> int:
        return sum(1 for f in self.findings if f.severity.rank >= at_least.rank)