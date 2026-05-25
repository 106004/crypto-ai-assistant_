"""Compatibility wrapper for legacy market collection tests and imports."""

from __future__ import annotations

import json
from pathlib import Path

import requests

from data.clients.coingecko_client import COINGECKO_PRICE_URL, TRACKED_COINS
from utils.time_utils import get_utc_now


MARKET_DATA_FILE = Path(__file__).resolve().parent / "data" / "market_data.json"


def _build_params():
    return {
        "ids": ",".join(coin["id"] for coin in TRACKED_COINS.values()),
        "vs_currencies": "usd",
        "include_24hr_change": "true",
    }


def _save_market_data_to_json(data):
    try:
        MARKET_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        with MARKET_DATA_FILE.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        print(f"[MarketCollector] fallback JSON saved: {MARKET_DATA_FILE}")
    except OSError as error:
        print(f"[MarketCollector] fallback JSON save failed: {error}")
        return False

    return True


def save_market_data(data):
    """Legacy helper kept for compatibility with existing code paths."""

    try:
        from database_manager import upsert_market_data
    except Exception as error:
        print(f"[MarketCollector] Supabase unavailable, using JSON fallback: {error}")
        print("[MarketCollector] 使用 fallback local JSON")
        _save_market_data_to_json(data)
        return

    supabase_ok = True
    for coin_data in data.values():
        symbol = str(coin_data.get("symbol", "")).strip().upper() or "UNKNOWN"
        print(f"[MarketCollector] 準備寫入 Supabase：{symbol}")
        if not upsert_market_data(coin_data):
            supabase_ok = False

    if supabase_ok:
        print("[MarketCollector] Supabase market_data saved")
        return

    print("[MarketCollector] Supabase write failed, saving data/market_data.json")
    print("[MarketCollector] 使用 fallback local JSON")
    _save_market_data_to_json(data)


def load_market_data():
    """Legacy JSON fallback loader kept for compatibility."""

    if not MARKET_DATA_FILE.exists():
        return {}

    try:
        if MARKET_DATA_FILE.stat().st_size == 0:
            return {}

        with MARKET_DATA_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        print(f"[MarketCollector] load market_data.json failed: {error}")
        return {}


def collect_market_data():
    """Legacy collector wrapper with the old logging shape for tests."""

    print("[MarketCollector] 開始 market collection")

    try:
        response = requests.get(COINGECKO_PRICE_URL, params=_build_params(), timeout=10)
        response.raise_for_status()
        print("[MarketCollector] CoinGecko API 查詢成功")
        api_data = response.json()
    except requests.HTTPError as error:
        status_code = getattr(getattr(error, "response", None), "status_code", None)
        if status_code == 429:
            print("[MarketCollector] CoinGecko 被限流")
        else:
            print(f"[MarketCollector] CoinGecko API 查詢失敗: {error}")
        fallback_data = load_market_data()
        if fallback_data:
            print("[MarketCollector] 使用 fallback local JSON")
        print("[MarketCollector] market_data 更新完成")
        return fallback_data
    except Exception as error:
        print(f"[MarketCollector] CoinGecko API 查詢失敗: {error}")
        fallback_data = load_market_data()
        if fallback_data:
            print("[MarketCollector] 使用 fallback local JSON")
        print("[MarketCollector] market_data 更新完成")
        return fallback_data

    updated_at = get_utc_now().isoformat()
    market_data = {}

    for coin_key, coin_meta in TRACKED_COINS.items():
        coin_data = api_data.get(coin_meta["id"], {})
        price_usd = coin_data.get("usd")
        change_24h = coin_data.get("usd_24h_change")
        if price_usd is None or change_24h is None:
            continue

        normalized = {
            "name": coin_meta["name"],
            "symbol": coin_meta["symbol"],
            "price_usd": price_usd,
            "change_24h": change_24h,
            "source": "CoinGecko",
            "updated_at": updated_at,
            "updated_by": "MarketCollector",
        }
        market_data[coin_key] = normalized
        print(f"[MarketCollector] 準備寫入 Supabase：{coin_meta['symbol']}")

    if market_data:
        save_market_data(market_data)
    else:
        print("[MarketCollector] 使用 fallback local JSON")
        market_data = load_market_data()

    print("[MarketCollector] market_data 更新完成")
    return market_data


if __name__ == "__main__":
    collect_market_data()
