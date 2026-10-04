from __future__ import annotations


def human_size(num) -> str:
    try:
        value = float(num)
    except (TypeError, ValueError):
        return ""
    if value <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if value < 1000 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} B"
            return f"{value:.2f} {unit}"
        value /= 1000.0
    return f"{value:.2f} {units[-1]}"


def truncate(text: str, limit: int = 80) -> str:
    if not text:
        return ""
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def filename_from_path(path: str) -> str:
    if not path:
        return ""
    import os

    return os.path.basename(path.rstrip("/\\")) or path


def safe_text(value) -> str:
    if value is None:
        return ""
    return str(value)