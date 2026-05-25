"""Compatibility wrapper for legacy market collection imports."""

from __future__ import annotations

from services.market.collector_service import collect_market_data


if __name__ == "__main__":
    collect_market_data()
