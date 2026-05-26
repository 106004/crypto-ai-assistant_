"""Decision engine scaffold.

Future role: decide what the user likely wants to do.
This first version is rule-based only and does not use Gemini or any LLM.
"""

from __future__ import annotations

import re
from typing import Dict


SUPPORTED_COINS = {"BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "TON", "TRX", "AVAX"}
CONTEXT_ALLOWED_PREVIOUS_INTENTS = {"price_query", "market_analysis"}
HELP_MESSAGES = {"help", "/help", "說明", "使用說明", "隤芣?", "雿輻隤芣?"}


def _build_result(intent: str, coin: str = "", confidence: float = 0.1) -> Dict[str, object]:
    return {
        "intent": intent,
        "coin": coin,
        "confidence": confidence,
    }


def _tokenize(message: str) -> list[str]:
    """Turn a message into simple alpha tokens.

    We only need a lightweight tokenizer for rule-based intent checks.
    """

    return re.findall(r"[a-zA-Z]+", message or "")


def _extract_coin(tokens: list[str]) -> str:
    for token in tokens:
        coin = token.upper()
        if coin in SUPPORTED_COINS:
            return coin
    return ""


def _is_context_message(text: str) -> bool:
    """Detect short follow-up phrases that rely on prior conversation."""

    normalized = text.strip()
    if not normalized:
        return False
    return normalized.startswith("那") or normalized.endswith("呢")


def _should_infer_from_state(previous_intent: str) -> bool:
    return previous_intent in CONTEXT_ALLOWED_PREVIOUS_INTENTS


def decide_user_intent(message: str, user_state: dict | None = None):
    """Classify a user message into a simple intent dictionary.

    This version is still rule-based, but it can also look at the previous
    user state to resolve vague follow-up messages like "那 ETH 呢".
    """

    text = str(message or "").strip().lower()
    if not text:
        return _build_result("unknown")

    normalized = text.replace("/", " ").strip()
    tokens = _tokenize(normalized)
    first_token = tokens[0] if tokens else ""
    previous_intent = str((user_state or {}).get("last_intent") or "").strip().lower()

    if normalized in HELP_MESSAGES:
        return _build_result("help", confidence=0.9)

    if normalized == "mycoin":
        return _build_result("get_favorite_coin", confidence=0.9)

    if first_token == "set" and len(tokens) >= 2:
        coin = tokens[1].upper()
        if coin in SUPPORTED_COINS:
            return _build_result("set_favorite_coin", coin=coin, confidence=0.9)
        return _build_result("unknown")

    if first_token == "analyze" and len(tokens) >= 2:
        coin = tokens[1].upper()
        if coin in SUPPORTED_COINS:
            return _build_result("market_analysis", coin=coin, confidence=0.9)
        return _build_result("unknown")

    if _is_context_message(normalized):
        coin = _extract_coin(tokens)
        if coin and _should_infer_from_state(previous_intent):
            return _build_result(previous_intent, coin=coin, confidence=0.8)
        if coin:
            return _build_result("unknown")

    if normalized in {coin.lower() for coin in SUPPORTED_COINS}:
        return _build_result("price_query", coin=normalized.upper(), confidence=0.9)

    if first_token.upper() in SUPPORTED_COINS:
        return _build_result("price_query", coin=first_token.upper(), confidence=0.5)

    if any(token.upper() in SUPPORTED_COINS for token in tokens):
        coin = _extract_coin(tokens)
        if coin:
            if "analyze" in tokens and len(tokens) > 1:
                return _build_result("market_analysis", coin=coin, confidence=0.5)
            return _build_result("price_query", coin=coin, confidence=0.5)

    if "help" in tokens or normalized in {"說明", "使用說明", "隤芣?", "雿輻隤芣?"}:
        return _build_result("help", confidence=0.5)

    return _build_result("unknown")
