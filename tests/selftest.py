"""Synthetic-data self test for the BrowserTrace parsing pipeline.

Creates fake Chromium and Firefox artifact databases in a temp folder, runs the
whole analysis pipeline (parse -> normalize -> group -> flag), and verifies
expected values plus CSV/HTML export. No real user data is touched.

Usage:
    python tests/selftest.py
"""

from __future__ import annotations

import json
import os as _os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta, timezone

ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from browsertrace.core.stats import aggregate_domains, compute_stats
from browsertrace.core.timeforge import TimeForge
from browsertrace.export import export_csv_report, export_html_report
from browsertrace.heuristics import analyze
from browsertrace.models import Session
from browsertrace.parsing import pipeline, resolve_source

BASE = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)


def epoch1601_sec(value: datetime) -> int:
    return TimeForge.to_epoch1601_us(value)


def chrome_history_db(path: str) -> None:
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE urls (id INTEGER PRIMARY KEY, url LONGVARCHAR, title LONGVARCHAR,
            visit_count INTEGER DEFAULT 0 NOT NULL, typed_count INTEGER DEFAULT 0 NOT NULL,
            last_visit_time INTEGER NOT NULL, hidden INTEGER DEFAULT 0 NOT NULL);
        CREATE TABLE visits (id INTEGER PRIMARY KEY, url INTEGER NOT NULL,
            visit_time INTEGER NOT NULL, from_visit INTEGER, transition INTEGER DEFAULT 0 NOT NULL,
            segment_id INTEGER, visit_duration INTEGER DEFAULT 0, incremental_snapshot_columns,
            opener_visit INTEGER);
        CREATE TABLE downloads (id INTEGER PRIMARY KEY, guid VARCHAR NOT NULL,
            current_path LONGVARCHAR NOT NULL, target_path LONGVARCHAR NOT NULL,
            start_time INTEGER NOT NULL, received_bytes INTEGER NOT NULL, total_bytes INTEGER NOT NULL,
            state INTEGER NOT NULL, danger_type INTEGER NOT NULL, interrupt_reason INTEGER NOT NULL,
            hash BLOB, end_time INTEGER NOT NULL, opened INTEGER, last_access_time INTEGER,
            transient INTEGER, referrer VARCHAR, site_url VARCHAR, tab_url VARCHAR,
            tab_referrer_url VARCHAR, http_method VARCHAR, by_ext_id VARCHAR, by_ext_name VARCHAR,
            etag VARCHAR, last_modified VARCHAR, mime_type VARCHAR, original_mime_type VARCHAR);
        CREATE TABLE downloads_url_chains (id INTEGER PRIMARY KEY AUTOINCREMENT,
            chain_index INTEGER, url LONGVARCHAR, tab_url LONGVARCHAR, referrer_url LONGVARCHAR,
            guid VARCHAR NOT NULL);
        CREATE INDEX visits_url_index ON visits (url);
        CREATE INDEX visits_from_index ON visits (from_visit);
        CREATE INDEX visits_time_index ON visits (visit_time);
        """
    )
    urls = [
        (1, "https://www.example.com/dashboard", "Example Dashboard", 12, epoch1601_sec(BASE)),
        (2, "https://docs.python.org/3/index.html", "Python 3 Index", 31, epoch1601_sec(BASE + timedelta(hours=2))),
        (3, "https://example.invalid/downloads/tool.pdf.exe", "tool", 2, epoch1601_sec(BASE + timedelta(hours=3))),
        (4, "http://192.168.0.50:8080/admin", "Internal admin", 5, epoch1601_sec(BASE + timedelta(days=1))),
    ]
    cur.executemany("INSERT INTO urls (id,url,title,visit_count,last_visit_time) VALUES (?,?,?,?,?)", urls)
    visits = [
        (1, 1, epoch1601_sec(BASE), 0, 6),
        (2, 2, epoch1601_sec(BASE + timedelta(hours=2)), 0, 1),
        (3, 1, epoch1601_sec(BASE + timedelta(hours=2, minutes=30)), 1, 0),
        (4, 3, epoch1601_sec(BASE + timedelta(hours=3)), 0, 7),
        (5, 4, epoch1601_sec(BASE + timedelta(days=1)), 0, 1),
    ]
    cur.executemany("INSERT INTO visits (id,url,visit_time,from_visit,transition) VALUES (?,?,?,?,?)", visits)
    downloads = [
        (1, "gdl1", "C:\\Users\\tester\\Downloads\\tool.pdf.exe", "C:\\Users\\tester\\Downloads\\tool.pdf.exe",
         epoch1601_sec(BASE + timedelta(hours=3, minutes=1)), 44440, 44440, 1, 0, 0,
         b"", epoch1601_sec(BASE + timedelta(hours=3, minutes=2)), 0, 0, 0,
         "https://example.invalid/", "https://example.invalid/downloads/tool.pdf.exe",
         "", "", "GET", "", "", "", "", "application/octet-stream", "application/octet-stream"),
        (2, "gdl2", "C:\\Users\\tester\\Downloads\\setup.msi", "C:\\Users\\tester\\Downloads\\setup.msi",
         epoch1601_sec(BASE + timedelta(hours=5)), 2097152, 2097152, 1, 0, 0,
         b"", epoch1601_sec(BASE + timedelta(hours=5, minutes=4)), 0, 0, 0,
         "https://www.example.com/install", "https://www.example.com/install",
         "", "", "GET", "", "", "", "", "application/x-msi", "application/x-msi"),
    ]
    cur.executemany(
        "INSERT INTO downloads (id,guid,current_path,target_path,start_time,received_bytes,total_bytes,"
        "state,danger_type,interrupt_reason,hash,end_time,opened,last_access_time,transient,referrer,"
        "site_url,tab_url,tab_referrer_url,http_method,by_ext_id,by_ext_name,etag,last_modified,"
        "mime_type,original_mime_type) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        downloads,
    )
    cur.execute(
        "INSERT INTO downloads_url_chains (chain_index,url,tab_url,referrer_url,guid) VALUES (?,?,?,?,?)",
        (0, "https://example.invalid/downloads/tool.pdf.exe", "", "https://www.example.com/page", "gdl1"),
    )
    cur.execute(
        "INSERT INTO downloads_url_chains (chain_index,url,tab_url,referrer_url,guid) VALUES (?,?,?,?,?)",
        (0, "https://www.example.com/install", "", "https://www.example.com/dashboard", "gdl2"),
    )
    conn.commit()
    conn.close()


def chrome_bookmarks(path: str) -> None:
    data = {
        "checksum": "",
        "roots": {
            "bookmark_bar": {
                "type": "folder", "name": "Bookmarks bar",
                "children": [
                    {"type": "url", "name": "Python Docs", "url": "https://docs.python.org/3/",
                     "date_added": epoch1601_sec(BASE), "id": "1", "guid": "b1"},
                    {"type": "url", "name": "Example", "url": "https://www.example.com/dashboard",
                     "date_added": epoch1601_sec(BASE + timedelta(days=2)), "id": "2", "guid": "b2"},
                    {"type": "folder", "name": "Work",
                     "children": [
                         {"type": "url", "name": "Internal", "url": "http://192.168.0.50:8080/admin",
                          "date_added": epoch1601_sec(BASE + timedelta(days=3)), "id": "3", "guid": "b3"},
                     ], "date_added": 0, "id": "4", "guid": "f1"},
                ],
                "date_added": 0, "id": "5", "guid": "root1",
            },
            "other": {"type": "folder", "name": "Other bookmarks", "children": [],
                      "date_added": 0, "id": "6", "guid": "root2"},
            "synced": {"type": "folder", "name": "Mobile bookmarks", "children": [],
                       "date_added": 0, "id": "7", "guid": "root3"},
        },
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)


def firefox_places_db(path: str) -> None:
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE moz_places (id INTEGER PRIMARY KEY, url LONGVARCHAR,
            title LONGVARCHAR, rev_host LONGVARCHAR, visit_count INTEGER DEFAULT 0,
            hidden INTEGER DEFAULT 0, typed INTEGER DEFAULT 0, frecency INTEGER DEFAULT -1,
            last_visit_date INTEGER, guid TEXT);
        CREATE TABLE moz_historyvisits (id INTEGER PRIMARY KEY, from_visit INTEGER,
            place_id INTEGER, visit_date INTEGER, visit_type INTEGER, session INTEGER);
        CREATE TABLE moz_bookmarks (id INTEGER PRIMARY KEY, type INTEGER, fk INTEGER,
            parent INTEGER, position INTEGER, title LONGVARCHAR, keyword_id INTEGER,
            folder_type TEXT, dateAdded INTEGER, lastModified INTEGER, guid TEXT);
        CREATE TABLE moz_annos (id INTEGER PRIMARY KEY, place_id INTEGER NOT NULL,
            anno_attribute_id INTEGER, content LONGVARCHAR, flags INTEGER DEFAULT 0,
            expiration INTEGER DEFAULT 0, type INTEGER DEFAULT 0, dateAdded INTEGER,
            lastModified INTEGER);
        CREATE TABLE moz_anno_attributes (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT);
        CREATE TABLE moz_inputhistory (place_id INTEGER, input LONGVARCHAR, use_count INTEGER);
        CREATE TABLE moz_bookmarks_deleted (guid TEXT);
        """
    )
    cur.execute("INSERT INTO moz_anno_attributes (id,name) VALUES (1,'downloads/destinationFileURI')")
    cur.execute("INSERT INTO moz_anno_attributes (id,name) VALUES (2,'downloads/metaData')")

    places = [
        (1, "https://mozilla.org/en-US/firefox/", "Download Firefox", 44, epoch1601_sec(BASE - timedelta(days=40)), "p1"),
        (2, "https://example.org/research/paper.pdf", "Research Paper", 1, epoch1601_sec(BASE + timedelta(hours=1)), "p2"),
        (3, "https://wiki.example.net/internal", "Internal Wiki", 3, epoch1601_sec(BASE + timedelta(days=4)), "p3"),
    ]
    cur.executemany(
        "INSERT INTO moz_places (id,url,title,visit_count,last_visit_date,guid) VALUES (?,?,?,?,?,?)",
        places,
    )
    visits = [
        (1, 0, 1, epoch1601_sec(BASE - timedelta(days=40)), 1, 0),
        (2, 0, 1, epoch1601_sec(BASE - timedelta(days=1)), 1, 0),
        (3, 0, 2, epoch1601_sec(BASE + timedelta(hours=1)), 1, 0),
        (4, 0, 3, epoch1601_sec(BASE + timedelta(days=4)), 1, 0),
        (5, 1, 3, epoch1601_sec(BASE + timedelta(days=4, hours=1)), 2, 0),
    ]
    cur.executemany(
        "INSERT INTO moz_historyvisits (id,from_visit,place_id,visit_date,visit_type,session) VALUES (?,?,?,?,?,?)",
        visits,
    )
    bookmarks = [
        (1, 2, None, 0, 0, "", None, None, 0, 0, "r1"),
        (2, 2, None, 1, 0, "Bookmarks Menu", None, None, 0, 0, "r2"),
        (3, 2, None, 1, 1, "Bookmarks Toolbar", None, None, 0, 0, "r3"),
        (4, 2, None, 1, 2, "Other Bookmarks", None, None, 0, 0, "r4"),
        (5, 2, None, 1, 3, "Mobile Bookmarks", None, None, 0, 0, "r5"),
        (6, 1, 2, 3, 0, "Firefox homepage", None, None,
         epoch1601_sec(BASE - timedelta(days=30)), epoch1601_sec(BASE - timedelta(days=30)), "b1"),
        (7, 1, 3, 2, 0, "Research", None, None,
         epoch1601_sec(BASE + timedelta(hours=1)), epoch1601_sec(BASE + timedelta(hours=1)), "b2"),
    ]
    cur.executemany(
        "INSERT INTO moz_bookmarks (id,type,fk,parent,position,title,keyword_id,folder_type,"
        "dateAdded,lastModified,guid) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        bookmarks,
    )
    annos = [
        (1, 2, 1, "file:///C:/Users/tester/Downloads/research-paper.pdf", 0, 0, 0,
         epoch1601_sec(BASE + timedelta(hours=1, minutes=2)), epoch1601_sec(BASE + timedelta(hours=1, minutes=2))),
        (2, 2, 2, json.dumps({"state": 2, "source": "https://example.org/research/", "fileSize": 98887,
                              "totalBytes": 98887, "endTime": epoch1601_sec(BASE + timedelta(hours=1, minutes=3))}),
         0, 0, 0, epoch1601_sec(BASE + timedelta(hours=1, minutes=2)), epoch1601_sec(BASE + timedelta(hours=1, minutes=3))),
    ]
    cur.executemany(
        "INSERT INTO moz_annos (id,place_id,anno_attribute_id,content,flags,expiration,type,dateAdded,lastModified) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        annos,
    )
    conn.commit()
    conn.close()


def fail(msg):
    print(f"FAIL: {msg}")
    raise SystemExit(1)


def main() -> int:
    work = tempfile.mkdtemp(prefix="browsertrace_selftest_")
    try:
        chrome_dir = _os.path.join(work, "chrome-profile")
        ff_dir = _os.path.join(work, "ff-profile")
        _os.makedirs(chrome_dir)
        _os.makedirs(ff_dir)
        chrome_history_db(_os.path.join(chrome_dir, "History"))
        chrome_bookmarks(_os.path.join(chrome_dir, "Bookmarks"))
        firefox_places_db(_os.path.join(ff_dir, "places.sqlite"))

        chrome_source = resolve_source(folder=chrome_dir)
        chrome_result = pipeline(chrome_source, progress=lambda m: None)
        ff_source = resolve_source(folder=ff_dir)
        ff_result = pipeline(ff_source, progress=lambda m: None)
        merged_events = [*chrome_result.events, *ff_result.events]
        result = chrome_result
        result.events = merged_events
        result.findings = analyze(merged_events)
        result.domains = aggregate_domains(merged_events)
        result.stats = compute_stats(merged_events)
        assert merged_events, "no events parsed"
        visits = [e for e in result.events if e.kind.value == "visit"]
        downloads = [e for e in result.events if e.kind.value == "download"]
        bookmarks = [e for e in result.events if e.kind.value == "bookmark"]
        print(f"events: {len(result.events)} visits={len(visits)} downloads={len(downloads)} bookmarks={len(bookmarks)}")

        chrome_events = [e for e in result.events if e.browser == "chrome"]
        firefox_events = [e for e in result.events if e.browser == "firefox"]
        if not chrome_events:
            fail("Chrome events not parsed from folder")
        if not firefox_events:
            fail("Firefox events not parsed from folder")

        chrome_download_names = [e.file_name for e in chrome_events if e.kind.value == "download"]
        if "tool.pdf.exe" not in chrome_download_names or "setup.msi" not in chrome_download_names:
            fail(f"chrome download filenames wrong: {chrome_download_names}")

        first = result.findings
        suspicious = [f for f in first if f.category == "suspicious-download"]
        if not any(t for t in suspicious if "tool.pdf.exe" in t.title or "double extension" in t.detail):
            fail("Expected a suspicious-download finding for the disguised payload")
        if not any(f.category == "uncommon-domain" for f in first):
            fail("Expected uncommon-domain findings")
        if not any(f.category == "repeated-usage" for f in first):
            fail("Expected repeated-usage findings")

        ts_check = [e for e in visits if e.url == "https://mozilla.org/en-US/firefox/"]
        if ts_check:
            expected = BASE - timedelta(days=40)
            delta = abs((ts_check[0].timestamp - expected).total_seconds())
            if delta > 1:
                fail(f"Firefox PRTime conversion wrong: {ts_check[0].timestamp} vs {expected}")
        chrome_first = visits[0]
        if chrome_first.timestamp is None or chrome_first.timestamp.tzinfo is None:
            fail("Chrome timestamp not timezone-aware")

        session = Session()
        session.source = result.source
        session.events = result.events
        session.findings = result.findings
        session.stats = result.stats
        session.domains = result.domains

        out_dir = _os.path.join(work, "export")
        written_csv = export_csv_report(session, out_dir, {"timeline": True, "findings": True,
                                                            "history": True, "downloads": True,
                                                            "bookmarks": True, "domains": True})
        html_file = _os.path.join(out_dir, "report.html")
        export_html_report(session, html_file, {"timeline": True, "findings": True, "history": True,
                                                 "downloads": True, "bookmarks": True, "domains": True})
        if not written_csv or not _os.path.isfile(html_file):
            fail("Exports missing files")
        with open(html_file, "r", encoding="utf-8") as fh:
            content = fh.read()
        if "BrowserTrace" not in content or "tool.pdf.exe" not in content:
            fail("HTML report content incomplete")

        single_source = resolve_source(files=[_os.path.join(chrome_dir, "History"),
                                                _os.path.join(chrome_dir, "Bookmarks")])
        single_result = pipeline(single_source)
        if not single_result.events:
            fail("Manual file selection produced no events")

        print("OK: synthetic self-test passed.")
        print(f"findings: {len(result.findings)}")
        for f in sorted(first, key=lambda x: x.count, reverse=True)[:6]:
            print(f"  [{f.severity.value.upper():6}] {f.category:20} {f.title[:60]}")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())