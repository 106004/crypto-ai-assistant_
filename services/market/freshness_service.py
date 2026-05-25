"""Market data freshness checks."""

from __future__ import annotations

from datetime import datetime, timezone

from config.settings import MAX_MARKET_DATA_AGE_SECONDS


def _parse_updated_at(updated_at):
    if isinstance(updated_at, datetime):
        parsed = updated_at
    else:
        value = str(updated_at).strip()
        if value.endswith("Z"):
            value = f"{value[:-1]}+00:00"
        parsed = datetime.fromisoformat(value)

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def get_market_data_age_seconds(market_data):
    market_data = market_data or {}
    updated_at = market_data.get("updated_at")
    if not updated_at:
        print("[Freshness] updated_at 缺失")
        return None

    updated_time = _parse_updated_at(updated_at)
    now_utc = datetime.now(timezone.utc)
    age_seconds = max(0, int((now_utc - updated_time).total_seconds()))
    symbol = str(market_data.get("symbol") or "").strip().upper() or "UNKNOWN"

    print(f"[Freshness] {symbol} age: {age_seconds}s")
    return age_seconds


def is_market_data_fresh(market_data):
    symbol = str((market_data or {}).get("symbol") or "").strip().upper() or "UNKNOWN"
    age_seconds = get_market_data_age_seconds(market_data)
    if age_seconds is None:
        print(f"[Freshness] {symbol} fresh: False")
        return False

    fresh = age_seconds <= MAX_MARKET_DATA_AGE_SECONDS
    print(f"[Freshness] {symbol} fresh: {fresh}")
    return fresh

