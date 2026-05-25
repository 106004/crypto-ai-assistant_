"""CoinGecko client wrapper for market collection."""

from __future__ import annotations

from typing import Dict

import requests

from services.market.coin_catalog import SUPPORTED_COINS as CATALOG_SUPPORTED_COINS


COINGECKO_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"

TRACKED_COINS: Dict[str, dict] = {
    symbol: {
        "id": info["coingecko_id"],
        "name": info["name"],
        "symbol": symbol.upper(),
    }
    for symbol, info in CATALOG_SUPPORTED_COINS.items()
}


def fetch_market_data(tracked_coins=None, timeout=10):
    coins = tracked_coins or TRACKED_COINS
    params = {
        "ids": ",".join(coin["id"] for coin in coins.values()),
        "vs_currencies": "usd",
        "include_24hr_change": "true",
    }

    print("[CoinGeckoClient] start request")
    try:
        response = requests.get(COINGECKO_PRICE_URL, params=params, timeout=timeout)
        response.raise_for_status()
        print("[CoinGeckoClient] request success")
        return response.json()
    except Exception as error:
        print(f"[CoinGeckoClient][ERROR] request failed: {error}")
        return None


def fetch_market_prices(tracked_coins=None, timeout=10):
    """Legacy compatibility wrapper."""
    return fetch_market_data(tracked_coins=tracked_coins, timeout=timeout)
