"""Lightweight market data model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class MarketData:
    symbol: str
    name: str
    price_usd: Any
    change_24h: Any
    source: str
    updated_at: Any
    updated_by: Optional[str] = None

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            print("[MarketDataModel][ERROR] invalid market data")
            return None

        try:
            symbol = str(data["symbol"]).strip().upper()
            name = str(data["name"]).strip()
            price_usd = data["price_usd"]
            change_24h = data["change_24h"]
            source = str(data.get("source", "")).strip() or "Unknown"
            updated_at = data["updated_at"]
            updated_by = data.get("updated_by")
        except KeyError:
            print("[MarketDataModel][ERROR] invalid market data")
            return None

        if not symbol or not name or updated_at is None:
            print("[MarketDataModel][ERROR] invalid market data")
            return None

        print("[MarketDataModel] MarketData created")
        return cls(
            symbol=symbol,
            name=name,
            price_usd=price_usd,
            change_24h=change_24h,
            source=source,
            updated_at=updated_at,
            updated_by=updated_by,
        )

    def to_dict(self):
        data = {
            "symbol": self.symbol,
            "name": self.name,
            "price_usd": self.price_usd,
            "change_24h": self.change_24h,
            "source": self.source,
            "updated_at": self.updated_at,
        }
        if self.updated_by is not None:
            data["updated_by"] = self.updated_by
        return data
