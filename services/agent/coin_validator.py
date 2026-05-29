"""General coin validation helpers for agent tasks."""

from __future__ import annotations

from services.market.coin_catalog import SUPPORTED_COINS as COIN_CATALOG


SUPPORTED_COINS = {str(symbol).strip().upper() for symbol in COIN_CATALOG}
VALID_COIN_INTENTS = {
    "price_query",
    "market_analysis",
    "set_favorite_coin",
    "unsupported_coin",
}


def _normalize_coin(raw_coin) -> str:
    return str(raw_coin or "").strip().upper()


def _normalize_intent(raw_intent) -> str:
    return str(raw_intent or "").strip().lower()


def validate_coin_task(task: dict[str, object]) -> dict[str, object]:
    """Validate a single task and normalize unsupported coins."""

    normalized_task = dict(task or {})
    intent = _normalize_intent(normalized_task.get("intent"))
    coin = _normalize_coin(normalized_task.get("coin"))

    normalized_task["intent"] = intent or "unknown"
    normalized_task["coin"] = coin or None

    if not coin:
        return normalized_task

    if normalized_task["intent"] not in VALID_COIN_INTENTS:
        return normalized_task

    if coin in SUPPORTED_COINS:
        return normalized_task

    print(f"[CoinValidator] unsupported coin: {coin}")
    normalized_task["intent"] = "unsupported_coin"
    normalized_task["reason"] = "coin_not_supported"
    normalized_task["coin"] = coin
    return normalized_task
