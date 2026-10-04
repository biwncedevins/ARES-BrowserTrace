from __future__ import annotations

import os
import sqlite3
import time
from datetime import datetime
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from ..core.stats import aggregate_domains, compute_stats
from ..heuristics import analyze
from ..models import Finding, SourceProfile
from . import chromium, firefox
from .reader import available_tables, clear_snapshot, create_snapshot


@dataclass
class SourceSpec:
    browser: str
    label: str = ""
    history_file: str = ""
    bookmarks_file: str = ""
    origin: str = "manual"
    notes: list = field(default_factory=list)
    profile: Optional[SourceProfile] = None
    variant: str = ""

    @property
    def is_firefox(self) -> bool:
        return self.browser == "firefox"

    @property
    def db_file(self) -> str:
        if self.is_firefox:
            return self.bookmarks_file or self.history_file
        return self.history_file


@dataclass
class LoadResult:
    source: SourceSpec
    events: list
    findings: list
    warnings: list
    stats: dict
    domains: list
    duration_s: float = 0.0


def classify_file(path: str) -> str:
    """Classify a single artifact file as history / places / bookmarks.

    Returns one of: 'chromium_history', 'firefox_places', 'chromium_bookmarks',
    'firefox_bookmarks', or 'unknown'.
    """
    if not path or not os.path.isfile(path):
        return "unknown"
    name = os.path.basename(path).lower()
    if name == "bookmarks" or name == "bookmarks.bak" or name.endswith("bookmarks.json"):
        return "chromium_bookmarks"
    if "places" in name:
        return "firefox_places"
    if name == "history":
        return "chromium_history"
    if name.endswith(".json"):
        try:
            import json

            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                data = json.load(fh)
            if isinstance(data, dict) and isinstance(data.get("roots"), dict):
                return "chromium_bookmarks"
        except Exception:
            pass
        return "unknown"
    tables = _probe_tables(path)
    if not tables:
        return "unknown"
    if "moz_places" in tables and "moz_bookmarks" in tables:
        return "firefox_places"
    if "urls" in tables or "visits" in tables:
        return "chromium_history"
    return "unknown"


def _probe_tables(path: str) -> set:
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
        try:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            return {str(r[0]) for r in rows}
        finally:
            conn.close()
    except Exception:
        return set()


def resolve_from_folder(folder: str) -> SourceSpec:
    if not folder or not os.path.isdir(folder):
        raise LookupError(f"Folder not found: {folder}")
    files = [os.path.join(folder, n) for n in os.listdir(folder)]
    files = [f for f in files if os.path.isfile(f)]
    spec = _resolve_files(files, origin=folder)
    if spec.browser == "unknown":
        raise LookupError("No recognizable browser artifacts found in the selected folder.")
    return spec


def resolve_from_files(files: List[str], folder: str = "") -> SourceSpec:
    spec = _resolve_files(files, origin=folder or "manual files")
    if spec.browser == "unknown":
        raise LookupError("No recognizable browser artifact files were selected.")
    return spec


def _base_for_folder(folder: str) -> str:
    return os.path.basename(os.path.abspath(folder)).lower()


def _resolve_files(files: List[str], origin: str = "") -> SourceSpec:
    specs = []
    for path in files:
        kind = classify_file(path)
        if kind != "unknown":
            specs.append((kind, path))
    browser = "unknown"
    for kind, _path in specs:
        if kind == "firefox_places":
            browser = "firefox"
            break
    if browser == "unknown" and any(k == "chromium_history" for k, _ in specs):
        browser = "chromium"
    if browser == "unknown" and any(k == "chromium_bookmarks" for k, _ in specs):
        browser = "chromium"
    if browser == "unknown":
        return SourceSpec(browser=browser, label=origin)
    order = {"firefox_places": 0, "chromium_history": 1, "chromium_bookmarks": 2, "firefox_bookmarks": 3}
    specs.sort(key=lambda kv: order.get(kv[0], 9))
    notes = []
    if origin:
        notes.append(origin)
    if browser == "firefox":
        places = next((p for k, p in specs if k == "firefox_places"), "")
        bookmarks = next((p for k, p in specs if k == "firefox_bookmarks"), "")
        if bookmarks and not places:
            browser = "unknown"
        return SourceSpec(
            browser="firefox",
            label=_label(origin, "Firefox"),
            history_file=places,
            bookmarks_file=bookmarks or places,
            origin=origin,
            notes=notes,
        )
    history = next((p for k, p in specs if k == "chromium_history"), "")
    bookmarks = next((p for k, p in specs if k == "chromium_bookmarks"), "")
    return SourceSpec(
        browser="chromium",
        label=_label(origin, "Chrome/Edge"),
        history_file=history,
        bookmarks_file=bookmarks,
        origin=origin,
        notes=notes,
    )


def _label(origin: str, fallback: str) -> str:
    if not origin:
        return fallback
    base = os.path.basename(os.path.abspath(origin))
    if base in (".", ""):
        return fallback
    return f"{fallback} — {base}"


def _guess_variant(origin) -> str:
    text = str(origin or "").lower()
    if "edge" in text or "msedge" in text:
        return "edge"
    return "chrome"


def resolve_from_profile(profile: SourceProfile) -> SourceSpec:
    browser = profile.browser
    if browser == "firefox":
        return SourceSpec(
            browser="firefox",
            label=profile.label,
            history_file=profile.places_file,
            bookmarks_file=profile.places_file,
            origin="profile",
            profile=profile,
        )
    return SourceSpec(
        browser="chromium",
        label=profile.label,
        history_file=profile.history_file,
        bookmarks_file=profile.bookmarks_file or "",
        origin="profile",
        profile=profile,
        variant=profile.browser,
    )


def resolve_source(profile: Optional[SourceProfile] = None,
                   folder: str = "",
                   files: List[str] = None) -> SourceSpec:
    if profile is not None:
        return resolve_from_profile(profile)
    if folder:
        return resolve_from_folder(folder)
    if files:
        return resolve_from_files(files)
    raise LookupError("No source selected.")


def pipeline(spec: SourceSpec, progress: Optional[Callable[[str], None]] = None,
             load_sections=(True, True, True)) -> LoadResult:
    t0 = time.perf_counter()

    def report(msg):
        if progress:
            progress(msg)

    events = []
    warnings = []
    db_path = spec.db_file or spec.history_file
    snapshot = ""
    try:
        if db_path:
            snapshot = create_snapshot(db_path)
            work_db = _snapshot_db(snapshot, db_path)
            report(f"Analyzing {spec.label} …")
            load_history, load_downloads, load_bookmarks = load_sections
            if spec.is_firefox:
                events = firefox.parse_all(work_db, spec.label, load_history, load_downloads, load_bookmarks)
            else:
                bname = spec.variant or _guess_variant(spec.origin)
                events = chromium.parse_all(work_db, spec.bookmarks_file, bname, spec.label,
                                            load_history, load_downloads, load_bookmarks)
        events = _dedupe(events)
        report(f"Parsed {len(events)} events — running heuristics …")
        findings = analyze(events)
        flag_map: dict = {}
        for f in findings:
            for event_id in f.event_ids:
                flag_map.setdefault(event_id, []).append(f.id)
        for ev in events:
            if ev.id in flag_map:
                ev.flags = sorted(flag_map[ev.id])
        stats = compute_stats(events)
        for f in findings:
            key = f.severity.value
            if key in stats["findings"]:
                stats["findings"][key] += 1
        domains = aggregate_domains(events)
        if not db_path and not events:
            warnings.append("No selectable artifact database was loaded.")
        if not events:
            warnings.append("No history, download or bookmark events were extracted from this source.")
    finally:
        if snapshot:
            clear_snapshot(snapshot)
    return LoadResult(
        source=spec,
        events=events,
        findings=findings,
        warnings=warnings,
        stats=stats,
        domains=domains,
        duration_s=time.perf_counter() - t0,
    )


def _snapshot_db(snapshot: str, original: str) -> str:
    return os.path.join(snapshot, os.path.basename(original))


def _dedupe(events: list) -> list:
    seen = set()
    out = []
    for ev in events:
        if ev.id in seen:
            continue
        seen.add(ev.id)
        out.append(ev)
    out.sort(key=lambda e: (e.timestamp or datetime.min, e.id))
    return out