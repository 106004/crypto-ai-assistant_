"""General coin validation helpers for agent tasks."""

from __future__ import annotations

import re

from services.agent.coin_aliases import normalize_coin_alias
from services.agent.unsupported_coin_service import detect_unsupported_coin
from services.market.coin_catalog import SUPPORTED_COINS as COIN_CATALOG


SUPPORTED_COINS = {str(symbol).strip().upper() for symbol in COIN_CATALOG}
VALID_COIN_INTENTS = {
    "price_query",
    "market_analysis",
    "set_favorite_coin",
    "unsupported_coin",
}


def normalize_llm_coin(raw_coin) -> dict[str, object]:
    """Normalize Gemini coin text into a canonical symbol when possible."""

    raw_text = str(raw_coin or "").strip()
    if not raw_text:
        return {
            "llm_raw_coin": None,
            "normalized_coin": None,
            "rejected_reason": "missing_coin",
        }

    supported_normalized = normalize_coin_alias(raw_text)
    if supported_normalized in SUPPORTED_COINS:
        return {
            "llm_raw_coin": raw_text,
            "normalized_coin": supported_normalized,
            "rejected_reason": None,
        }

    unsupported = detect_unsupported_coin(raw_text)
    unsupported_coin = str(unsupported.get("coin") or "").strip().upper() or None
    if unsupported_coin:
        return {
            "llm_raw_coin": raw_text,
            "normalized_coin": unsupported_coin,
            "rejected_reason": None,
        }

    if re.fullmatch(r"[A-Z]{2,10}", raw_text):
        return {
            "llm_raw_coin": raw_text,
            "normalized_coin": raw_text,
            "rejected_reason": None,
        }

    return {
        "llm_raw_coin": raw_text,
        "normalized_coin": None,
        "rejected_reason": "non_symbol_raw_text",
    }


def _normalize_intent(raw_intent) -> str:
    return str(raw_intent or "").strip().lower()


def validate_coin_task(task: dict[str, object]) -> dict[str, object]:
    """Validate a single task and normalize unsupported coins."""

    normalized_task = dict(task or {})
    intent = _normalize_intent(normalized_task.get("intent"))
    coin_info = normalize_llm_coin(normalized_task.get("coin"))
    coin = str(coin_info.get("normalized_coin") or "").strip().upper() or None

    normalized_task["intent"] = intent or "unknown"
    normalized_task["coin"] = coin or None

    if not coin:
        if coin_info.get("llm_raw_coin") and coin_info.get("rejected_reason"):
            normalized_task["intent"] = "clarification_needed"
            normalized_task["reason"] = str(coin_info.get("rejected_reason") or "non_symbol_raw_text")
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
