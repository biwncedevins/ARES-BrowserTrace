from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class EventKind(str, Enum):
    VISIT = "visit"
    DOWNLOAD = "download"
    BOOKMARK = "bookmark"

    @property
    def label(self) -> str:
        return {
            EventKind.VISIT: "VISIT",
            EventKind.DOWNLOAD: "DOWNLOAD",
            EventKind.BOOKMARK: "BOOKMARK",
        }[self]


@dataclass
class Event:
    id: str
    kind: EventKind
    browser: str
    profile: str
    timestamp: Optional[datetime]
    url: str = ""
    domain: str = ""
    title: str = ""
    detail: str = ""
    flags: list = field(default_factory=list)
    visit_count: int = 0
    transition: str = ""
    from_visit: str = ""
    file_name: str = ""
    target_path: str = ""
    mime_type: str = ""
    total_bytes: int = 0
    received_bytes: int = 0
    state: str = ""
    danger_type: str = ""
    referrer: str = ""
    folder_path: str = ""
    added_time: Optional[datetime] = None
    modified_time: Optional[datetime] = None
    raw: dict = field(default_factory=dict)

    def event_text(self) -> str:
        if self.kind == EventKind.VISIT:
            return self.title or self.url
        if self.kind == EventKind.DOWNLOAD:
            return self.file_name or self.url
        if self.kind == EventKind.BOOKMARK:
            return self.title or self.url
        return self.url

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "browser": self.browser,
            "profile": self.profile,
            "timestamp": self.timestamp,
            "url": self.url,
            "domain": self.domain,
            "title": self.title,
            "detail": self.detail,
            "flags": list(self.flags),
            "visit_count": self.visit_count,
            "transition": self.transition,
            "from_visit": self.from_visit,
            "file_name": self.file_name,
            "target_path": self.target_path,
            "mime_type": self.mime_type,
            "total_bytes": self.total_bytes,
            "received_bytes": self.received_bytes,
            "state": self.state,
            "danger_type": self.danger_type,
            "referrer": self.referrer,
            "folder_path": self.folder_path,
        }