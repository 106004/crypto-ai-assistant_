"""Clarification helpers for ambiguous agent intents."""

from __future__ import annotations

from difflib import get_close_matches

from services.agent.coin_aliases import COIN_ALIASES, SUPPORTED_COINS


EXTRA_CLARIFICATION_ALIASES = {
    "shib": "SHIB",
    "SHIB": "SHIB",
    "shiba inu": "SHIB",
    "柴犬幣": "SHIB",
    "柴犬币": "SHIB",
}

DISPLAY_NAMES = {
    "BTC": "比特幣",
    "ETH": "以太幣",
    "SOL": "Solana",
    "DOGE": "狗狗幣",
    "BNB": "幣安幣",
    "XRP": "瑞波幣",
    "ADA": "艾達幣",
    "TON": "電報幣",
    "TRX": "波場",
    "AVAX": "雪崩幣",
    "SHIB": "柴犬幣",
}

_CLARIFICATION_ALIAS_TO_SYMBOL = {
    **{alias.lower(): symbol for alias, symbol in COIN_ALIASES.items()},
    **{alias.lower(): symbol for alias, symbol in EXTRA_CLARIFICATION_ALIASES.items()},
}
_CLARIFICATION_ALIAS_VALUES = sorted(_CLARIFICATION_ALIAS_TO_SYMBOL.keys())
_SUPPORTED_COIN_ORDER = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "TON", "TRX", "AVAX"]
_SUPPORTED_COIN_CODES = " / ".join(symbol.lower() for symbol in _SUPPORTED_COIN_ORDER)


def _symbol_label(symbol: str) -> str:
    return DISPLAY_NAMES.get(symbol, symbol)


def suggest_clarification_candidates(message: str, max_candidates: int = 2) -> list[str]:
    """Suggest coin candidates for a clarification prompt."""

    raw = str(message or "").strip().lower()
    if not raw:
        return []

    candidates: list[str] = []
    for token in raw.replace("/", " ").split():
        matches = get_close_matches(token, _CLARIFICATION_ALIAS_VALUES, n=max_candidates, cutoff=0.55)
        for alias in matches:
            symbol = _CLARIFICATION_ALIAS_TO_SYMBOL.get(alias)
            if symbol and symbol not in candidates:
                candidates.append(symbol)
            if len(candidates) >= max_candidates:
                return candidates

    if not candidates:
        matches = get_close_matches(raw, _CLARIFICATION_ALIAS_VALUES, n=max_candidates, cutoff=0.55)
        for alias in matches:
            symbol = _CLARIFICATION_ALIAS_TO_SYMBOL.get(alias)
            if symbol and symbol not in candidates:
                candidates.append(symbol)
            if len(candidates) >= max_candidates:
                break

    return candidates[:max_candidates]


def build_clarification_payload(candidates: list[str], reason: str = "low_confidence") -> dict[str, object]:
    normalized_candidates = [
        str(candidate or "").strip().upper()
        for candidate in candidates
        if str(candidate or "").strip()
    ]
    unique_candidates = list(dict.fromkeys(normalized_candidates))
    return {
        "intent": "clarification_needed",
        "candidates": unique_candidates,
        "reason": reason,
    }


def build_clarification_message(candidates: list[str], reason: str = "low_confidence") -> str:
    """Build a user-facing clarification message."""

    unique_candidates = [
        str(candidate or "").strip().upper()
        for candidate in candidates
        if str(candidate or "").strip()
    ]
    unique_candidates = list(dict.fromkeys(unique_candidates))

    if not unique_candidates:
        return (
            "我還不確定你想查哪個幣。\n\n"
            f"目前支援：\n{_SUPPORTED_COIN_CODES}\n\n"
            "你可以輸入：\n"
            "btc\n"
            "analyze btc\n"
            "set btc"
        )

    lines = [
        "我不太確定你指的是哪個幣種。",
        "",
        "你是指：",
    ]
    for index, symbol in enumerate(unique_candidates, start=1):
        lines.append(f"{index}. {symbol} {_symbol_label(symbol)}")
    lines.append("")
    lines.append("請直接輸入幣種，例如：doge 或 btc。")

    if reason and reason != "low_confidence":
        lines.append(f"原因：{reason}")

    return "\n".join(lines)
