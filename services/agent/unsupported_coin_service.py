"""Unsupported coin helpers for the agent layer."""

from __future__ import annotations

import re
from difflib import SequenceMatcher, get_close_matches


SUPPORTED_COIN_CODES = [
    "BTC",
    "ETH",
    "SOL",
    "BNB",
    "XRP",
    "DOGE",
    "ADA",
    "TON",
    "TRX",
    "AVAX",
]

UNSUPPORTED_COIN_ALIASES = {
    "trump": "TRUMP",
    "TRUMP": "TRUMP",
    "trump coin": "TRUMP",
    "川普幣": "TRUMP",
    "川普币": "TRUMP",
    "shib": "SHIB",
    "SHIB": "SHIB",
    "shiba inu": "SHIB",
    "柴犬幣": "SHIB",
    "柴犬币": "SHIB",
    "floki": "FLOKI",
    "FLOKI": "FLOKI",
    "bonk": "BONK",
    "BONK": "BONK",
    "pepe": "PEPE",
    "PEPE": "PEPE",
    "pepe coin": "PEPE",
    "pepe幣": "PEPE",
    "pepe币": "PEPE",
}

_ALIASES_BY_LOWER = {alias.lower(): symbol for alias, symbol in UNSUPPORTED_COIN_ALIASES.items()}
_ALIASES = sorted({alias.lower() for alias in UNSUPPORTED_COIN_ALIASES})
_SUPPORTED_COIN_TEXT = " / ".join(SUPPORTED_COIN_CODES)


def _build_none_result() -> dict[str, object]:
    return {"coin": None, "confidence": 0.0, "method": "none"}


def _tokenize_candidates(message: str) -> list[str]:
    raw = str(message or "").strip()
    if not raw:
        return []

    candidates = [raw.lower()]
    candidates.extend(
        token.lower()
        for token in re.findall(r"[A-Za-z\u4e00-\u9fff]+", raw)
        if token.strip()
    )
    return list(dict.fromkeys(candidate.strip() for candidate in candidates if candidate.strip()))


def _score_fuzzy(candidate: str, alias: str) -> float:
    ratio = SequenceMatcher(None, candidate, alias).ratio()
    return round(min(1.0, max(0.0, ratio)), 3)


def detect_unsupported_coin(message: str) -> dict[str, object]:
    """Return an unsupported coin match if the message clearly refers to one."""

    raw = str(message or "").strip()
    if not raw:
        return _build_none_result()

    lowered = raw.lower()
    for alias_lower, symbol in sorted(_ALIASES_BY_LOWER.items(), key=lambda item: len(item[0]), reverse=True):
        if re.fullmatch(r"[A-Za-z ]+", alias_lower):
            pattern = rf"(?<![A-Za-z0-9]){re.escape(alias_lower)}(?![A-Za-z0-9])"
            if re.search(pattern, lowered):
                return {"coin": symbol, "confidence": 1.0, "method": "exact"}
        else:
            if alias_lower in lowered:
                return {"coin": symbol, "confidence": 1.0, "method": "exact"}

    candidates = _tokenize_candidates(raw)
    for candidate in candidates:
        matches = get_close_matches(candidate, _ALIASES, n=1, cutoff=0.72)
        if not matches:
            continue
        alias_lower = matches[0]
        symbol = _ALIASES_BY_LOWER.get(alias_lower)
        if symbol is None:
            continue
        confidence = _score_fuzzy(candidate, alias_lower)
        if confidence >= 0.85:
            return {"coin": symbol, "confidence": confidence, "method": "fuzzy"}

    return _build_none_result()


def build_unsupported_coin_payload(coin: str, reason: str = "coin_not_supported") -> dict[str, object]:
    normalized_coin = str(coin or "").strip().upper()
    return {
        "intent": "unsupported_coin",
        "coin": normalized_coin or None,
        "reason": reason,
    }


def build_unsupported_coin_message(coin: str) -> str:
    normalized_coin = str(coin or "").strip().upper() or "UNKNOWN"
    return (
        f"目前我還不能查詢或分析 {normalized_coin}。\n\n"
        f"目前只支援：\n{_SUPPORTED_COIN_TEXT}\n\n"
        "你可以輸入：\n"
        "btc\n"
        "analyze eth\n"
        "set sol"
    )
