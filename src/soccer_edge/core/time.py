"""Timezone-aware time helpers. All timestamps in this system are UTC-aware."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def ensure_utc(dt: datetime) -> datetime:
    """Reject naive datetimes loudly; normalise aware ones to UTC."""
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"naive datetime not allowed: {dt!r}")
    return dt.astimezone(UTC)


def parse_iso_utc(value: str) -> datetime:
    """Parse an ISO-8601 string (accepting a trailing 'Z') into a UTC datetime."""
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError(f"timestamp without timezone: {value!r}")
    return dt.astimezone(UTC)


def iso_utc(dt: datetime) -> str:
    """Deterministic ISO string with 'Z' suffix and second precision unless sub-second present."""
    dt = ensure_utc(dt)
    if dt.microsecond:
        return dt.isoformat(timespec="microseconds").replace("+00:00", "Z")
    return dt.isoformat(timespec="seconds").replace("+00:00", "Z")


def minutes_until(target: datetime, now: datetime | None = None) -> float:
    now = now or utc_now()
    return (ensure_utc(target) - ensure_utc(now)) / timedelta(minutes=1)
