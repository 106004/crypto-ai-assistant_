from config.settings import MAX_MARKET_DATA_AGE_SECONDS
from services.market.freshness_service import (
    is_market_data_fresh as _is_market_data_fresh_service,
)


MARKET_DATA_MAX_AGE_SECONDS = MAX_MARKET_DATA_AGE_SECONDS

SUPPORTED_COINS = {
    "btc": {"id": "bitcoin", "name": "Bitcoin", "symbol": "BTC"},
    "eth": {"id": "ethereum", "name": "Ethereum", "symbol": "ETH"},
    "sol": {"id": "solana", "name": "Solana", "symbol": "SOL"},
    "bnb": {"id": "binancecoin", "name": "BNB", "symbol": "BNB"},
    "xrp": {"id": "ripple", "name": "XRP", "symbol": "XRP"},
    "doge": {"id": "dogecoin", "name": "Dogecoin", "symbol": "DOGE"},
    "ada": {"id": "cardano", "name": "Cardano", "symbol": "ADA"},
    "ton": {"id": "the-open-network", "name": "Toncoin", "symbol": "TON"},
    "trx": {"id": "tron", "name": "TRON", "symbol": "TRX"},
    "avax": {"id": "avalanche-2", "name": "Avalanche", "symbol": "AVAX"},
}

COINGLASS_SYMBOLS = {
    "btc": "BTC",
    "eth": "ETH",
    "sol": "SOL",
    "bnb": "BNB",
    "xrp": "XRP",
    "doge": "DOGE",
    "ada": "ADA",
    "ton": "TON",
    "trx": "TRX",
    "avax": "AVAX",
}


def get_coinglass_url(symbol):
    normalized_symbol = str(symbol).strip().lower()
    coinglass_symbol = COINGLASS_SYMBOLS.get(normalized_symbol)
    if coinglass_symbol is None:
        return None

    return f"https://www.coinglass.com/zh-TW/currencies/{coinglass_symbol}"


def get_all_mainstream_coinglass_links():
    lines = []
    for symbol_key, coinglass_symbol in COINGLASS_SYMBOLS.items():
        lines.append(f"{symbol_key.upper()}")
        lines.append(f"https://www.coinglass.com/zh-TW/currencies/{coinglass_symbol}")
        lines.append("")

    return "\n".join(lines).strip()


def get_coinglass_fallback_message():
    return (
        "目前無法提供即時價格。\n\n"
        "請改看 CoinGlass 即時行情。\n"
        f"系統只接受 {MAX_MARKET_DATA_AGE_SECONDS // 60} 分鐘內的價格資料，避免誤導。\n\n"
        f"{get_all_mainstream_coinglass_links()}"
    )


def _is_market_data_fresh(symbol, updated_at):
    market_data = {"symbol": symbol, "updated_at": updated_at}
    return _is_market_data_fresh_service(market_data)


def get_coin_from_supabase(symbol):
    """Read one fresh coin from Supabase market_data."""

    normalized_symbol = str(symbol).strip().upper()
    print(f"[SupabaseData] reading market_data for {normalized_symbol}")

    try:
        from database_manager import get_market_data_by_symbol

        coin_data = get_market_data_by_symbol(normalized_symbol)
    except Exception as error:
        print(f"[SupabaseData] market_data fetch failed: {error}")
        print("[SupabaseData] no fresh data available")
        return None

    found = isinstance(coin_data, dict)
    print(f"[SupabaseData] found: {found}")
    if not found:
        print(f"[Freshness] {normalized_symbol} no Supabase data, using CoinGlass fallback links")
        return None

    try:
        fresh = _is_market_data_fresh(normalized_symbol, coin_data.get("updated_at"))
    except (TypeError, ValueError) as error:
        print(f"[Freshness] {normalized_symbol} updated_at parse failed: {error}")
        fresh = False

    if not fresh:
        return None

    result = dict(coin_data)
    result["source"] = "Supabase"
    return result
