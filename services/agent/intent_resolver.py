"""Single intent parser for agent routing signals."""

from __future__ import annotations

import re


INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "market_analysis": (
        "analyze",
        "analysis",
        "分析",
        "看看",
        "研究",
        "怎麼樣",
        "怎麼看",
    ),
    "set_favorite_coin": (
        "set",
        "設定",
        "設成",
        "我的幣",
        "最愛",
    ),
    "price_query": (
        "price",
        "價格",
        "多少",
        "幾塊",
        "幾元",
    ),
    "help": (
        "help",
        "幫助",
        "指令",
        "怎麼用",
        "說明",
        "使用說明",
    ),
}

INTENT_PRIORITY = ("market_analysis", "set_favorite_coin", "price_query", "help")


def _normalize(message: str) -> str:
    return str(message or "").strip().lower()


def _contains_keyword(text: str, keyword: str) -> bool:
    if not keyword:
        return False
    if re.fullmatch(r"[a-z]+", keyword):
        return re.search(rf"\b{re.escape(keyword)}\b", text) is not None
    return keyword in text


def resolve_intent(message: str) -> dict[str, object]:
    """Parse intent signals from a raw message without making routing decisions."""

    normalized = _normalize(message)
    if not normalized:
        result = {
            "intent": "unknown",
            "reason": "empty_message",
            "matched_keywords": [],
            "matched_intents": [],
        }
        print("[IntentResolver] resolved intent: unknown")
        print("[IntentResolver] resolved: unknown")
        return result

    matched_keywords: list[str] = []
    matched_intents: list[str] = []

    for intent in INTENT_PRIORITY:
        keywords = INTENT_KEYWORDS[intent]
        hits = [keyword for keyword in keywords if _contains_keyword(normalized, keyword)]
        if not hits:
            continue
        matched_intents.append(intent)
        matched_keywords.extend(hits)

    if matched_intents:
        intent = matched_intents[0]
        reason = "multiple_keywords" if len(matched_intents) > 1 else f"{intent}_keyword"
    else:
        intent = "unknown"
        reason = "no_keywords"

    print(f"[IntentResolver] resolved intent: {intent}")
    print(f"[IntentResolver] resolved: {intent}")
    return {
        "intent": intent,
        "reason": reason,
        "matched_keywords": matched_keywords,
        "matched_intents": matched_intents,
    }
