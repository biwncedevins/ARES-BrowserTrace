from __future__ import annotations

import json
import os
from typing import Iterable

from ..core.domains import extract_domain
from ..core.format import filename_from_path, human_size
from ..core.timeforge import TimeForge
from ..models import Event, EventKind
from .reader import query_rows, table_columns, available_tables

TRANSITIONS = {
    0: "LINK",
    1: "TYPED",
    2: "AUTO_BOOKMARK",
    3: "AUTO_SUBFRAME",
    4: "MANUAL_SUBFRAME",
    5: "GENERATED",
    6: "AUTO_TOPLEVEL",
    7: "FORM_SUBMIT",
    8: "RELOAD",
    9: "KEYWORD",
    10: "KEYWORD_GENERATED",
    11: "OVERWRITE",
}

DOWNLOAD_STATES = {
    0: "IN_PROGRESS",
    1: "COMPLETE",
    2: "CANCELLED",
    3: "INTERRUPTED",
}

DANGER_TYPES = {
    0: "NOT_DANGEROUS",
    1: "DANGEROUS_FILE",
    2: "DANGEROUS_URL",
    3: "DANGEROUS_CONTENT",
    4: "MAYBE_DANGEROUS_CONTENT",
    5: "UNCOMMON_CONTENT",
    6: "USER_VALIDATED",
    7: "DANGEROUS_HOST",
    8: "POTENTIALLY_UNWANTED",
    11: "ALLOWLISTED_BY_POLICY",
    12: "ASYNC_SCANNING",
    13: "BLOCKED_PASSWORD_PROTECTED",
    14: "BLOCKED_TOO_LARGE",
    15: "SENSITIVE_CONTENT_WARNING",
    16: "SCAN_FAILED",
    17: "DEEP_SCANNED_SAFE",
    18: "PROMPT_FOR_SCANNING",
    19: "BLOCKED_UNSUPPORTED_FILETYPE",
    20: "DANGEROUS_ACCOUNT_COMPROMISE",
}


def parse_history(db_path: str, browser: str, profile: str, copy_dir: str = "") -> list:
    tables = available_tables(db_path)
    events = []
    if "visits" in tables and "urls" in tables:
        sql = (
            "SELECT u.id AS url_id, u.url, u.title, u.visit_count, u.last_visit_time, "
            "v.id AS visit_id, v.visit_time, v.transition, v.from_visit "
            "FROM visits v JOIN urls u ON v.url = u.id"
        )
        rows = query_rows(db_path, sql)
        for row in rows:
            ts = TimeForge.normalize(row.get("visit_time"), "chrome")
            if ts is None:
                ts = TimeForge.normalize(row.get("last_visit_time"), "chrome")
            url = row.get("url") or ""
            transition = TRANSITIONS.get(int(row.get("transition") or 0), str(row.get("transition")))
            events.append(
                Event(
                    id=f"visit-{row.get('visit_id')}",
                    kind=EventKind.VISIT,
                    browser=browser,
                    profile=profile,
                    timestamp=ts,
                    url=url,
                    domain=extract_domain(url),
                    title=row.get("title") or "",
                    detail=f"{transition} · {row.get('visit_count', 0)} visits",
                    visit_count=int(row.get("visit_count") or 0),
                    transition=transition,
                    from_visit=str(row.get("from_visit") or ""),
                    raw={"url_id": row.get("url_id"), "visit_id": row.get("visit_id")},
                )
            )
        if not rows:
            events = []
    if not events and "urls" in tables:
        sql = "SELECT id, url, title, visit_count, last_visit_time FROM urls"
        for row in query_rows(db_path, sql):
            ts = TimeForge.normalize(row.get("last_visit_time"), "chrome")
            url = row.get("url") or ""
            events.append(
                Event(
                    id=f"url-{row.get('id')}",
                    kind=EventKind.VISIT,
                    browser=browser,
                    profile=profile,
                    timestamp=ts,
                    url=url,
                    domain=extract_domain(url),
                    title=row.get("title") or "",
                    detail=f"last visit · {row.get('visit_count', 0)} visits",
                    visit_count=int(row.get("visit_count") or 0),
                    raw={"url_id": row.get("id")},
                )
            )
    return events


def parse_downloads(db_path: str, browser: str, profile: str, copy_dir: str = "") -> list:
    tables = available_tables(db_path)
    if "downloads" not in tables:
        return []
    cols = table_columns(db_path, "downloads")
    select = ["id", "guid", "current_path", "target_path", "start_time", "end_time",
              "received_bytes", "total_bytes", "state", "danger_type", "interrupt_reason",
              "mime_type", "referrer", "opened", "last_modified"]
    select = [c for c in select if c in cols]
    sql = f"SELECT {', '.join(select)} FROM downloads"
    url_map = {}
    if "downloads_url_chains" in tables:
        chain_cols = table_columns(db_path, "downloads_url_chains")
        if "guid" in chain_cols:
            key_col = "guid"
        elif "download_id" in chain_cols:
            key_col = "download_id"
        else:
            key_col = ""
        if key_col:
            for row in query_rows(
                db_path,
                f"SELECT {key_col}, chain_index, url FROM downloads_url_chains ORDER BY chain_index",
            ):
                url_map.setdefault(str(row.get(key_col) or ""), []).append(row.get("url") or "")

    events = []
    for row in query_rows(db_path, sql):
        ts = TimeForge.normalize(row.get("start_time"), "chrome")
        if ts is None:
            ts = TimeForge.normalize(row.get("end_time"), "chrome")
        target = row.get("target_path") or row.get("current_path") or ""
        file_name = filename_from_path(target)
        key = str(row.get("guid") or "") or str(row.get("id"))
        urls = url_map.get(key, [])
        url = urls[0] if urls else row.get("referrer") or ""
        referrer = urls[1] if len(urls) > 1 else row.get("referrer") or ""
        total = int(row.get("total_bytes") or 0)
        received = int(row.get("received_bytes") or 0)
        state = DOWNLOAD_STATES.get(int(row.get("state") or 0), str(row.get("state")))
        danger = DANGER_TYPES.get(int(row.get("danger_type") or 0), str(row.get("danger_type")))
        size_str = human_size(total) if total else ("partial " + human_size(received) if received else "")
        events.append(
            Event(
                id=f"download-{row.get('id')}",
                kind=EventKind.DOWNLOAD,
                browser=browser,
                profile=profile,
                timestamp=ts,
                url=url,
                domain=extract_domain(url),
                title="",
                detail=f"{state} · {size_str}".strip(" ·"),
                file_name=file_name,
                target_path=target,
                mime_type=row.get("mime_type") or "",
                total_bytes=total,
                received_bytes=received,
                state=state,
                danger_type=danger,
                referrer=referrer,
                raw={"guid": row.get("guid"), "interrupt_reason": (row.get("interrupt_reason") or "")},
            )
        )
    return events


def parse_bookmarks_file(bookmarks_path: str, browser: str, profile: str) -> list:
    if not bookmarks_path or not os.path.isfile(bookmarks_path):
        return []
    try:
        with open(bookmarks_path, "r", encoding="utf-8", errors="replace") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return []

    events = []

    def walk(folder, folder_path: str):
        children = folder.get("children") or []
        for node in children:
            node_type = node.get("type")
            name = node.get("name") or ""
            if node_type == "url":
                ts = TimeForge.normalize(node.get("date_added"), "chrome")
                ts_modified = TimeForge.normalize(node.get("date_last_used"), "chrome") or ts
                url = node.get("url") or ""
                events.append(
                    Event(
                        id=f"bookmark-{node.get('id')}",
                        kind=EventKind.BOOKMARK,
                        browser=browser,
                        profile=profile,
                        timestamp=ts,
                        url=url,
                        domain=extract_domain(url),
                        title=name,
                        detail=folder_path or "root",
                        folder_path=folder_path,
                        modified_time=ts_modified,
                        raw={"guid": node.get("guid")},
                    )
                )
            elif node_type == "folder" and children:
                sub = f"{folder_path}/{name}" if folder_path else name
                walk(node, sub)

    roots = data.get("roots") or {}
    for key in ("bookmark_bar", "other", "synced", "mobile"):
        root = roots.get(key)
        if root and isinstance(root, dict):
            walk(root, "")

    return events


def parse_all(db_path: str, bookmarks_file: str, browser: str, profile: str,
              load_history: bool = True, load_downloads: bool = True,
              load_bookmarks: bool = True) -> list:
    from ..core.stats import utcnow

    events: list = []
    if load_history and db_path:
        events.extend(parse_history(db_path, browser, profile))
    if load_downloads and db_path:
        events.extend(parse_downloads(db_path, browser, profile))
    if load_bookmarks:
        events.extend(parse_bookmarks_file(bookmarks_file, browser, profile))
    return events