import os
import sys


def resource_path(relative: str) -> str:
    """Resolve a bundled resource path when frozen with PyInstaller."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, relative)
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), relative)


def icon_path() -> str:
    return resource_path(os.path.join("resources", "icon.ico"))


def icon_png_path() -> str:
    return resource_path(os.path.join("resources", "icon.png"))