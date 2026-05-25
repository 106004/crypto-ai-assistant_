"""Market data collection service."""

from __future__ import annotations

import json
from pathlib import Path

from data.clients.coingecko_client import fetch_market_data
import data.repositories.market_data_repository as market_data_repository
from services.market.coin_catalog import SUPPORTED_COINS
from utils.logging_utils import log_error, log_info
from utils.time_utils import get_utc_now


MARKET_DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "market_data.json"


def _get_tracked_coins():
    return {
        symbol: {
            "id": info["coingecko_id"],
            "name": info["name"],
            "symbol": symbol.upper(),
        }
        for symbol, info in SUPPORTED_COINS.items()
    }


def _save_market_data_to_json(data):
    try:
        MARKET_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        with MARKET_DATA_FILE.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        log_info("CollectorService", f"fallback JSON saved: {MARKET_DATA_FILE}")
    except OSError as error:
        log_error("CollectorService", f"fallback JSON save failed: {error}")
        return False

    return True


def _load_market_data_from_json():
    if not MARKET_DATA_FILE.exists():
        return {}

    try:
        if MARKET_DATA_FILE.stat().st_size == 0:
            return {}

        with MARKET_DATA_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        log_error("CollectorService", f"fallback JSON load failed: {error}")
        return {}


def _normalize_coin(coin_key, coin_meta, coin_data, updated_at):
    price_usd = coin_data.get("usd")
    change_24h = coin_data.get("usd_24h_change")

    if price_usd is None or change_24h is None:
        return None

    normalized = {
        "name": coin_meta["name"],
        "symbol": coin_meta["symbol"],
        "price_usd": price_usd,
        "change_24h": change_24h,
        "source": "CoinGecko",
        "updated_at": updated_at,
        "updated_by": "CollectorService",
    }
    log_info("CollectorService", f"{coin_meta['symbol']} normalized")
    return normalized


def collect_market_data():
    log_info("CollectorService", "開始 market collection")

    tracked_coins = _get_tracked_coins()

    try:
        api_data = fetch_market_data(tracked_coins)
        if api_data is None:
            log_error("CollectorService", "CoinGecko fetch failed")
            return _load_market_data_from_json()
        log_info("CollectorService", "CoinGecko data fetched")
    except Exception as error:
        log_error("CollectorService", f"CoinGecko fetch failed: {error}")
        return _load_market_data_from_json()

    updated_at = get_utc_now().isoformat()
    market_data = {}
    supabase_ok = True

    for coin_key, coin_meta in tracked_coins.items():
        coin_data = api_data.get(coin_meta["id"], {})
        normalized = _normalize_coin(coin_key, coin_meta, coin_data, updated_at)
        if normalized is None:
            continue

        market_data[coin_key] = normalized

        if market_data_repository.save_market_data(normalized):
            log_info("CollectorService", f"{coin_meta['symbol']} saved")
        else:
            supabase_ok = False

    if not market_data:
        log_error("CollectorService", "no market data normalized")
        return _load_market_data_from_json()

    if not supabase_ok:
        log_error("CollectorService", "Supabase save failed, using fallback JSON")
        _save_market_data_to_json(market_data)

    log_info("CollectorService", "market collection complete")
    return market_data
