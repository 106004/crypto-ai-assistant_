"""General coin validation helpers for agent tasks."""

from __future__ import annotations

import re

from services.agent.coin_aliases import COIN_ALIASES
from services.agent.unsupported_coin_service import UNSUPPORTED_COIN_ALIASES
from services.market.coin_catalog import SUPPORTED_COINS as COIN_CATALOG


SUPPORTED_COINS = {str(symbol).strip().upper() for symbol in COIN_CATALOG}
_SUPPORTED_ALIAS_BY_LOWER = {str(alias).strip().lower(): str(symbol).strip().upper() for alias, symbol in COIN_ALIASES.items()}
_UNSUPPORTED_ALIAS_BY_LOWER = {
    str(alias).strip().lower(): str(symbol).strip().upper()
    for alias, symbol in UNSUPPORTED_COIN_ALIASES.items()
}
VALID_COIN_INTENTS = {
    "price_query",
    "market_analysis",
    "set_favorite_coin",
    "unsupported_coin",
}


def _normalize_lookup_key(raw_coin: object) -> str:
    return re.sub(r"\s+", " ", str(raw_coin or "").strip()).lower()


def normalize_coin_symbol(raw_coin) -> str | None:
    """Normalize Gemini coin text into a canonical symbol when possible."""

    raw_text = re.sub(r"\s+", " ", str(raw_coin or "").strip())
    if not raw_text:
        return None

    upper_text = raw_text.upper()
    if re.fullmatch(r"[A-Z]{2,10}", upper_text):
        return upper_text

    lookup_key = _normalize_lookup_key(raw_text)
    supported_alias = _SUPPORTED_ALIAS_BY_LOWER.get(lookup_key)
    if supported_alias:
        return supported_alias

    unsupported_alias = _UNSUPPORTED_ALIAS_BY_LOWER.get(lookup_key)
    if unsupported_alias:
        return unsupported_alias

    return None


def normalize_llm_coin(raw_coin) -> dict[str, object]:
    """Normalize Gemini coin text into a canonical symbol when possible."""

    raw_text = re.sub(r"\s+", " ", str(raw_coin or "").strip())
    if not raw_text:
        return {
            "llm_raw_coin": None,
            "normalized_coin": None,
            "rejected_reason": "missing_coin",
        }

    normalized_coin = normalize_coin_symbol(raw_text)
    if normalized_coin is not None:
        return {
            "llm_raw_coin": raw_text,
            "normalized_coin": normalized_coin,
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
