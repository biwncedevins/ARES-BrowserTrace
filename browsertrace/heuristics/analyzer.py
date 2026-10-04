from __future__ import annotations

import os
import re
from collections import defaultdict
from datetime import datetime, timezone

from ..core.domains import extract_domain, is_ip_address, registrable_domain
from ..core.format import human_size
from ..models import Event, EventKind, Finding, Severity
from .common_domains import COMMON_DOMAINS

DANGEROUS_EXTENSIONS = {
    ".exe", ".scr", ".bat", ".cmd", ".com", ".vbs", ".vbe", ".js", ".jse",
    ".wsf", ".wsh", ".ps1", ".psm1", ".msi", ".msp", ".hta", ".cpl", ".pif",
    ".jar", ".reg", ".chm", ".lnk", ".docm", ".xlsm", ".pptm", ".iso",
    ".dmg", ".appimage", ".svg", ".html", ".htm",
}

MACRO_EXTENSIONS = {".docm", ".xlsm", ".pptm", ".doc", ".xls", ".ppt"}

URL_SHORTENERS = {
    "bit.ly", "tinyurl.com", "goo.gl", "t.co", "ow.ly", "is.gd", "buff.ly",
    "rebrand.ly", "cutt.ly", "rb.gy", "shorturl.at", "snip.ly", "bl.ink",
    "tny.im", "v.gd", "zip.co", "lnk.to", "qrco.de", "clicky.me", "gg.gg",
}

FILE_EXT_RE = re.compile(r"^.+\.([A-Za-z0-9]{1,8})\.([A-Za-z0-9]{1,8})$")

FINDING_CATEGORY_SUSPICIOUS_DOWNLOAD = "suspicious-download"
FINDING_CATEGORY_UNCOMMON_DOMAIN = "uncommon-domain"
FINDING_CATEGORY_REPEATED_USAGE = "repeated-usage"
FINDING_CATEGORY_UNUSUAL_PATTERN = "unusual-pattern"

MAX_UNCOMMON_DOMAINS = 60
MAX_REPEATED_URLS = 40


class _Analyzer:
    def __init__(self):
        self.findings = []
        self._fid = 0

    def _add(self, severity, category, title, detail, domain="", timestamp=None,
             event_ids=(), count=1, source=""):
        self._fid += 1
        self.findings.append(
            Finding(
                id=f"F{self._fid}",
                severity=severity,
                category=category,
                title=title,
                detail=detail,
                domain=domain,
                timestamps=[timestamp] if timestamp else [],
                event_ids=list(event_ids),
                source=source,
                count=count,
            )
        )


def analyze(events: list) -> list:
    analyzer = _Analyzer()
    _suspicious_downloads(analyzer, events)
    _uncommon_domains(analyzer, events)
    _repeated_usage(analyzer, events)
    _unusual_patterns(analyzer, events)
    analyzer.findings.sort(key=lambda f: (-f.severity.rank, f.timestamps and str(f.timestamps[0]) or ""))
    return analyzer.findings


def _suspicious_downloads(analyzer: _Analyzer, events: list) -> None:
    downloads = [e for e in events if e.kind == EventKind.DOWNLOAD]
    if not downloads:
        return
    first_seen_by_domain = {}
    for ev in events:
        if ev.timestamp is not None and ev.domain:
            if ev.domain not in first_seen_by_domain or ev.timestamp < first_seen_by_domain[ev.domain]:
                first_seen_by_domain[ev.domain] = ev.timestamp

    for ev in downloads:
        name = ev.file_name or ""
        host = ev.domain
        reasons = []
        severity = Severity.MEDIUM

        base, ext = os.path.splitext(name or ev.url.split("/")[-1])
        ext = ext.lower()
        if ext:
            base2, ext2 = os.path.splitext(base)
            if ext2 and ext2.lower() in {".pdf", ".doc", ".jpg", ".jpeg", ".png", ".gif", ".txt", ".csv", ".xls", ".zip", ".rar", ".mp3", ".mp4", ".zip"}:
                reasons.append(f"double extension: {ext2.lower()}{ext} (disguised payload)")
                severity = Severity.HIGH
        if ext in DANGEROUS_EXTENSIONS:
            reasons.append(f"executable/script extension: {ext}")
        if is_ip_address(host):
            reasons.append(f"downloaded from raw IP host: {host}")
            if severity == Severity.MEDIUM:
                severity = Severity.HIGH
        reg = registrable_domain(host)
        if reg in URL_SHORTENERS:
            reasons.append(f"download from URL shortener: {reg}")
        if host and reg not in COMMON_DOMAINS and first_seen_by_domain.get(host) == ev.timestamp:
            reasons.append("first contact: no earlier activity on this domain in the dataset")
            severity = Severity.HIGH
        if ev.state and ev.state != "COMPLETE" and ev.state not in ("CANCELLED", "INTERRUPTED", "FAILED"):
            pass
        if reasons:
            detail = "; ".join(reasons)
            if ev.state:
                detail += f" — state: {ev.state}"
            if ev.total_bytes:
                detail += f" — size: {human_size(ev.total_bytes)}"
            analyzer._add(
                severity=severity,
                category=FINDING_CATEGORY_SUSPICIOUS_DOWNLOAD,
                title=f"Suspicious download: {os.path.basename(ev.target_path) or ev.file_name or ev.url}",
                detail=detail,
                domain=host,
                timestamp=ev.timestamp,
                event_ids=[ev.id],
                source=f"{ev.browser}/{ev.profile}",
            )


def _uncommon_domains(analyzer: _Analyzer, events: list) -> None:
    by_domain = defaultdict(list)
    for ev in events:
        if ev.domain:
            by_domain[ev.domain].append(ev)
    flagged = 0
    for host, evs in by_domain.items():
        if is_ip_address(host):
            continue
        reg = registrable_domain(host)
        if reg in COMMON_DOMAINS:
            continue
        has_download = any(e.kind == EventKind.DOWNLOAD for e in evs)
        if len(evs) < 2 and not has_download:
            continue
        if flagged >= MAX_UNCOMMON_DOMAINS:
            return
        severity = Severity.LOW if has_download else Severity.INFO
        counts = {
            EventKind.VISIT: sum(1 for e in evs if e.kind == EventKind.VISIT),
            EventKind.DOWNLOAD: sum(1 for e in evs if e.kind == EventKind.DOWNLOAD),
            EventKind.BOOKMARK: sum(1 for e in evs if e.kind == EventKind.BOOKMARK),
        }
        detail = f"{counts[EventKind.VISIT]} visits, {counts[EventKind.DOWNLOAD]} downloads, {counts[EventKind.BOOKMARK]} bookmarks"
        if has_download:
            detail += " — not in known-domain list"
        analyzer._add(
            severity=severity,
            category=FINDING_CATEGORY_UNCOMMON_DOMAIN,
            title=f"Uncommon domain: {host}",
            detail=detail,
            domain=host,
            timestamp=evs[0].timestamp,
            event_ids=[e.id for e in evs][:8],
            count=len(evs),
            source=evs[0].browser + "/" + evs[0].profile,
        )
        flagged += 1


def _repeated_usage(analyzer: _Analyzer, events: list) -> None:
    url_counts = defaultdict(int)
    domain_counts = defaultdict(int)
    for ev in events:
        if ev.kind == EventKind.VISIT and ev.url:
            url_counts[ev.url] = max(url_counts.get(ev.url, 0), int(ev.visit_count or 0))
        if ev.domain:
            domain_counts[ev.domain] += 1
    flagged = 0
    for url, count in sorted(url_counts.items(), key=lambda kv: -kv[1]):
        if count < 25:
            break
        if flagged >= MAX_REPEATED_URLS:
            break
        host = extract_domain(url)
        analyzer._add(
            severity=Severity.INFO,
            category=FINDING_CATEGORY_REPEATED_USAGE,
            title=f"Repeatedly visited: {count}×",
            detail=f"Same URL opened {count} times — {host or url}",
            domain=host,
            timestamp=None,
            event_ids=[],
            count=count,
        )
        flagged += 1
    for host, count in sorted(domain_counts.items(), key=lambda kv: -kv[1]):
        if count >= 1000:
            analyzer._add(
                severity=Severity.LOW,
                category=FINDING_CATEGORY_REPEATED_USAGE,
                title=f"Heavily used domain: {count} events",
                detail=f"{host} accounts for {count} recorded events.",
                domain=host,
                timestamp=None,
                count=count,
            )


def _unusual_patterns(analyzer: _Analyzer, events: list) -> None:
    dated = [e for e in events if e.timestamp is not None]
    if not dated:
        return
    dated_sorted = sorted(dated, key=lambda e: e.timestamp)

    off_hour_events = 0
    for ev in dated:
        local = ev.timestamp.astimezone()
        if local.hour >= 23 or local.hour < 5:
            off_hour_events += 1
    if off_hour_events >= 6:
        analyzer._add(
            severity=Severity.MEDIUM,
            category=FINDING_CATEGORY_UNUSUAL_PATTERN,
            title=f"Off-hours activity: {off_hour_events} events",
            detail="Events recorded between 00:00 and 05:00 local time are often associated with automated or covert activity.",
            timestamp=dated_sorted[0].timestamp,
            count=off_hour_events,
        )

    for i, ev in enumerate(dated_sorted):
        if i and (dated_sorted[i].timestamp - dated_sorted[i - 1].timestamp).total_seconds() <= 60:
            continue
        count = 1
        j = i
        while j + 1 < len(dated_sorted) and (dated_sorted[j + 1].timestamp - ev.timestamp).total_seconds() <= 60:
            count += 1
            j += 1
        if count >= 12:
            window = dated_sorted[i].timestamp
            analyzer._add(
                severity=Severity.MEDIUM,
                category=FINDING_CATEGORY_UNUSUAL_PATTERN,
                title=f"Activity burst: {count} events within 1 minute",
                detail=f"{count} recorded events in a 60-second window beginning at "
                       f"{window.strftime('%Y-%m-%d %H:%M:%S')} UTC — consistent with automation or rapid fire browsing.",
                event_ids=[e.id for e in dated_sorted[i:j + 1]][:20],
                timestamp=window,
                count=count,
            )

    download_times = [e.timestamp for e in dated if e.kind == EventKind.DOWNLOAD]
    if len(download_times) >= 3:
        st = sorted(download_times)
        start = st[0]
        end = st[-1]
        if (end - start).total_seconds() <= 300:
            analyzer._add(
                severity=Severity.MEDIUM,
                category=FINDING_CATEGORY_UNUSUAL_PATTERN,
                title=f"Rapid successive downloads: {len(st)} within 5 minutes",
                detail="Multiple downloads completed in quick succession — often a sign of bulk harvesting.",
                timestamp=start,
                count=len(st),
            )

    spans = {}
    for ev in dated:
        spans.setdefault(ev.domain, []).append(ev.timestamp)
    for host, times in spans.items():
        if len(times) >= 2:
            lo = min(times)
            hi = max(times)
            days = (hi - lo).total_seconds() / 86400.0
            if days > 365:
                analyzer._add(
                    severity=Severity.INFO,
                    category=FINDING_CATEGORY_UNUSUAL_PATTERN,
                    title=f"Long-running activity: {host}",
                    detail=f"Activity on this domain spans {int(days)} days.",
                    domain=host,
                    count=len(times),
                )
                break