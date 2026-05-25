"""UTC time helpers for the project."""

from __future__ import annotations

from datetime import datetime, timezone


def get_utc_now():
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


def parse_iso_datetime(datetime_str):
    """Safely parse an ISO datetime string into a UTC-aware datetime."""
    if not datetime_str:
        return None

    try:
        parsed = datetime.fromisoformat(str(datetime_str).strip())
    except (TypeError, ValueError):
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def get_age_seconds(updated_at):
    """Return the age in seconds between now and updated_at."""
    parsed = updated_at if isinstance(updated_at, datetime) else parse_iso_datetime(updated_at)
    if parsed is None:
        return None

    now_utc = get_utc_now()
    return max(0, int((now_utc - parsed.astimezone(timezone.utc)).total_seconds()))
