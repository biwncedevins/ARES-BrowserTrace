from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SourceProfile:
    browser: str
    label: str
    profile_name: str = ""
    root: str = ""
    history_file: str = ""
    bookmarks_file: str = ""
    places_file: str = ""
    auto: bool = False
    note: str = ""

    @property
    def is_firefox(self) -> bool:
        return self.browser == "firefox"

    @property
    def has_history(self) -> bool:
        return bool(self.history_file or self.places_file)

    @property
    def main_db(self) -> str:
        return self.places_file or self.history_file

    def describe(self) -> str:
        parts = [self.label]
        if self.root:
            parts.append(self.root)
        if self.note:
            parts.append(self.note)
        return " — ".join(parts)