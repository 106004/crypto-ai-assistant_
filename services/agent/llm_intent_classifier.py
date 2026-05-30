"""Gemini-based fallback classifier for ambiguous agent intents."""

from __future__ import annotations

import json
import re
from typing import Any

from config.settings import GEMINI_MODEL
from gemini_client import get_gemini_client
from services.agent.coin_validator import validate_coin_task
from services.agent.coin_validator import SUPPORTED_COINS


ALLOWED_INTENTS = {
    "price_query",
    "market_analysis",
    "set_favorite_coin",
    "get_favorite_coin",
    "help",
    "unknown",
}
ALLOWED_TASK_INTENTS = {
    "price_query",
    "market_analysis",
    "unsupported_coin",
    "clarification_needed",
    "unknown",
}
NULL_COIN_ALLOWED_INTENTS = {"help", "get_favorite_coin", "unknown"}
CONFIDENCE_THRESHOLD = 0.75


def _build_response(intent: str, coin: str | None, confidence: float, reason: str) -> dict[str, object]:
    return {
        "intent": intent,
        "coin": coin,
        "confidence": confidence,
        "reason": reason,
    }


def _build_unknown(reason: str) -> dict[str, object]:
    return _build_response("unknown", None, 0.0, reason)


def _strip_code_fences(text: str) -> str:
    cleaned = str(text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _extract_json_text(text: str) -> str | None:
    cleaned = _strip_code_fences(text)
    if not cleaned:
        return None

    if cleaned.startswith("{") and cleaned.endswith("}"):
        return cleaned

    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match:
        return match.group(0)
    return None


def _normalize_intent(raw_intent: Any) -> str:
    intent = str(raw_intent or "").strip().lower()
    if intent not in ALLOWED_INTENTS:
        return ""
    return intent


def _normalize_coin(raw_coin: Any) -> str | None:
    if raw_coin is None:
        return None

    coin = str(raw_coin).strip().upper()
    if coin in {"", "NULL", "NONE"}:
        return None
    return coin


def _normalize_task_intent(raw_intent: Any) -> str:
    intent = str(raw_intent or "").strip().lower()
    if intent not in ALLOWED_TASK_INTENTS:
        return ""
    return intent


def _normalize_task_coin(raw_coin: Any) -> str | None:
    return _normalize_coin(raw_coin)


def _compatibility_confidence(intent: str) -> float:
    if intent == "unknown":
        return 0.0
    if intent == "clarification_needed":
        return 0.7
    if intent == "unsupported_coin":
        return 0.99
    return 0.9


def _normalize_tasks_payload(payload_tasks: Any) -> list[dict[str, object]] | None:
    if not isinstance(payload_tasks, list) or not payload_tasks:
        return None

    normalized_tasks: list[dict[str, object]] = []
    for raw_task in payload_tasks:
        if not isinstance(raw_task, dict):
            return None

        intent = _normalize_task_intent(raw_task.get("intent"))
        if not intent:
            return None

        coin = _normalize_task_coin(raw_task.get("coin"))
        if intent in {"price_query", "market_analysis"}:
            if coin is not None and coin not in SUPPORTED_COINS:
                normalized_tasks.append({"intent": "unsupported_coin", "coin": coin})
                continue
            normalized_tasks.append({"intent": intent, "coin": coin})
            continue

        if intent == "unsupported_coin":
            if coin is None or coin in SUPPORTED_COINS:
                return None
            normalized_tasks.append({"intent": "unsupported_coin", "coin": coin})
            continue

        normalized_tasks.append({"intent": intent, "coin": coin})

    validated_tasks = [validate_coin_task(task) for task in normalized_tasks]

    unsupported_tasks = [
        task
        for task in validated_tasks
        if str(task.get("intent") or "").strip().lower() == "unsupported_coin"
    ]
    unsupported_coins = {
        str(task.get("coin") or "").strip().upper()
        for task in unsupported_tasks
        if str(task.get("coin") or "").strip()
    }
    if len(unsupported_tasks) == len(validated_tasks) and len(unsupported_coins) == 1:
        return [
            {
                "intent": "unsupported_coin",
                "coin": next(iter(unsupported_coins)),
            }
        ]

    if validated_tasks and str(validated_tasks[0].get("intent") or "").strip().lower() in {"clarification_needed", "unknown"}:
        return [
            {
                "intent": str(validated_tasks[0].get("intent") or "unknown").strip().lower(),
                "coin": validated_tasks[0].get("coin"),
            }
        ]

    return [
        {
            "intent": str(task.get("intent") or "unknown").strip().lower(),
            "coin": task.get("coin"),
        }
        for task in validated_tasks
    ]


def _build_tasks_response(tasks: list[dict[str, object]]) -> dict[str, object]:
    primary_task = tasks[0]
    primary_intent = str(primary_task.get("intent") or "unknown").strip().lower()
    primary_coin = _normalize_coin(primary_task.get("coin"))
    reason = "coin_not_supported" if len(tasks) == 1 and primary_intent == "unsupported_coin" else "multi_intent_tasks"
    return {
        "tasks": tasks,
        "intent": primary_intent,
        "coin": primary_coin,
        "confidence": _compatibility_confidence(primary_intent),
        "reason": reason,
    }


def _validate_classifier_result(result: dict[str, object]) -> dict[str, object]:
    validated = validate_coin_task(result)
    intent = str(validated.get("intent") or "").strip().lower()
    if intent == "unsupported_coin":
        return {
            **validated,
            "reason": "coin_not_supported",
        }
    return validated


def _normalize_confidence(raw_confidence: Any) -> tuple[float | None, str | None]:
    if raw_confidence is None:
        return None, "missing_confidence"

    try:
        confidence = float(raw_confidence)
    except (TypeError, ValueError):
        return None, "missing_confidence"

    return confidence, None


def _format_candidates(candidates: list[dict[str, object]] | None) -> str:
    if not candidates:
        return "None"

    parts: list[str] = []
    for item in candidates:
        coin = str(item.get("coin") or "").strip().upper()
        score = item.get("score")
        if coin:
            parts.append(f"{coin}:{score}")
    return ", ".join(parts) if parts else "None"


def _build_prompt(message: str, candidates: list[dict[str, object]] | None = None) -> str:
    return (
        "You are intent classifier.\n"
        "Analyze the user's message for multiple intents.\n"
        "If there are multiple intents, output them in the same order as the user's meaning.\n"
        "Please only output JSON.\n"
        "Do not explain.\n"
        "Do not check prices.\n"
        "Do not analyze the market.\n"
        "Do not give investment advice.\n"
        "Return tasks only.\n"
        "If there is only one intent, tasks must still contain exactly one item.\n"
        "Each task must contain intent and coin.\n"
        "Use one of these task intents: price_query, market_analysis, unsupported_coin, clarification_needed, unknown.\n"
        "If the coin is unknown, set coin to null.\n"
        "Use the original message and the candidate coins if provided.\n"
        "Candidate coins are hints, not hard restrictions.\n"
        "You may select one of the candidates or choose another supported coin if the user's text clearly points to it.\n"
        "Do not invent a coin that is not supported by the user's meaning.\n"
        "If the coin is known but unsupported, return unsupported_coin.\n"
        "\n"
        "Return this JSON schema exactly:\n"
        '{'
        '"tasks":[{"intent":"price_query | market_analysis | unsupported_coin | clarification_needed | unknown","coin":"any coin symbol or null"}]'
        '}\n'
        "\n"
        f"Candidate coins: {_format_candidates(candidates)}\n"
        f"User message: {message}"
    )


def parse_llm_classifier_output(
    raw_text: str,
    message: str | None = None,
    candidates: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Parse and validate a Gemini classifier payload."""

    json_text = _extract_json_text(raw_text)
    print(f"[LLMClassifier] raw response:\n{raw_text}")
    if json_text is None:
        return _build_unknown("invalid_json")

    try:
        payload = json.loads(json_text)
    except json.JSONDecodeError:
        return _build_unknown("invalid_json")

    if not isinstance(payload, dict):
        return _build_unknown("invalid_json")

    print(f"[LLMClassifier] parsed JSON:\n{payload}")

    payload_tasks = _normalize_tasks_payload(payload.get("tasks"))
    if payload_tasks is not None:
        print(f"[LLMClassifier] parsed tasks:\n{payload_tasks}")
        return _validate_classifier_result(_build_tasks_response(payload_tasks))

    raw_intent = payload.get("intent")
    raw_coin = payload.get("coin")
    raw_confidence = payload.get("confidence")
    reason = str(payload.get("reason") or "").strip() or "llm_result"

    intent = _normalize_intent(raw_intent)
    if not intent:
        return _build_unknown("unsupported_intent")

    confidence, confidence_error = _normalize_confidence(raw_confidence)
    if confidence_error is not None or confidence is None:
        return _build_unknown(confidence_error or "missing_confidence")

    coin = _normalize_coin(raw_coin)
    if confidence < CONFIDENCE_THRESHOLD:
        return _build_response(
            "clarification_needed",
            coin if coin is not None else None,
            confidence,
            "low_confidence",
        )

    if coin is None:
        if intent in NULL_COIN_ALLOWED_INTENTS:
            if intent == "unknown":
                return _build_response("unknown", None, confidence, reason)
            return _build_response(intent, None, confidence, reason)
        return _build_unknown("coin_unrecognized")

    if coin not in SUPPORTED_COINS:
        return _validate_classifier_result(_build_response("unsupported_coin", coin, confidence, "coin_not_supported"))

    if intent == "unknown":
        return _build_response("unknown", None, confidence, reason)

    if intent in {"help", "get_favorite_coin"}:
        return _build_response(intent, None, confidence, reason)

    return _build_response(intent, coin, confidence, reason)


def classify_with_llm(
    message: str,
    candidates: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Classify intent and coin using Gemini when rule-based signals are ambiguous."""

    print("[LLMClassifier] raw output received")
    if candidates:
        print("[LLMJudge] candidates received")

    client = get_gemini_client()
    if client is None:
        print("[LLMClassifier] unavailable or failed")
        return _build_unknown("missing_client")

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=_build_prompt(message, candidates=candidates),
        )
        raw_output = str(getattr(response, "text", "") or "").strip()
    except Exception:
        print("[LLMClassifier] unavailable or failed")
        return _build_unknown("llm_error")

    result = parse_llm_classifier_output(raw_output, message=message, candidates=candidates)
    reason = str(result.get("reason") or "").strip().lower()
    intent = str(result.get("intent") or "").strip().lower()

    if reason == "invalid_json":
        print("[LLMClassifier] unavailable or failed")
        return result

    print(f"[LLMClassifier] final classifier output:\n{result}")
    if "tasks" in result:
        print("[LLMClassifier] multi-intent tasks parsed")
    print("[LLMClassifier] JSON parsed")

    if intent == "unsupported_coin" or reason == "coin_not_supported":
        print("[LLMClassifier] unsupported coin detected")
        return result

    if reason == "unsupported_intent":
        print("[LLMClassifier] rejected unsupported intent")
        return result

    if reason == "missing_confidence":
        print("[LLMClassifier] rejected low confidence")
        return result

    if intent == "clarification_needed":
        print("[LLMJudge] requested clarification")
        return result

    if intent == "unknown" and reason == "low_confidence":
        print("[LLMJudge] rejected low confidence result")
        return result

    if intent in ALLOWED_INTENTS:
        if candidates:
            print("[LLMJudge] selected coin")
        print("[LLMClassifier] accepted")
        return result

    print("[LLMClassifier] invalid JSON")
    return _build_unknown("invalid_json")
