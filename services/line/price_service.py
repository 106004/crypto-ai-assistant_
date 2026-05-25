"""LINE price query flow."""

from __future__ import annotations

from datetime import datetime, timezone

from data.repositories.market_data_repository import get_market_data_by_symbol  # compatibility alias
from services.line.message_service import format_price_message, format_stale_data_message
from services.market.coin_catalog import get_coinglass_url
from services.market.freshness_service import is_market_data_fresh


def _parse_market_data_updated_at_utc(updated_at):
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


def _check_supabase_market_data_freshness(symbol, updated_at, now_utc=None):
    now_utc = now_utc or datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    else:
        now_utc = now_utc.astimezone(timezone.utc)

    print(f"[Freshness] {symbol} updated_at 值：{updated_at}")
    updated_time = _parse_market_data_updated_at_utc(updated_at)
    age_seconds = max(0, (now_utc - updated_time).total_seconds())
    age_minutes = age_seconds / 60
    fresh = age_seconds <= 300

    print(f"[Freshness] {symbol} parsed updated_at UTC：{updated_time.isoformat()}")
    print(f"[Freshness] 現在 UTC：{now_utc.isoformat()}")
    print(f"[Freshness] 資料年齡：{age_minutes:.1f} 分鐘")
    print("[Freshness] freshness limit：5 分鐘")
    print(f"[Freshness] fresh：{fresh}")

    if fresh:
        print(f"[Freshness] {symbol} 資料新鮮，年齡 {age_minutes:.1f} 分鐘")
    else:
        print(
            f"[Freshness] {symbol} 資料過期，年齡 {age_minutes:.1f} 分鐘，"
            "不會回覆舊價格"
        )

    return {
        "fresh": fresh,
        "age_seconds": age_seconds,
        "age_minutes": age_minutes,
        "updated_at_utc": updated_time,
        "now_utc": now_utc,
    }


def get_fresh_market_data(symbol, now_utc=None, get_market_data_by_symbol_fn=None):
    display_symbol = str(symbol).strip().upper()
    get_market_data_by_symbol_fn = get_market_data_by_symbol_fn or get_market_data_by_symbol

    market_data = get_market_data_by_symbol_fn(display_symbol)
    if not isinstance(market_data, dict):
        print(f"[Freshness] {display_symbol} Supabase 沒有資料，走 CoinGlass fallback links")
        return None

    try:
        freshness = _check_supabase_market_data_freshness(
            display_symbol,
            market_data.get("updated_at"),
            now_utc=now_utc,
        )
    except (TypeError, ValueError) as error:
        print(f"[Freshness] {display_symbol} updated_at 解析失敗：{error}")
        print(
            f"[Freshness] {display_symbol} 資料視為過期，避免使用無法判斷時間的資料"
        )
        return None

    if not freshness["fresh"]:
        return None

    result = dict(market_data)
    result["source"] = "Supabase"
    result["_age_minutes"] = freshness["age_minutes"]
    return result


def handle_price_query(symbol, get_market_data_by_symbol_fn=None, now_utc=None):
    display_symbol = str(symbol).strip().upper()
    print(f"[PriceService] start query {display_symbol}")

    market_data = get_fresh_market_data(
        display_symbol,
        now_utc=now_utc,
        get_market_data_by_symbol_fn=get_market_data_by_symbol_fn,
    )

    if not isinstance(market_data, dict):
        print("[PriceService] CoinGlass fallback")
        return format_stale_data_message(display_symbol, get_coinglass_url(display_symbol))

    print("[PriceService] market_data found")
    fresh = is_market_data_fresh(market_data)
    print(f"[PriceService] freshness: {fresh}")
    if not fresh:
        print("[PriceService] CoinGlass fallback")
        return format_stale_data_message(display_symbol, get_coinglass_url(display_symbol))

    return format_price_message(market_data)
