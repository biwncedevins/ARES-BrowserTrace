from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Dict

from ..core.domains import extract_domain
from ..core.format import filename_from_path, human_size
from ..core.timeforge import TimeForge
from ..models import Event, EventKind
from .reader import query_rows, table_columns, available_tables

FIREFOX_DOWNLOAD_STATES = {
    0: "NOT_STARTED",
    1: "DOWNLOADING",
    2: "COMPLETE",
    3: "FAILED",
    4: "CANCELLED",
    5: "PAUSED",
    6: "BLOCKED",
    7: "SCANNING",
    8: "DIRTY",
}

ROOT_NAMES = {1: "root", 2: "Bookmarks Menu", 3: "Bookmarks Toolbar", 4: "Other Bookmarks", 5: "Mobile Bookmarks"}
MENU_ROOT = 2
TOOLBAR_ROOT = 3
OTHER_ROOT = 4
MOBILE_ROOT = 5


def parse_history(db_path: str, profile: str, copy_dir: str = "") -> list:
    tables = available_tables(db_path)
    events = []
    if {"moz_places", "moz_historyvisits"}.issubset(tables):
        sql = (
            "SELECT p.id AS place_id, p.url, p.title, p.visit_count, p.last_visit_date, "
            "v.id AS visit_id, v.visit_date, v.from_visit "
            "FROM moz_historyvisits v JOIN moz_places p ON v.place_id = p.id"
        )
        rows = query_rows(db_path, sql)
        for row in rows:
            ts = TimeForge.normalize(row.get("visit_date"), "prtime")
            if ts is None:
                ts = TimeForge.normalize(row.get("last_visit_date"), "prtime")
            url = row.get("url") or ""
            events.append(
                Event(
                    id=f"visit-{row.get('visit_id')}",
                    kind=EventKind.VISIT,
                    browser="firefox",
                    profile=profile,
                    timestamp=ts,
                    url=url,
                    domain=extract_domain(url),
                    title=row.get("title") or "",
                    detail=f"{row.get('visit_count', 0)} visits",
                    visit_count=int(row.get("visit_count") or 0),
                    from_visit=str(row.get("from_visit") or ""),
                    raw={"place_id": row.get("place_id"), "visit_id": row.get("visit_id")},
                )
            )
    return events


def parse_downloads(db_path: str, profile: str, copy_dir: str = "") -> list:
    tables = available_tables(db_path)
    if "moz_annos" not in tables or "moz_anno_attributes" not in tables:
        return []
    dest_sql = (
        "SELECT a.place_id, a.id AS anno_id, a.dateAdded, a.content AS dest_uri, p.url, p.title "
        "FROM moz_annos a "
        "JOIN moz_places p ON a.place_id = p.id "
        "WHERE a.anno_attribute_id = (SELECT id FROM moz_anno_attributes WHERE name = 'downloads/destinationFileURI')"
    )
    meta_sql = (
        "SELECT a.place_id, a.content AS meta "
        "FROM moz_annos a "
        "WHERE a.anno_attribute_id = (SELECT id FROM moz_anno_attributes WHERE name = 'downloads/metaData')"
    )
    try:
        dest_rows = query_rows(db_path, dest_sql)
        meta_rows = query_rows(db_path, meta_sql)
    except Exception:
        return []
    meta_by_place = {}
    for row in meta_rows:
        try:
            meta_by_place[row["place_id"]] = json.loads(row.get("meta") or "{}")
        except (ValueError, TypeError):
            meta_by_place[row["place_id"]] = {}

    events = []
    seen_batches = set()
    index = 0
    for row in dest_rows:
        place_id = row.get("place_id")
        meta = meta_by_place.get(place_id, {}) if place_id else {}
        state = FIREFOX_DOWNLOAD_STATES.get(int(meta.get("state") or 0), str(meta.get("state")))
        end_time = meta.get("endTime")
        ts = TimeForge.normalize(end_time, "prtime")
        if ts is None:
            ts = TimeForge.normalize(row.get("dateAdded"), "prtime")
        file_size = meta.get("fileSize")
        total = int(meta.get("totalBytes") or file_size or 0)
        received = int(meta.get("fileSize") or 0) if state not in ("COMPLETE",) else total
        source = meta.get("source") or row.get("url") or ""
        dest_uri = row.get("dest_uri") or ""
        target_path = _file_uri_to_path(dest_uri)
        if not target_path:
            target_path = meta.get("filePath") or meta.get("path") or dest_uri
        file_name = filename_from_path(target_path)
        size_str = human_size(total) if total else (human_size(received) if received else "")
        index += 1
        events.append(
            Event(
                id=f"download-{place_id or index}",
                kind=EventKind.DOWNLOAD,
                browser="firefox",
                profile=profile,
                timestamp=ts,
                url=source,
                domain=extract_domain(source),
                title="",
                detail=f"{state} · {size_str}".strip(" ·"),
                file_name=file_name,
                target_path=target_path.replace("/", "\\") if target_path else "",
                total_bytes=total,
                received_bytes=received,
                state=state,
                raw={"place_id": place_id, "anno_id": row.get("anno_id")},
            )
        )
    return events


def _file_uri_to_path(uri: str) -> str:
    if not uri:
        return ""
    try:
        parsed = urllib.parse.urlsplit(uri)
        if parsed.scheme != "file":
            return uri
        return urllib.request.url2pathname(urllib.parse.unquote(parsed.path))
    except Exception:
        return uri


def parse_bookmarks(db_path: str, profile: str, copy_dir: str = "") -> list:
    tables = available_tables(db_path)
    if "moz_bookmarks" not in tables or "moz_places" not in tables:
        return []
    cols = table_columns(db_path, "moz_bookmarks")
    rows = query_rows(db_path, "SELECT id, type, parent, title, fk, dateAdded, lastModified FROM moz_bookmarks")
    parent_map: Dict[int, tuple] = {}
    for row in rows:
        parent_map[int(row["id"])] = (int(row["type"] or 0), str(row.get("title") or ""), int(row.get("parent") or 0))

    place_id_to_event_id = {}
    place_sql = "SELECT id, url, title FROM moz_places WHERE id IN ({})"
    fks = [int(r.get("fk") or 0) for r in rows if r.get("fk")]
    place_map = {}
    for chunk in _chunks(fks, 500):
        if not chunk:
            continue
        place_sql = (
            "SELECT id, url, title FROM moz_places WHERE id IN ({0})".format(",".join("?" * len(chunk)))
        )
        for pr in query_rows(db_path, place_sql, tuple(chunk)):
            place_map[int(pr["id"])] = pr

    events = []
    for row in rows:
        node_type = int(row.get("type") or 0)
        if node_type != 1:
            continue
        fk = int(row.get("fk") or 0)
        place = place_map.get(fk)
        if not place:
            continue
        url = place.get("url") or ""
        ts = TimeForge.normalize(row.get("dateAdded"), "prtime")
        modified = TimeForge.normalize(row.get("lastModified"), "prtime") or ts
        title = row.get("title") or place.get("title") or ""
        folder_path = _folder_path(int(row["id"]), parent_map)
        events.append(
            Event(
                id=f"bookmark-{row.get('id')}",
                kind=EventKind.BOOKMARK,
                browser="firefox",
                profile=profile,
                timestamp=ts,
                url=url,
                domain=extract_domain(url),
                title=title,
                detail=folder_path or "root",
                folder_path=folder_path,
                modified_time=modified,
                raw={"place_id": fk, "bookmark_id": row.get("id")},
            )
        )
    return events


def _chunks(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def _folder_path(node_id: int, parent_map: Dict[int, tuple]) -> str:
    parts = []
    seen = set()
    current = node_id
    while current and current not in seen:
        seen.add(current)
        info = parent_map.get(current)
        if not info:
            break
        ntype, title, parent = info
        current = parent
        if ntype == 2 and title:
            parts.append(title)
        elif current == 0 or current == 1:
            if ntype == 2 and title:
                parts.append(title)
            break
    root_title = "root"
    if current in parent_map:
        info = parent_map[current]
        if info and info[1]:
            root_title = info[1]
    parts = [p for p in parts if p and p != root_title]
    return "/".join(reversed(parts))


def parse_all(db_path: str, profile: str, load_history: bool = True,
              load_downloads: bool = True, load_bookmarks: bool = True) -> list:
    events = []
    if load_history:
        events.extend(parse_history(db_path, profile))
    if load_downloads:
        events.extend(parse_downloads(db_path, profile))
    if load_bookmarks:
        events.extend(parse_bookmarks(db_path, profile))
    return events