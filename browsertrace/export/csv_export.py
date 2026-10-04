from __future__ import annotations

import csv
import os
from datetime import datetime, timezone

from ..core.timeforge import TimeForge
from ..models import EventKind

TIMELINE_COLUMNS = [
    "time_utc", "time_unix", "type", "browser", "profile", "domain", "title",
    "url", "file_name", "target_path", "state", "size_bytes", "transition",
    "visit_count", "folder", "referrer", "flags",
]

FINDINGS_COLUMNS = ["severity", "category", "title", "detail", "domain", "count", "first_time_utc"]

DOMAINS_COLUMNS = ["domain", "events", "visits", "downloads", "bookmarks",
                   "first_seen_utc", "last_seen_utc", "days_span", "sources"]


def _utc(dt) -> str:
    if dt is None:
        return ""
    return TimeForge.iso_utc(dt)


def _row_for(event) -> dict:
    from_ts = event.raw.get("start_time") if event.kind == EventKind.DOWNLOAD else (
        event.raw.get("visit_time") if event.kind == EventKind.VISIT else event.raw.get("date_added"))
    flags = ", ".join(event.flags) if event.flags else ""
    return {
        "time_utc": _utc(event.timestamp),
        "time_unix": str(int(event.timestamp.timestamp())) if event.timestamp else "",
        "type": event.kind.value.upper(),
        "browser": event.browser,
        "profile": event.profile,
        "domain": event.domain,
        "title": event.title,
        "url": event.url,
        "file_name": event.file_name,
        "target_path": event.target_path,
        "state": event.state,
        "size_bytes": event.total_bytes or "",
        "transition": event.transition,
        "visit_count": event.visit_count or "",
        "folder": event.folder_path,
        "referrer": event.referrer,
        "flags": flags,
    }


def export_csv_report(session, out_dir: str, scope: dict) -> list:
    os.makedirs(out_dir, exist_ok=True)
    written = []
    if scope.get("timeline", True):
        path = os.path.join(out_dir, "browsertrace_timeline.csv")
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.DictWriter(fh, fieldnames=TIMELINE_COLUMNS)
            writer.writeheader()
            for ev in session.events:
                writer.writerow(_row_for(ev))
        written.append(path)
    if scope.get("history", False):
        path = os.path.join(out_dir, "browsertrace_history.csv")
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.DictWriter(fh, fieldnames=TIMELINE_COLUMNS)
            writer.writeheader()
            for ev in session.events:
                if ev.kind == EventKind.VISIT:
                    writer.writerow(_row_for(ev))
        written.append(path)
    if scope.get("downloads", False):
        path = os.path.join(out_dir, "browsertrace_downloads.csv")
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.DictWriter(fh, fieldnames=TIMELINE_COLUMNS)
            writer.writeheader()
            for ev in session.events:
                if ev.kind == EventKind.DOWNLOAD:
                    writer.writerow(_row_for(ev))
        written.append(path)
    if scope.get("bookmarks", False):
        path = os.path.join(out_dir, "browsertrace_bookmarks.csv")
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.DictWriter(fh, fieldnames=TIMELINE_COLUMNS)
            writer.writeheader()
            for ev in session.events:
                if ev.kind == EventKind.BOOKMARK:
                    writer.writerow(_row_for(ev))
        written.append(path)
    if scope.get("findings", True):
        path = os.path.join(out_dir, "browsertrace_findings.csv")
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.DictWriter(fh, fieldnames=FINDINGS_COLUMNS)
            writer.writeheader()
            for f in session.findings:
                writer.writerow({
                    "severity": f.severity.value.upper(),
                    "category": f.category,
                    "title": f.title,
                    "detail": f.detail,
                    "domain": f.domain,
                    "count": f.count,
                    "first_time_utc": _utc(f.timestamps[0]) if f.timestamps else "",
                })
        written.append(path)
    if scope.get("domains", False):
        path = os.path.join(out_dir, "browsertrace_domains.csv")
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.DictWriter(fh, fieldnames=DOMAINS_COLUMNS)
            writer.writeheader()
            for row in session.domains:
                writer.writerow({
                    "domain": row.domain,
                    "events": row.total,
                    "visits": row.visits,
                    "downloads": row.downloads,
                    "bookmarks": row.bookmarks,
                    "first_seen_utc": _utc(row.first_seen),
                    "last_seen_utc": _utc(row.last_seen),
                    "days_span": f"{row.days_span:.1f}" if row.days_span else "",
                    "sources": "; ".join(row.sources),
                })
        written.append(path)
    return written