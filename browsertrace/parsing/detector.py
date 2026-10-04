from __future__ import annotations

import configparser
import json
import os
from typing import List, Optional

from ..models import SourceProfile


def _appdata() -> str:
    return os.environ.get("APPDATA", "")

def _localappdata() -> str:
    return os.environ.get("LOCALAPPDATA", "")


CHROMIUM_ROOTS = [
    ("chrome", "Google", "Chrome", "User Data"),
    ("edge", "Microsoft", "Edge", "User Data"),
    ("chrome", "Google", "Chromium", "User Data"),
    ("chrome", "BraveSoftware", "Brave-Browser", "User Data"),
]


def _chromium_profiles(browser: str, user_data_dir: str) -> List[SourceProfile]:
    if not user_data_dir or not os.path.isdir(user_data_dir):
        return []
    profiles = []
    try:
        entries = sorted(os.listdir(user_data_dir))
    except OSError:
        return []
    skip = {
        "Cache", "Code Cache", "GrShaderCache", "ShaderCache", "GPUCache",
        "Crashpad", "DawnGraphiteCache", "Local State", "GraphiteDawnCache",
        "component_crx_cache", "OptimizationHints", "First Run", "metrics",
    }
    for name in entries:
        sub = os.path.join(user_data_dir, name)
        if not os.path.isdir(sub):
            continue
        if name in skip or name.startswith("."):
            continue
        has_history = os.path.isfile(os.path.join(sub, "History"))
        if not has_history and name not in ("Default", "Guest Profile", "System Profile"):
            continue
        if name.startswith("Profile ") or name in ("Default", "Guest Profile", "System Profile"):
            label = _chromium_label(sub, name, browser)
            profiles.append(
                SourceProfile(
                    browser=browser,
                    label=label,
                    profile_name=name,
                    root=user_data_dir,
                    history_file=os.path.join(sub, "History"),
                    bookmarks_file=os.path.join(sub, "Bookmarks"),
                    auto=True,
                )
            )
    return profiles


def _chromium_label(profile_dir: str, name: str, browser: str) -> str:
    label = name
    prefs = os.path.join(profile_dir, "Preferences")
    try:
        with open(prefs, "r", encoding="utf-8", errors="replace") as fh:
            data = json.load(fh)
        label = data.get("profile", {}).get("name") or label
    except (OSError, ValueError):
        pass
    pretty = browser.capitalize()
    if browser == "edge":
        pretty = "Edge"
    return f"{pretty} — {label}"


def _firefox_profiles() -> List[SourceProfile]:
    base = os.path.join(_appdata(), "Mozilla", "Firefox")
    if not os.path.isdir(base):
        return []
    profiles = []
    ini = os.path.join(base, "profiles.ini")
    seen = set()
    if os.path.isfile(ini):
        parser = configparser.ConfigParser()
        try:
            parser.read(ini, encoding="utf-8")
        except Exception:
            parser = configparser.ConfigParser()
        for section in parser.sections():
            if section.lower().startswith("profile"):
                rel = parser.get(section, "path", fallback="")
                name = parser.get(section, "name", fallback=rel)
                is_relative = parser.get(section, "isrelative", fallback="1") == "1"
                full = os.path.join(base, rel) if is_relative else rel
                if not os.path.isdir(full):
                    continue
                label = f"Firefox — {name}"
                if full not in seen:
                    seen.add(full)
                    profiles.append(
                        SourceProfile(
                            browser="firefox",
                            label=label,
                            profile_name=name,
                            root=full,
                            places_file=os.path.join(full, "places.sqlite"),
                            auto=True,
                        )
                    )
    profiles_dir = os.path.join(base, "Profiles")
    if os.path.isdir(profiles_dir):
        try:
            for name in sorted(os.listdir(profiles_dir)):
                full = os.path.join(profiles_dir, name)
                if not os.path.isdir(full) or full in seen:
                    continue
                seen.add(full)
                profiles.append(
                    SourceProfile(
                        browser="firefox",
                        label=f"Firefox — {name}",
                        profile_name=name,
                        root=full,
                        places_file=os.path.join(full, "places.sqlite"),
                        auto=True,
                    )
                )
        except OSError:
            pass
    for p in profiles:
        if not os.path.isfile(p.places_file):
            p.note = "places.sqlite missing (browser may be running or profile uninitialized)"
    return profiles


def detect_profiles() -> List[SourceProfile]:
    profiles: List[SourceProfile] = []
    local = _localappdata()
    for browser, vendor, product, sub in CHROMIUM_ROOTS:
        user_data = os.path.join(local, vendor, product, sub)
        if not os.path.isdir(user_data):
            continue
        for p in _chromium_profiles(browser, user_data):
            if not p.has_history:
                p.note = "No History database found in this profile."
            profiles.append(p)
    profiles.extend(_firefox_profiles())
    for p in profiles:
        if p.auto and p.note == "":
            pass
    return profiles


def refresh_profile(profile: SourceProfile) -> SourceProfile:
    """Re-check artifact paths for a profile (e.g. after browser close)."""
    if profile.is_firefox:
        if not os.path.isfile(profile.places_file):
            profile.note = "places.sqlite missing"
    else:
        if not os.path.isfile(profile.history_file):
            profile.note = "History database missing"
        if not os.path.isfile(profile.bookmarks_file):
            profile.bookmarks_file = ""
    return profile