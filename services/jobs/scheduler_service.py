"""Background job helpers for scheduled tasks."""

from __future__ import annotations

from data.clients.line_client import push_message
from data.repositories.market_data_repository import get_market_data_by_symbol
from data.repositories.user_repository import get_all_users
from services.market.collector_service import collect_market_data
from services.line.message_service import (
    format_coin_glass_link_message,
    format_daily_guide_message,
    format_missing_favorite_coin_message,
    format_price_message,
)
from services.market.freshness_service import is_market_data_fresh
from utils.logger import log_error, log_info, log_warning


def run_market_update_job(collector=None):
    log_info("MarketUpdateJob", "started")

    collector = collector or collect_market_data

    try:
        collector()
    except Exception as error:
        log_error("MarketUpdateJob", f"market update failed: {error}")
        raise

    log_info("MarketUpdateJob", "completed")
    return True


def run_daily_guide_job(get_users_fn=None, push_message_fn=None, guide_message_fn=None):
    get_users_fn = get_users_fn or get_all_users
    push_message_fn = push_message_fn or push_message
    guide_message_fn = guide_message_fn or format_daily_guide_message

    log_info("DailyGuideJob", "started")
    users = get_users_fn() or []
    log_info("DailyGuideJob", f"user count: {len(users)}")

    for user in users:
        user_id = str(user.get("line_user_id") or user.get("user_id") or "").strip()
        if not user_id:
            log_warning("DailyGuideJob", "skipping user without user_id")
            continue

        log_info("DailyGuideJob", f"pushing guide to user {user_id}")
        try:
            push_message_fn(user_id, guide_message_fn())
        except Exception as error:
            log_error("DailyGuideJob", f"push failed for {user_id}: {error}")

    log_info("DailyGuideJob", "completed")
    return True


def _build_favorite_coin_stale_message(symbol):
    return format_coin_glass_link_message(
        symbol,
        f"⚠️ {symbol} 價格資料超過 5 分鐘",
        "系統不會推播過期價格，避免誤導。",
    )


def run_favorite_coin_push_job(
    get_users_fn=None,
    get_market_data_by_symbol_fn=None,
    push_message_fn=None,
    is_market_data_fresh_fn=None,
    price_message_fn=None,
    missing_favorite_coin_message_fn=None,
):
    get_users_fn = get_users_fn or get_all_users
    get_market_data_by_symbol_fn = get_market_data_by_symbol_fn or get_market_data_by_symbol
    push_message_fn = push_message_fn or push_message
    is_market_data_fresh_fn = is_market_data_fresh_fn or is_market_data_fresh
    price_message_fn = price_message_fn or format_price_message
    missing_favorite_coin_message_fn = (
        missing_favorite_coin_message_fn or format_missing_favorite_coin_message
    )

    log_info("FavoriteCoinJob", "started")
    users = get_users_fn() or []
    log_info("FavoriteCoinJob", f"user count: {len(users)}")

    for user in users:
        user_id = str(user.get("line_user_id") or user.get("user_id") or "").strip()
        if not user_id:
            log_warning("FavoriteCoinJob", "skipping user without user_id")
            continue

        favorite_coin = str(user.get("favorite_coin") or "").strip().lower()
        if not favorite_coin:
            log_info("FavoriteCoinJob", f"missing favorite coin for user {user_id}")
            try:
                push_message_fn(user_id, missing_favorite_coin_message_fn())
                log_info("FavoriteCoinJob", "push completed")
            except Exception as error:
                log_error("FavoriteCoinJob", f"push failed for {user_id}: {error}")
            continue

        symbol = favorite_coin.upper()
        log_info("FavoriteCoinJob", f"pushing {symbol} to user {user_id}")

        try:
            coin_data = get_market_data_by_symbol_fn(symbol)
        except Exception as error:
            log_error("FavoriteCoinJob", f"market data fetch failed for {symbol}: {error}")
            coin_data = None

        if not isinstance(coin_data, dict):
            log_info("FavoriteCoinJob", f"{symbol} stale, pushing CoinGlass link")
            try:
                push_message_fn(user_id, _build_favorite_coin_stale_message(symbol))
                log_info("FavoriteCoinJob", "push completed")
            except Exception as error:
                log_error("FavoriteCoinJob", f"push failed for {user_id}: {error}")
            continue

        try:
            fresh = is_market_data_fresh_fn(coin_data)
        except Exception as error:
            log_error("FavoriteCoinJob", f"freshness check failed for {symbol}: {error}")
            fresh = False

        if not fresh:
            log_info("FavoriteCoinJob", f"{symbol} stale, pushing CoinGlass link")
            try:
                push_message_fn(user_id, _build_favorite_coin_stale_message(symbol))
                log_info("FavoriteCoinJob", "push completed")
            except Exception as error:
                log_error("FavoriteCoinJob", f"push failed for {user_id}: {error}")
            continue

        try:
            push_message_fn(user_id, price_message_fn(coin_data))
            log_info("FavoriteCoinJob", "push completed")
        except Exception as error:
            log_error("FavoriteCoinJob", f"push failed for {user_id}: {error}")

    log_info("FavoriteCoinJob", "completed")
    return True


def run_favorite_coin_job(
    get_users_fn=None,
    get_market_data_by_symbol_fn=None,
    push_message_fn=None,
    is_market_data_fresh_fn=None,
    price_message_fn=None,
    missing_favorite_coin_message_fn=None,
):
    return run_favorite_coin_push_job(
        get_users_fn=get_users_fn,
        get_market_data_by_symbol_fn=get_market_data_by_symbol_fn,
        push_message_fn=push_message_fn,
        is_market_data_fresh_fn=is_market_data_fresh_fn,
        price_message_fn=price_message_fn,
        missing_favorite_coin_message_fn=missing_favorite_coin_message_fn,
    )
