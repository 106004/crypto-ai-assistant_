"""LINE price query flow."""

from __future__ import annotations

from crypto_api import get_coinglass_fallback_message
from data.repositories.market_data_repository import get_market_data
from data.repositories.market_data_repository import get_market_data_by_symbol  # compatibility alias
from services.line.message_service import format_price_message, format_stale_data_message
from services.market.freshness_service import is_market_data_fresh


def handle_price_query(symbol):
    display_symbol = str(symbol).strip().upper()
    print(f"[PriceService] 開始查詢 {display_symbol}")

    market_data = get_market_data_by_symbol(display_symbol)
    if not isinstance(market_data, dict):
        print("[PriceService] 使用 CoinGlass fallback")
        return format_stale_data_message(display_symbol, get_coinglass_fallback_message())

    print("[PriceService] 找到 market_data")
    fresh = is_market_data_fresh(market_data)
    print(f"[PriceService] freshness: {fresh}")
    if not fresh:
        print("[PriceService] 使用 CoinGlass fallback")
        return format_stale_data_message(display_symbol, get_coinglass_fallback_message())

    return format_price_message(market_data)
