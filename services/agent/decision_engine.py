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
from services.market.coin_catalog import is_supported_coin


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

MULTI_INTENT_HINTS = {
    "並",
    "以及",
    "還有",
    "順便",
    "跟",
    "再",
    "also",
    "and",
}

FAST_PATH_SINGLE_WORD_COMMANDS = {"btc", "eth", "sol", "mycoin", "help"}
FAST_PATH_TWO_WORD_COMMANDS = {
    ("set", "btc"),
    ("analyze", "btc"),
}
NATURAL_LANGUAGE_HINTS = {
    "請",
    "今天",
    "幫我",
    "看看",
    "怎麼樣",
    "告訴我",
    "我最愛",
    "最愛貨幣",
    "分析一下",
}
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


def is_potential_multi_intent(message: str) -> bool:
    normalized = _normalize_text(message)
    if not normalized:
        return False

    for hint in MULTI_INTENT_HINTS:
        if hint in {"also", "and"}:
            if re.search(rf"\b{re.escape(hint)}\b", normalized):
                return True
            continue
        if hint in normalized:
            return True
    return False


def is_fast_path_command(message: str) -> bool:
    normalized = _normalize_text(message)
    if not normalized:
        return False

    collapsed = " ".join(normalized.split())
    if collapsed in FAST_PATH_SINGLE_WORD_COMMANDS:
        return True

    tokens = collapsed.split()
    if len(tokens) == 1:
        coin_resolution = semantic_resolver.resolve_coin_symbol(collapsed)
        if str(coin_resolution.get("coin") or "").strip().upper():
            return True

        unsupported = detect_unsupported_coin(collapsed)
        if str(unsupported.get("coin") or "").strip().upper():
            return True

    if len(tokens) == 2 and tuple(tokens) in FAST_PATH_TWO_WORD_COMMANDS:
        return True

    if len(tokens) == 2 and tokens[0] in {"set", "analyze"}:
        coin_text = tokens[1]
        coin_resolution = semantic_resolver.resolve_coin_symbol(coin_text)
        if str(coin_resolution.get("coin") or "").strip().upper():
            return True

        unsupported = detect_unsupported_coin(coin_text)
        if str(unsupported.get("coin") or "").strip().upper():
            return True

    return False


def is_natural_language(message: str) -> bool:
    normalized = _normalize_text(message)
    if not normalized or is_fast_path_command(message):
        return False

    if re.search(r"[?？]", message or ""):
        return True

    if is_potential_multi_intent(normalized):
        return True

    if any(hint in normalized for hint in NATURAL_LANGUAGE_HINTS):
        return True

    if re.search(r"[\u4e00-\u9fff]", message or ""):
        return True

    tokens = _tokenize(normalized)
    if len(tokens) >= 3:
        english_hints = {"please", "analyze", "analysis", "tell", "look", "how"}
        if any(token in english_hints for token in tokens):
            return True

    return False


def _extract_generic_ticker(message: str) -> str | None:
    normalized = str(message or "").strip()
    if not normalized:
        return None

    candidates = re.findall(r"[A-Za-z]{3,10}", normalized)
    for candidate in reversed(candidates):
        ticker = candidate.strip().upper()
        if not ticker or ticker.lower() in GENERIC_TICKER_STOPWORDS:
            continue
        print(f"[UnknownTickerExtractor] extracted ticker: {ticker}")
        return ticker

    return None


def _apply_generic_ticker_extraction(
    message: str,
    llm_result: dict[str, object],
) -> dict[str, object] | None:
    intent = str(llm_result.get("intent") or "").strip().lower()
    tasks = llm_result.get("tasks")

    task_list: list[dict[str, object]] = []
    if isinstance(tasks, list):
        task_list = [dict(task or {}) for task in tasks]

    needs_ticker = False
    if task_list:
        for task in task_list:
            task_intent = str((task or {}).get("intent") or "").strip().lower()
            task_coin = str((task or {}).get("coin") or "").strip().upper()
            if task_intent in {"price_query", "market_analysis"} and not task_coin:
                needs_ticker = True
                break
    elif intent in {"price_query", "market_analysis"} and not str(llm_result.get("coin") or "").strip():
        needs_ticker = True

    if not needs_ticker:
        return llm_result

    extracted_ticker = _extract_generic_ticker(message)
    if not extracted_ticker:
        return llm_result

    if not is_supported_coin(extracted_ticker.lower()):
        print("[DecisionEngine] route -> unsupported_coin")
        return build_unsupported_coin_payload(extracted_ticker, reason="coin_not_supported")

    if task_list:
        enriched_tasks = []
        for task in task_list:
            enriched_task = dict(task)
            task_intent = str(enriched_task.get("intent") or "").strip().lower()
            task_coin = str(enriched_task.get("coin") or "").strip().upper()
            if task_intent in {"price_query", "market_analysis"} and not task_coin:
                enriched_task["coin"] = extracted_ticker
            enriched_tasks.append(enriched_task)

        updated_result = dict(llm_result)
        updated_result["tasks"] = enriched_tasks
        if len(enriched_tasks) == 1:
            updated_result["intent"] = str(enriched_tasks[0].get("intent") or "unknown").strip().lower()
            updated_result["coin"] = str(enriched_tasks[0].get("coin") or extracted_ticker).strip().upper()
        return updated_result

    updated_result = dict(llm_result)
    updated_result["coin"] = extracted_ticker
    return updated_result


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
    print(f"[DecisionEngine] classifier_result:\n{llm_result}")
    llm_tasks = llm_result.get("tasks")
    if isinstance(llm_tasks, list) and llm_tasks:
        print(f"[DecisionEngine] multi-intent tasks received: {llm_tasks}")
        print("[DecisionEngine] tasks detected")
        return llm_result
    print("[DecisionEngine] fallback to single-intent path")
    llm_reason = str(llm_result.get("reason") or "").strip().lower()
    llm_intent = str(llm_result.get("intent") or "").strip().lower()

    if llm_intent == "unsupported_coin" or llm_reason == "coin_not_supported":
        print("[DecisionEngine] route -> unsupported_coin")
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
    print("[DecisionEngine] route -> unsupported_coin")
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

    if is_fast_path_command(raw_text):
        print("[DecisionEngine] fast-path command")
        rule_based = _extract_rule_based_intent(normalized, tokens, resolved_coin, previous_intent)
        if rule_based is not None:
            return rule_based
        print("[DecisionEngine] LLM failed, fallback to rule-based")
    else:
        if is_natural_language(raw_text):
            print("[DecisionEngine] natural-language detected")
        print("[DecisionEngine] routing to LLM-first path")
        llm_result = classify_with_llm(raw_text)
        llm_result = _apply_generic_ticker_extraction(raw_text, llm_result)
        if str(llm_result.get("intent") or "").strip().lower() == "unsupported_coin":
            return llm_result
        llm_tasks = llm_result.get("tasks")
        if isinstance(llm_tasks, list) and llm_tasks:
            if len(llm_tasks) >= 2:
                print("[DecisionEngine] multi-intent tasks accepted")
            return llm_result

        accepted_llm_result = _accept_llm_result(llm_result)
        if accepted_llm_result.get("intent") != "unknown" or accepted_llm_result.get("coin"):
            return accepted_llm_result

        print("[DecisionEngine] LLM failed, fallback to rule-based")
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
