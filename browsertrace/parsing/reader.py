from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
from typing import Iterator, Optional


class DBError(Exception):
    pass


class _Connection:
    def __init__(self, db_path: str, copy_dir: Optional[str] = None):
        self.db_path = db_path
        self.copy_dir = copy_dir or ""
        self.conn: Optional[sqlite3.Connection] = None

    def __enter__(self):
        path = self.db_path
        if self.copy_dir:
            base = os.path.basename(self.db_path)
            path = os.path.join(self.copy_dir, base)
        try:
            self.conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA query_only = ON")
            self.conn.execute("PRAGMA temp_store = MEMORY")
        except sqlite3.Error as exc:
            raise DBError(f"Unable to open database read-only: {path}\n{exc}") from exc
        return self

    def __exit__(self, *exc):
        if self.conn is not None:
            try:
                self.conn.close()
            except sqlite3.Error:
                pass


def copy_database(db_path: str) -> str:
    """Take a snapshot copy of a SQLite database so the browser lock never blocks us.

    Also copies the sibling WAL/SHM files so recent un-checkpointed pages survive.
    Returns a temp directory containing the snapshot.
    """
    if not db_path or not os.path.isfile(db_path):
        raise DBError(f"Artifact database not found: {db_path}")
    copy_dir = tempfile.mkdtemp(prefix="browsertrace_")
    try:
        base = os.path.basename(db_path)
        shutil.copy2(db_path, os.path.join(copy_dir, base))
        for suffix in ("-wal", "-shm"):
            side = db_path + suffix
            if os.path.isfile(side):
                shutil.copy2(side, os.path.join(copy_dir, base + suffix))
        return copy_dir
    except OSError as exc:
        shutil.rmtree(copy_dir, ignore_errors=True)
        raise DBError(f"Unable to snapshot database {db_path}: {exc}") from exc


create_snapshot = copy_database


def clear_snapshot(copy_dir: str) -> None:
    if copy_dir:
        shutil.rmtree(copy_dir, ignore_errors=True)


def path_inside(copy_dir: str, db_path: str) -> str:
    return os.path.join(copy_dir, os.path.basename(db_path))


def snapshot_ttl():
    pass


def table_columns(db_path: str, table: str) -> set:
    with _Connection(db_path) as cx:
        try:
            rows = cx.conn.execute(f"PRAGMA table_info({table})").fetchall()
            return {str(r["name"]) for r in rows}
        except sqlite3.Error:
            return set()


def available_tables(db_path: str) -> set:
    with _Connection(db_path) as cx:
        try:
            rows = cx.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            return {str(r["name"]) for r in rows}
        except sqlite3.Error:
            return set()


def query_rows(db_path: str, sql: str, params: tuple = ()) -> list:
    with _Connection(db_path) as cx:
        try:
            cursor = cx.conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as exc:
            raise DBError(f"Query failed: {exc}") from exc


def iter_rows(db_path: str, copy_dir: str, sql: str, params: tuple = ()) -> Iterator[dict]:
    """Query against the snapshot copy when available, yielding rows lazily."""
    target = db_path
    cleanup = ""
    if copy_dir:
        target = path_inside(copy_dir, db_path)
        cleanup = copy_dir
    with _Connection(target) as cx:
        try:
            cursor = cx.conn.execute(sql, params)
            for row in cursor:
                yield dict(row)
        finally:
            if cleanup:
                shutil.rmtree(cleanup, ignore_errors=True)