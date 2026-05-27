"""Decision engine scaffold.

Future role: decide what the user likely wants to do.
This first version is rule-based only and uses an LLM fallback only when
the message remains ambiguous after semantic coin resolution.
"""

from __future__ import annotations

import re
from typing import Dict

from services.agent import semantic_resolver
from services.agent.clarification_service import (
    build_clarification_payload,
    suggest_clarification_candidates,
)
from services.agent.unsupported_coin_service import (
    build_unsupported_coin_payload,
    detect_unsupported_coin,
)
from services.agent.llm_intent_classifier import classify_with_llm


SUPPORTED_COINS = {
    "BTC",
    "ETH",
    "SOL",
    "DOGE",
    "BNB",
    "XRP",
    "ADA",
    "TON",
    "TRX",
    "AVAX",
}
ALLOWED_LLM_INTENTS = {
    "price_query",
    "market_analysis",
    "set_favorite_coin",
    "get_favorite_coin",
    "help",
    "unknown",
}
CONTEXT_ALLOWED_PREVIOUS_INTENTS = {"price_query", "market_analysis"}
HELP_MESSAGES = {"help", "/help", "說明", "使用說明", "幫助"}
PRICE_HINTS = {"price", "價格", "多少", "幣價", "現價", "現在", "多少錢"}
ANALYSIS_HINTS = {"analyze", "analysis", "分析", "看一下", "看", "評估", "走勢", "風險", "趨勢", "危險"}
SET_HINTS = {"set", "設成", "設定", "最愛"}
FAVORITE_HINTS = {"mycoin", "最愛的幣", "我最愛的幣", "favorite", "我的幣"}
AMBIGUOUS_HINTS = {
    "幫我看一下",
    "看一下",
    "幫我看",
    "怎麼樣",
    "會不會",
    "能不能",
    "值得嗎",
    "還能",
    "漲嗎",
    "跌嗎",
}


def _build_result(intent: str, coin: str = "", confidence: float = 0.1) -> Dict[str, object]:
    return {
        "intent": intent,
        "coin": coin,
        "confidence": confidence,
    }


def _tokenize(message: str) -> list[str]:
    """Turn a message into simple alpha tokens."""

    return re.findall(r"[a-zA-Z]+", message or "")


def _normalize_text(message: str) -> str:
    return str(message or "").strip().lower().replace("/", " ").strip()


def _is_context_message(text: str) -> bool:
    normalized = text.strip()
    if not normalized:
        return False
    return normalized.startswith(("那", "這", "再", "還", "請問")) or normalized.endswith(("呢", "嗎", "啊", "?"))


def _should_infer_from_state(previous_intent: str) -> bool:
    return previous_intent in CONTEXT_ALLOWED_PREVIOUS_INTENTS


def _extract_rule_based_intent(
    normalized: str,
    tokens: list[str],
    resolved_coin: str,
    previous_intent: str,
) -> dict[str, object] | None:
    if normalized in HELP_MESSAGES or "help" in tokens:
        return _build_result("help", confidence=0.9)

    if any(hint in normalized for hint in FAVORITE_HINTS):
        return _build_result("get_favorite_coin", confidence=0.9)

    if _is_context_message(normalized):
        if resolved_coin and _should_infer_from_state(previous_intent):
            return _build_result(previous_intent, coin=resolved_coin, confidence=0.8)
        if resolved_coin:
            return _build_result("unknown")
        return None

    if any(hint in normalized for hint in SET_HINTS):
        if resolved_coin:
            return _build_result("set_favorite_coin", coin=resolved_coin, confidence=0.9)
        return None

    if any(hint in normalized for hint in ANALYSIS_HINTS):
        if resolved_coin and not any(hint in normalized for hint in AMBIGUOUS_HINTS):
            return _build_result("market_analysis", coin=resolved_coin, confidence=0.9)
        if resolved_coin:
            return None
        return None

    if any(hint in normalized for hint in PRICE_HINTS):
        if resolved_coin:
            return _build_result("price_query", coin=resolved_coin, confidence=0.9)
        return None

    if resolved_coin and not any(hint in normalized for hint in AMBIGUOUS_HINTS):
        return _build_result("price_query", coin=resolved_coin, confidence=0.9)

    return None


def _accept_llm_result(result: dict[str, object]) -> dict[str, object]:
    intent = str(result.get("intent") or "unknown").strip().lower()
    coin = str(result.get("coin") or "").strip().upper()
    confidence = float(result.get("confidence") or 0.0)

    if intent not in ALLOWED_LLM_INTENTS:
        return _build_result("unknown")

    if coin and coin not in SUPPORTED_COINS:
        return _build_result("unknown")

    if confidence < 0.75:
        return _build_result("unknown")

    if intent == "unknown":
        return _build_result("unknown", coin=coin, confidence=confidence)

    return _build_result(intent, coin=coin, confidence=confidence)


def _build_clarification_result(
    message: str,
    candidates: list[dict[str, object]] | None = None,
) -> dict[str, object] | None:
    llm_result = classify_with_llm(message, candidates=candidates)
    llm_reason = str(llm_result.get("reason") or "").strip().lower()
    llm_intent = str(llm_result.get("intent") or "").strip().lower()

    if llm_intent == "unsupported_coin" or llm_reason == "coin_not_supported":
        return llm_result

    if llm_intent == "clarification_needed" or llm_reason in {"low_confidence", "candidate_mismatch"}:
        clarification_candidates = candidates or suggest_clarification_candidates(message)
        if not clarification_candidates:
            print("[Clarification] clarification triggered")
            print("[Clarification] candidates suggested")
            return None

        print("[Clarification] clarification triggered")
        print(f"[Clarification] candidates suggested: {clarification_candidates}")
        reason = "candidate_mismatch" if llm_reason == "candidate_mismatch" else "low_confidence"
        return build_clarification_payload(clarification_candidates, reason=reason)

    accepted = _accept_llm_result(llm_result)
    if accepted.get("intent") != "unknown" or accepted.get("coin"):
        return accepted

    return None


def _build_unsupported_coin_result(message: str) -> dict[str, object] | None:
    unsupported = detect_unsupported_coin(message)
    coin = str(unsupported.get("coin") or "").strip().upper()
    if not coin:
        return None

    print(f"[UnsupportedCoin] unsupported coin detected coin={coin}")
    return build_unsupported_coin_payload(coin, reason="coin_not_supported")


def decide_user_intent(message: str, user_state: dict | None = None):
    """Classify a user message into a simple intent dictionary."""

    raw_text = str(message or "").strip()
    if not raw_text:
        return _build_result("unknown")

    coin_resolution = semantic_resolver.resolve_coin_symbol(raw_text)
    resolved_coin = str(coin_resolution.get("coin") or "").strip().upper()
    resolution_method = str(coin_resolution.get("method") or "").strip().lower()
    resolution_candidates = coin_resolution.get("candidates")
    normalized = _normalize_text(raw_text)
    tokens = _tokenize(normalized)
    previous_intent = str((user_state or {}).get("last_intent") or "").strip().lower()

    rule_based = _extract_rule_based_intent(normalized, tokens, resolved_coin, previous_intent)
    if rule_based is not None:
        return rule_based

    if resolution_method == "fuzzy_candidates":
        fuzzy_result = _build_clarification_result(raw_text, candidates=resolution_candidates)
        if fuzzy_result is not None:
            return fuzzy_result

    unsupported_coin_result = _build_unsupported_coin_result(raw_text)
    if unsupported_coin_result is not None:
        return unsupported_coin_result

    clarification_result = _build_clarification_result(raw_text)
    if clarification_result is not None:
        return clarification_result

    return _build_result("unknown")
