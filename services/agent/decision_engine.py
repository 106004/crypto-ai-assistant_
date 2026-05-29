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
from services.agent.coin_validator import validate_coin_task
from services.agent.coin_resolver import resolve_coin
from services.agent.intent_resolver import resolve_intent
from services.agent.llm_intent_classifier import classify_with_llm
from services.agent.unsupported_coin_service import detect_unsupported_coin
from services.market.coin_catalog import is_supported_coin


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


def _is_ascii_text(text: str) -> bool:
    return all(ord(char) < 128 for char in str(text or ""))


def _is_plain_single_token_message(message: str) -> bool:
    tokens = str(message or "").strip().split()
    return len(tokens) == 1 and bool(tokens[0])


def _should_attempt_llm_first(
    raw_text: str,
    intent_signal: dict[str, object],
    coin_signal: dict[str, object],
) -> bool:
    intent = str(intent_signal.get("intent") or "unknown").strip().lower()
    reason = str(intent_signal.get("reason") or "").strip().lower()
    matched_intents = [
        str(item or "").strip().lower()
        for item in (intent_signal.get("matched_intents") or [])
        if str(item or "").strip()
    ]
    coin = str(coin_signal.get("coin") or "").strip().upper()
    method = str(coin_signal.get("method") or "").strip().lower()
    token_count = len(str(raw_text or "").strip().split())

    if intent == "help":
        return False

    if reason == "multiple_keywords" or len(matched_intents) > 1:
        return True

    if method == "fuzzy_candidates":
        return True

    if not coin:
        return not _is_ascii_text(raw_text)

    if _is_plain_single_token_message(raw_text) and _is_ascii_text(raw_text):
        return False

    if not _is_ascii_text(raw_text):
        return True

    if token_count > 1 and not is_supported_coin(coin.lower()):
        return True

    return False


def _build_unsupported_coin_result(
    result: dict[str, object],
) -> dict[str, object]:
    payload = {
        "intent": "unsupported_coin",
        "coin": str(result.get("coin") or "").strip().upper(),
        "reason": "coin_not_supported",
    }

    if "tasks" in result:
        payload["tasks"] = result.get("tasks")

    confidence = result.get("confidence")
    if confidence is not None:
        try:
            payload["confidence"] = float(confidence)
        except (TypeError, ValueError):
            pass

    return payload


def _validate_task_list_result(result: dict[str, object]) -> dict[str, object]:
    tasks = result.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        return result

    validated_tasks = [validate_coin_task(dict(task or {})) for task in tasks]
    updated_result = dict(result)
    updated_result["tasks"] = [
        {
            "intent": str(task.get("intent") or "unknown").strip().lower(),
            "coin": task.get("coin"),
        }
        for task in validated_tasks
    ]

    primary_task = updated_result["tasks"][0]
    updated_result["intent"] = str(primary_task.get("intent") or "unknown").strip().lower()
    updated_result["coin"] = str(primary_task.get("coin") or "").strip().upper() or None

    if len(updated_result["tasks"]) == 1 and updated_result["intent"] == "unsupported_coin":
        updated_result["reason"] = "coin_not_supported"
        return _build_unsupported_coin_result(updated_result)

    if len(updated_result["tasks"]) > 1:
        updated_result["reason"] = "multi_intent_tasks"

    return updated_result


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

    if len(tokens) == 2 and tuple(tokens) in FAST_PATH_TWO_WORD_COMMANDS:
        return True

    if len(tokens) == 2 and tokens[0] in {"set", "analyze"}:
        coin_text = tokens[1]
        coin_resolution = semantic_resolver.resolve_coin_symbol(coin_text)
        if str(coin_resolution.get("coin") or "").strip().upper():
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


def _extract_generic_coin_candidate(message: str) -> str | None:
    raw = str(message or "").strip()
    if not raw:
        return None

    if re.search(r"\d", raw):
        return None

    candidates = re.findall(r"(?<![A-Za-z])[A-Za-z]{3,5}(?![A-Za-z])", raw)
    for candidate in candidates:
        ticker = candidate.strip().upper()
        if not ticker or ticker.lower() in GENERIC_TICKER_STOPWORDS:
            continue
        return ticker

    return None


def _coin_from_unsupported_alias(message: str) -> str | None:
    unsupported = detect_unsupported_coin(message)
    return str(unsupported.get("coin") or "").strip().upper() or None


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

    if task_list:
        enriched_tasks = []
        for task in task_list:
            enriched_task = dict(task)
            task_intent = str(enriched_task.get("intent") or "").strip().lower()
            task_coin = str(enriched_task.get("coin") or "").strip().upper()
            if task_intent in {"price_query", "market_analysis"} and not task_coin:
                enriched_task["coin"] = extracted_ticker
            enriched_tasks.append(enriched_task)

        validated_tasks = [validate_coin_task(task) for task in enriched_tasks]
        unsupported_task = next(
            (
                task
                for task in validated_tasks
                if str(task.get("intent") or "").strip().lower() == "unsupported_coin"
            ),
            None,
        )
        if unsupported_task is not None:
            return {
                "intent": "unsupported_coin",
                "coin": str(unsupported_task.get("coin") or "").strip().upper(),
                "reason": "coin_not_supported",
            }

        updated_result = dict(llm_result)
        updated_result["tasks"] = validated_tasks
        if len(enriched_tasks) == 1:
            updated_result["intent"] = str(validated_tasks[0].get("intent") or "unknown").strip().lower()
            updated_result["coin"] = str(validated_tasks[0].get("coin") or extracted_ticker).strip().upper()
            if updated_result["intent"] == "unsupported_coin":
                updated_result["reason"] = "coin_not_supported"
        return updated_result

    validated_result = validate_coin_task(
        {
            **dict(llm_result),
            "coin": extracted_ticker,
        }
    )
    if str(validated_result.get("intent") or "").strip().lower() == "unsupported_coin":
        return {
            "intent": "unsupported_coin",
            "coin": str(validated_result.get("coin") or "").strip().upper(),
            "reason": "coin_not_supported",
        }

    updated_result = dict(llm_result)
    updated_result["coin"] = extracted_ticker
    return updated_result


def _build_generic_coin_result(
    message: str,
    normalized: str,
    tokens: list[str],
) -> dict[str, object] | None:
    candidate = _extract_generic_coin_candidate(message)
    if not candidate:
        return None

    intent_signal = resolve_intent(message)
    base_intent = str(intent_signal.get("intent") or "unknown").strip().lower()
    if base_intent == "help":
        return _build_result("help", confidence=0.9)
    if base_intent not in {"market_analysis", "set_favorite_coin", "price_query"}:
        base_intent = "price_query"

    validated = validate_coin_task(
        {
            "intent": base_intent,
            "coin": candidate,
            "confidence": 0.9,
        }
    )
    if str(validated.get("intent") or "").strip().lower() == "unsupported_coin":
        return {
            "intent": "unsupported_coin",
            "coin": str(validated.get("coin") or "").strip().upper(),
            "reason": "coin_not_supported",
        }

    if base_intent == "market_analysis":
        return _build_result("market_analysis", coin=candidate, confidence=0.9)

    if base_intent == "set_favorite_coin":
        return _build_result("set_favorite_coin", coin=candidate, confidence=0.9)

    return _build_result("price_query", coin=candidate, confidence=0.9)


def _build_rule_based_result_from_signals(
    raw_text: str,
    intent_signal: dict[str, object],
    coin_signal: dict[str, object],
    previous_intent: str,
) -> dict[str, object] | None:
    intent = str(intent_signal.get("intent") or "unknown").strip().lower()
    matched_intents = [
        str(item or "").strip().lower()
        for item in (intent_signal.get("matched_intents") or [])
        if str(item or "").strip()
    ]
    coin = str(coin_signal.get("coin") or "").strip().upper()

    if intent == "help":
        return _build_result("help", confidence=0.9)

    if coin and _is_context_message(raw_text):
        if _should_infer_from_state(previous_intent):
            return _build_result(previous_intent, coin=coin, confidence=0.8)
        if coin:
            return _build_result("unknown")
        return None

    task_intents = [item for item in matched_intents if item in {"price_query", "market_analysis", "set_favorite_coin"}]
    if len(task_intents) > 1 and coin:
        tasks = []
        for task_intent in task_intents:
            validated = validate_coin_task(
                {
                    "intent": task_intent,
                    "coin": coin,
                    "confidence": 0.9,
                }
            )
            if str(validated.get("intent") or "").strip().lower() == "unsupported_coin":
                return {
                    "intent": "unsupported_coin",
                    "coin": coin,
                    "reason": "coin_not_supported",
                }
            tasks.append(
                {
                    "intent": task_intent,
                    "coin": coin,
                }
            )
        return {
            "tasks": tasks,
            "intent": tasks[0]["intent"],
            "coin": coin,
            "confidence": 0.9,
            "reason": "multi_intent_signals",
        }

    if coin and intent in {"price_query", "market_analysis", "set_favorite_coin"}:
        validated = validate_coin_task(
            {
                "intent": intent,
                "coin": coin,
                "confidence": 0.9,
            }
        )
        if str(validated.get("intent") or "").strip().lower() == "unsupported_coin":
            return {
                "intent": "unsupported_coin",
                "coin": coin,
                "reason": "coin_not_supported",
            }
        return _build_result(intent, coin=coin, confidence=0.9)

    if coin and intent == "unknown":
        validated = validate_coin_task(
            {
                "intent": "price_query",
                "coin": coin,
                "confidence": 0.9,
            }
        )
        if str(validated.get("intent") or "").strip().lower() == "unsupported_coin":
            return {
                "intent": "unsupported_coin",
                "coin": coin,
                "reason": "coin_not_supported",
            }
        return _build_result("price_query", coin=coin, confidence=0.9)

    return None


def _accept_llm_result(result: dict[str, object]) -> dict[str, object]:
    validated = validate_coin_task(result)
    intent = str(validated.get("intent") or "unknown").strip().lower()
    coin = str(validated.get("coin") or "").strip().upper()
    confidence = float(validated.get("confidence") or 0.0)

    if intent not in ALLOWED_LLM_INTENTS:
        if intent == "unsupported_coin":
            return {
                "intent": "unsupported_coin",
                "coin": coin,
                "confidence": confidence,
                "reason": "coin_not_supported",
            }
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


def decide_user_intent(message: str, user_state: dict | None = None):
    """Classify a user message into a simple intent dictionary."""

    raw_text = str(message or "").strip()
    if not raw_text:
        return _build_result("unknown")

    intent_signal = resolve_intent(raw_text)
    coin_signal = resolve_coin(raw_text)
    resolved_coin = str(coin_signal.get("coin") or "").strip().upper()
    previous_intent = str((user_state or {}).get("last_intent") or "").strip().lower()
    resolution_method = str(coin_signal.get("method") or "").strip().lower()
    resolution_candidates = coin_signal.get("candidates")

    direct_result = _build_rule_based_result_from_signals(raw_text, intent_signal, coin_signal, previous_intent)
    llm_first = _should_attempt_llm_first(raw_text, intent_signal, coin_signal)

    if not llm_first and direct_result is not None:
        return direct_result

    if llm_first:
        if not _is_ascii_text(raw_text):
            print("[DecisionEngine] natural-language detected")
        print("[DecisionEngine] LLM-first path")
        print("[DecisionEngine] routing to LLM-first path")
        llm_result = classify_with_llm(raw_text)
        llm_reason = str(llm_result.get("reason") or "").strip().lower()
        if llm_reason in {"missing_client", "llm_error", "invalid_json"}:
            print("[DecisionEngine] LLM failed, resolver fallback")
            print("[DecisionEngine] LLM unavailable or failed, fallback to ticker extraction")
        llm_result = _apply_generic_ticker_extraction(raw_text, llm_result)
        llm_result = _validate_task_list_result(llm_result)
        if str(llm_result.get("intent") or "").strip().lower() == "unsupported_coin":
            return llm_result

        if llm_reason in {"low_confidence", "candidate_mismatch"} or str(llm_result.get("intent") or "").strip().lower() == "clarification_needed":
            clarification_result = _build_clarification_result(raw_text, candidates=resolution_candidates)
            if clarification_result is not None:
                return clarification_result

        llm_tasks = llm_result.get("tasks")
        if isinstance(llm_tasks, list) and llm_tasks:
            if len(llm_tasks) >= 2:
                print("[DecisionEngine] multi-intent tasks accepted")
            return llm_result

        accepted_llm_result = _accept_llm_result(llm_result)
        if str(accepted_llm_result.get("intent") or "").strip().lower() == "unsupported_coin":
            return _build_unsupported_coin_result(llm_result)
        if accepted_llm_result.get("intent") != "unknown" or accepted_llm_result.get("coin"):
            return accepted_llm_result

        print("[DecisionEngine] LLM failed, fallback to rule-based")
        rule_based = _build_rule_based_result_from_signals(raw_text, intent_signal, coin_signal, previous_intent)
        if rule_based is not None:
            return rule_based

    if resolution_method == "fuzzy_candidates":
        fuzzy_result = _build_clarification_result(raw_text, candidates=resolution_candidates)
        if fuzzy_result is not None:
            return fuzzy_result

    if direct_result is not None:
        return direct_result

    if llm_first:
        clarification_result = _build_clarification_result(raw_text)
        if clarification_result is not None:
            return clarification_result

    return _build_result("unknown")
