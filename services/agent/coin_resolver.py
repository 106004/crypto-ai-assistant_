"""Single coin parser for agent routing signals."""

from __future__ import annotations

import re

from services.agent.unsupported_coin_service import detect_unsupported_coin
from services.agent import semantic_resolver


GENERIC_TICKER_STOPWORDS = {
    "a",
    "about",
    "analysis",
    "and",
    "analyze",
    "are",
    "ask",
    "at",
    "by",
    "for",
    "from",
    "help",
    "how",
    "i",
    "in",
    "is",
    "me",
    "my",
    "of",
    "on",
    "or",
    "please",
    "price",
    "prices",
    "show",
    "tell",
    "the",
    "today",
    "what",
    "with",
}


def _normalize(message: str) -> str:
    return str(message or "").strip()


def _extract_generic_ticker(message: str) -> str | None:
    raw = _normalize(message)
    if not raw or re.search(r"\d", raw):
        return None

    candidates = re.findall(r"(?<![A-Za-z])[A-Za-z]{3,5}(?![A-Za-z])", raw)
    for candidate in candidates:
        ticker = candidate.strip().upper()
        if not ticker or ticker.lower() in GENERIC_TICKER_STOPWORDS:
            continue
        return ticker

    return None


def resolve_coin(message: str) -> dict[str, object]:
    """Parse coin signals from a raw message without deciding workflow."""

    raw = _normalize(message)
    if not raw:
        result = {
            "coin": None,
            "reason": "empty_message",
            "matched_keywords": [],
            "confidence": 0.0,
            "method": "none",
        }
        print("[CoinResolver] resolved coin: none")
        print("[CoinResolver] resolved: none")
        return result

    unsupported_alias = detect_unsupported_coin(raw)
    unsupported_coin = str(unsupported_alias.get("coin") or "").strip().upper()
    if unsupported_coin:
        result = {
            "coin": unsupported_coin,
            "reason": "nickname_normalized",
            "matched_keywords": [unsupported_coin],
            "confidence": float(unsupported_alias.get("confidence") or 0.0),
            "method": str(unsupported_alias.get("method") or "exact"),
        }
        print(f"[CoinResolver] resolved coin: {unsupported_coin}")
        print(f"[CoinResolver] resolved: {unsupported_coin}")
        return result

    semantic = semantic_resolver.resolve_coin_symbol(raw)
    semantic_coin = str(semantic.get("coin") or "").strip().upper()
    semantic_method = str(semantic.get("method") or "").strip().lower()
    if semantic_method == "fuzzy_candidates":
        result = {
            "coin": None,
            "reason": "fuzzy_candidates",
            "matched_keywords": [],
            "confidence": float(semantic.get("confidence") or 0.0),
            "method": semantic_method,
            "candidates": semantic.get("candidates") or [],
        }
        print("[CoinResolver] resolved coin: fuzzy_candidates")
        print("[CoinResolver] resolved: fuzzy_candidates")
        return result

    if semantic_method in {"exact_alias", "fuzzy"} and semantic_coin:
        result = {
            "coin": semantic_coin,
            "reason": semantic_method,
            "matched_keywords": [semantic_coin],
            "confidence": float(semantic.get("confidence") or 0.0),
            "method": semantic_method,
        }
        print(f"[CoinResolver] resolved coin: {semantic_coin}")
        print(f"[CoinResolver] resolved: {semantic_coin}")
        return result

    generic_ticker = _extract_generic_ticker(raw)
    if generic_ticker:
        print(f"[UnknownTickerExtractor] extracted ticker: {generic_ticker}")
        result = {
            "coin": generic_ticker,
            "reason": "ticker_extraction",
            "matched_keywords": [generic_ticker],
            "confidence": 0.5,
            "method": "generic",
        }
        print(f"[CoinResolver] resolved coin: {generic_ticker}")
        print(f"[CoinResolver] resolved: {generic_ticker}")
        return result

    result = {
        "coin": None,
        "reason": "no_coin",
        "matched_keywords": [],
        "confidence": 0.0,
        "method": "none",
    }
    print("[CoinResolver] resolved coin: none")
    print("[CoinResolver] resolved: none")
    return result
