from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Union

try:
    from dateutil import parser as _dateutil_parser
except Exception:  # pragma: no cover
    _dateutil_parser = None


class TimeForge:
    """TimeForge-style timestamp normalization.

    Browser vendors store time in several incompatible epochs:

      * Chromium (Chrome/Edge) history:  microseconds since 1601-01-01 UTC
      * Firefox  PRTime (places):        microseconds since 1601-01-01 UTC
      * Unix-style:                      seconds / milliseconds / microseconds / nanoseconds

    ``TimeForge`` converts every source value into a single timezone-aware UTC
    ``datetime`` cached on each event, then renders it in one canonical UI format.
    """

    EPOCH_1601 = datetime(1601, 1, 1, tzinfo=timezone.utc)
    UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
    CANONICAL_FORMAT = "%Y-%m-%d %H:%M:%S"

    FORMAT_EPOCH_1601_US = "epoch1601_us"
    FORMAT_UNIX_NS = "unix_ns"
    FORMAT_UNIX_US = "unix_us"
    FORMAT_UNIX_MS = "unix_ms"
    FORMAT_UNIX_S = "unix_s"
    FORMAT_ISO = "iso8601"

    _E1_6 = 1_000_000_000_000_000_000
    _E1_5 = 1_000_000_000_000_000
    _E1_3 = 1_000_000_000_000
    _E1_0 = 1_000_000_000

    @classmethod
    def from_epoch1601_us(cls, value) -> Optional[datetime]:
        if value is None:
            return None
        return cls.EPOCH_1601 + timedelta(seconds=int(value) / 1_000_000.0)

    @classmethod
    def from_unix_s(cls, value) -> Optional[datetime]:
        if value is None:
            return None
        return cls.UNIX_EPOCH + timedelta(seconds=float(value))

    @classmethod
    def from_unix_ms(cls, value) -> Optional[datetime]:
        if value is None:
            return None
        return cls.UNIX_EPOCH + timedelta(seconds=float(value) / 1000.0)

    @classmethod
    def from_unix_us(cls, value) -> Optional[datetime]:
        if value is None:
            return None
        return cls.UNIX_EPOCH + timedelta(seconds=float(value) / 1_000_000.0)

    @classmethod
    def from_unix_ns(cls, value) -> Optional[datetime]:
        if value is None:
            return None
        return cls.UNIX_EPOCH + timedelta(seconds=float(value) / 1_000_000_000.0)

    @classmethod
    def from_iso(cls, value: str) -> Optional[datetime]:
        if _dateutil_parser is not None:
            try:
                return _dateutil_parser.isoparse(value)
            except Exception:
                return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None

    @classmethod
    def detect_format(cls, value: Union[int, float, str]) -> Optional[str]:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return cls.FORMAT_ISO if (isinstance(value, str) and value.strip()) else None
        magnitude = abs(numeric)
        if magnitude >= cls._E1_6:
            return cls.FORMAT_UNIX_NS
        if magnitude >= cls._E1_5:
            return cls.FORMAT_EPOCH_1601_US
        if magnitude >= cls._E1_3:
            return cls.FORMAT_UNIX_US
        if magnitude >= cls._E1_0:
            return cls.FORMAT_UNIX_MS
        if magnitude >= 100_000_000:
            return cls.FORMAT_UNIX_S
        return None

    _HINT_MAP = {
        "chrome": FORMAT_EPOCH_1601_US,
        "webkit": FORMAT_EPOCH_1601_US,
        "prtime": FORMAT_EPOCH_1601_US,
        "epoch1601_us": FORMAT_EPOCH_1601_US,
        "unix_us": FORMAT_UNIX_US,
        "unix_ms": FORMAT_UNIX_MS,
        "unix_s": FORMAT_UNIX_S,
        "unix_ns": FORMAT_UNIX_NS,
        "iso": FORMAT_ISO,
    }

    @classmethod
    def normalize(cls, value, hint: str = "") -> Optional[datetime]:
        """Normalize an arbitrary browser timestamp to a UTC-aware datetime."""
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)

        fmt = cls._HINT_MAP.get(str(hint).lower()) or cls.detect_format(value)

        if fmt == cls.FORMAT_EPOCH_1601_US:
            return cls.from_epoch1601_us(value)
        if fmt == cls.FORMAT_UNIX_NS:
            return cls.from_unix_ns(value)
        if fmt == cls.FORMAT_UNIX_US:
            return cls.from_unix_us(value)
        if fmt == cls.FORMAT_UNIX_MS:
            return cls.from_unix_ms(value)
        if fmt == cls.FORMAT_UNIX_S:
            return cls.from_unix_s(value)
        if fmt == cls.FORMAT_ISO:
            return cls.from_iso(str(value))

        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return cls.from_iso(str(value))
        if numeric >= 0:
            detected = cls.detect_format(numeric)
            if detected and detected != cls.FORMAT_ISO:
                return cls.normalize(numeric, detected)
        return None

    @classmethod
    def to_epoch1601_us(cls, dt: datetime) -> int:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt = dt.astimezone(timezone.utc)
        return int((dt - cls.EPOCH_1601).total_seconds() * 1_000_000)

    @classmethod
    def to_unix_us(cls, dt: datetime) -> int:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt = dt.astimezone(timezone.utc)
        return int((dt - cls.UNIX_EPOCH).total_seconds() * 1_000_000)

    @classmethod
    def _local_tz(cls):
        return datetime.now().astimezone().tzinfo

    @classmethod
    def _fmt(cls, dt: datetime, fsuffix: str) -> str:
        micro = dt.strftime("%f")[:3]
        return dt.strftime(cls.CANONICAL_FORMAT) + fsuffix + micro

    @classmethod
    def display_utc(cls, dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt = dt.astimezone(timezone.utc)
        return cls._fmt(dt, " UTC")

    @classmethod
    def display_local(cls, dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        try:
            dt_local = dt.astimezone()
        except Exception:
            dt_local = dt.astimezone(cls._local_tz())
        return cls._fmt(dt_local, "")

    @classmethod
    def iso_utc(cls, dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    @classmethod
    def label_for_hint(cls, hint: str) -> str:
        return {
            "chrome": "Chromium epoch (µs since 1601-01-01 UTC)",
            "webkit": "WebKit/Chromium epoch (µs since 1601-01-01 UTC)",
            "prtime": "Firefox PRTime (µs since 1601-01-01 UTC)",
            "unix_us": "Unix microseconds",
            "unix_ms": "Unix milliseconds",
            "unix_s": "Unix seconds",
            "iso": "ISO-8601 string",
        }.get(hint, "auto-detected")