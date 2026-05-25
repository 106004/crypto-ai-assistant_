"""Market data repository for Supabase market_data table."""

from __future__ import annotations

from data.clients.supabase_client import get_supabase_client


def _normalize_symbol(symbol):
    return str(symbol or "").strip().upper()


def _first_row(response):
    data = getattr(response, "data", None)
    if isinstance(data, list) and data:
        return data[0]
    return None


def get_market_data(symbol):
    normalized_symbol = _normalize_symbol(symbol)
    print(f"[MarketDataRepository] fetching {normalized_symbol or 'UNKNOWN'}")
    if not normalized_symbol:
        return None

    client = get_supabase_client()
    if client is None:
        return None

    try:
        response = (
            client.table("market_data")
            .select("*")
            .eq("symbol", normalized_symbol)
            .limit(1)
            .execute()
        )
        result = _first_row(response)
        get_market_data.last_error = None
        return result
    except Exception as error:
        get_market_data.last_error = error
        print(f"[MarketDataRepository][ERROR] fetching {normalized_symbol}: {error}")
        return None


def get_all_market_data():
    client = get_supabase_client()
    if client is None:
        return []

    try:
        response = client.table("market_data").select("*").execute()
        data = getattr(response, "data", None)
        get_all_market_data.last_error = None
        return data if isinstance(data, list) else []
    except Exception as error:
        get_all_market_data.last_error = error
        print(f"[MarketDataRepository][ERROR] fetching all market data: {error}")
        return []


def save_market_data(coin_data):
    normalized = dict(coin_data or {})
    symbol = _normalize_symbol(normalized.get("symbol"))
    print(f"[MarketDataRepository] saving {symbol or 'UNKNOWN'}")
    if not symbol:
        save_market_data.last_error = ValueError("missing symbol")
        return False

    client = get_supabase_client()
    if client is None:
        save_market_data.last_error = RuntimeError("missing supabase client")
        return False

    payload = {
        "symbol": symbol,
        "name": normalized.get("name"),
        "price_usd": normalized.get("price_usd"),
        "change_24h": normalized.get("change_24h"),
        "source": normalized.get("source"),
        "updated_at": normalized.get("updated_at"),
    }
    if "updated_by" in normalized:
        payload["updated_by"] = normalized.get("updated_by")

    try:
        existing = (
            client.table("market_data")
            .select("symbol")
            .eq("symbol", symbol)
            .limit(1)
            .execute()
        )
        if _first_row(existing) is not None:
            client.table("market_data").update(payload).eq("symbol", symbol).execute()
        else:
            client.table("market_data").insert(payload).execute()
    except Exception as error:
        save_market_data.last_error = error
        print(f"[MarketDataRepository][ERROR] saving {symbol}: {error}")
        return False

    save_market_data.last_error = None
    return True


def get_market_data_by_symbol(symbol):
    return get_market_data(symbol)


def upsert_market_data(coin_data):
    return save_market_data(coin_data)


get_market_data.last_error = None
get_all_market_data.last_error = None
save_market_data.last_error = None
