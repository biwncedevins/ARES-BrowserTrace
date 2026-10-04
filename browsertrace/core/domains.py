from __future__ import annotations

from urllib.parse import urlparse

COMMON_TLDS = {
    "com", "org", "net", "io", "co", "gov", "edu", "info", "biz", "me", "dev",
    "app", "tv", "cc", "pro", "xyz", "site", "online", "tech", "ai", "blog",
}


def extract_domain(url: str) -> str:
    """Extract a normalized registrable-ish host from a URL.

    Strips scheme, ports, userinfo and the leading ``www``. Returns an empty
    string for non-navigable schemes such as ``about:``, ``chrome://``,
    ``data:`` and ``file://``.
    """
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        host = parsed.hostname
    except (ValueError, TypeError):
        return ""
    if not host:
        return ""
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def registrable_domain(host: str) -> str:
    """Best-effort reduction to the registrable domain (e.g. mail.google.com -> google.com)."""
    if not host:
        return ""
    labels = host.split(".")
    if len(labels) <= 2:
        return host
    suffix = labels[-1]
    if suffix in COMMON_TLDS and len(labels) >= 3:
        return ".".join(labels[-2:])
    return host


def is_ip_address(host: str) -> bool:
    import ipaddress

    if not host:
        return False
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False