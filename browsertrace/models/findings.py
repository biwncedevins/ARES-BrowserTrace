from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @property
    def rank(self) -> int:
        return {Severity.INFO: 0, Severity.LOW: 1, Severity.MEDIUM: 2, Severity.HIGH: 3}[self]

    @property
    def label(self) -> str:
        return self.value.upper()


@dataclass
class Finding:
    id: str
    severity: Severity
    category: str
    title: str
    detail: str = ""
    domain: str = ""
    timestamps: list = field(default_factory=list)
    event_ids: list = field(default_factory=list)
    source: str = ""
    count: int = 1

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "severity": self.severity.value,
            "category": self.category,
            "title": self.title,
            "detail": self.detail,
            "domain": self.domain,
            "timestamps": [str(t) for t in self.timestamps],
            "event_ids": list(self.event_ids),
            "source": self.source,
            "count": self.count,
        }