from datetime import datetime, timezone


MARKET_DATA_MAX_AGE_SECONDS = 5 * 60

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
        lines.append(f"{symbol_key.upper()}：")
        lines.append(f"https://www.coinglass.com/zh-TW/currencies/{coinglass_symbol}")
        lines.append("")

    return "\n".join(lines).strip()


def get_coinglass_fallback_message():
    return (
        "⚠️ 即時市場資料服務暫時異常\n\n"
        "因為價格具有即時性，\n"
        "系統不會使用超過 5 分鐘的舊價格避免誤導。\n\n"
        "你可以先查看 CoinGlass 即時行情：\n\n"
        f"{get_all_mainstream_coinglass_links()}"
    )


def _is_market_data_fresh(symbol, updated_at):
    if isinstance(updated_at, datetime):
        updated_time = updated_at
    else:
        value = str(updated_at).strip()
        if value.endswith("Z"):
            value = f"{value[:-1]}+00:00"
        updated_time = datetime.fromisoformat(value)

    if updated_time.tzinfo is None:
        updated_time = updated_time.replace(tzinfo=timezone.utc)
    else:
        updated_time = updated_time.astimezone(timezone.utc)

    now_utc = datetime.now(timezone.utc)
    age_seconds = max(0, (now_utc - updated_time).total_seconds())
    age_minutes = age_seconds / 60
    fresh = age_seconds <= MARKET_DATA_MAX_AGE_SECONDS

    print(f"[Freshness] {symbol} updated_at 原始值：{updated_at}")
    print(f"[Freshness] {symbol} parsed updated_at UTC：{updated_time.isoformat()}")
    print(f"[Freshness] 系統現在 UTC：{now_utc.isoformat()}")
    print(f"[Freshness] 資料年齡：{age_minutes:.1f} 分鐘")
    print("[Freshness] freshness limit：5 分鐘")
    print(f"[Freshness] fresh：{fresh}")

    if fresh:
        print(f"[Freshness] {symbol} 資料新鮮，資料年齡：{age_minutes:.1f} 分鐘")
    else:
        print(f"[Freshness] {symbol} 資料已過期，資料年齡：{age_minutes:.1f} 分鐘，超過限制：5 分鐘，放棄使用 Supabase 價格")

    return fresh


def get_coin_from_supabase(symbol):
    """Read one fresh coin from Supabase market_data."""

    normalized_symbol = str(symbol).strip().upper()
    print(f"[SupabaseData] 嘗試讀取 market_data：{normalized_symbol}")

    try:
        from database_manager import get_market_data_by_symbol

        coin_data = get_market_data_by_symbol(normalized_symbol)
    except Exception as error:
        print(f"[SupabaseData] 讀取 market_data 失敗：{error}")
        print("[SupabaseData] 是否找到資料：False")
        return None

    found = isinstance(coin_data, dict)
    print(f"[SupabaseData] 是否找到資料：{found}")
    if not found:
        print(f"[Freshness] {normalized_symbol} 在 Supabase 沒有資料，提供 CoinGlass fallback links")
        return None

    try:
        fresh = _is_market_data_fresh(normalized_symbol, coin_data.get("updated_at"))
    except (TypeError, ValueError) as error:
        print(f"[Freshness] {normalized_symbol} updated_at 解析失敗：{error}")
        fresh = False

    if not fresh:
        return None
    result = dict(coin_data)
    result["source"] = "Supabase"
    return result
