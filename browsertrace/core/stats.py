from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..models import Event, EventKind


@dataclass
class DomainAggregate:
    domain: str
    total: int = 0
    visits: int = 0
    downloads: int = 0
    bookmarks: int = 0
    first_seen: datetime = None
    last_seen: datetime = None
    sources: list = field(default_factory=list)

    @property
    def days_span(self) -> float:
        if self.first_seen and self.last_seen and self.last_seen > self.first_seen:
            return (self.last_seen - self.first_seen).total_seconds() / 86400.0
        return 0.0


def compute_stats(events: list) -> dict:
    kinds = defaultdict(int)
    browsers = defaultdict(int)
    domains = defaultdict(int)
    with_time = 0
    for ev in events:
        kinds[ev.kind] += 1
        browsers[ev.browser] += 1
        if ev.domain:
            domains[ev.domain] += 1
        if ev.timestamp is not None:
            with_time += 1
    by_severity = {"info": 0, "low": 0, "medium": 0, "high": 0}
    return {
        "total": len(events),
        "visits": kinds.get(EventKind.VISIT, 0),
        "downloads": kinds.get(EventKind.DOWNLOAD, 0),
        "bookmarks": kinds.get(EventKind.BOOKMARK, 0),
        "browsers": dict(browsers),
        "domains": len(domains),
        "with_time": with_time,
        "findings": {"info": 0, "low": 0, "medium": 0, "high": 0},
    }


def aggregate_domains(events: list) -> list:
    agg: dict = {}

    def get_or_create(domain: str) -> DomainAggregate:
        row = agg.get(domain)
        if row is None:
            row = DomainAggregate(domain=domain)
            agg[domain] = row
        return row

    for ev in events:
        if not ev.domain:
            continue
        row = get_or_create(ev.domain)
        row.total += 1
        if ev.kind == EventKind.VISIT:
            row.visits += 1
        elif ev.kind == EventKind.DOWNLOAD:
            row.downloads += 1
        else:
            row.bookmarks += 1
        src = f"{ev.browser}/{ev.profile}"
        if src not in row.sources:
            row.sources.append(src)
        if ev.timestamp is not None:
            if row.first_seen is None or ev.timestamp < row.first_seen:
                row.first_seen = ev.timestamp
            if row.last_seen is None or ev.timestamp > row.last_seen:
                row.last_seen = ev.timestamp

    return sorted(agg.values(), key=lambda r: (-r.total, r.domain))


def utcnow() -> datetime:
    return datetime.now(timezone.utc)