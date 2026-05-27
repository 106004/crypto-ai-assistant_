"""Gemini-based fallback classifier for ambiguous agent intents."""

from __future__ import annotations

import json
import re
from typing import Any

from config.settings import GEMINI_MODEL
from gemini_client import get_gemini_client


ALLOWED_INTENTS = {
    "price_query",
    "market_analysis",
    "set_favorite_coin",
    "get_favorite_coin",
    "help",
    "unknown",
}
SUPPORTED_COINS = {
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
        "Please only output JSON.\n"
        "Do not explain.\n"
        "Do not check prices.\n"
        "Do not analyze the market.\n"
        "Do not give investment advice.\n"
        "Use the original message and the candidate coins if provided.\n"
        "If a candidate looks similar but does not fit the user's meaning, do not select it.\n"
        "If the coin is known but unsupported, return unsupported_coin.\n"
        "\n"
        "Return this JSON schema exactly:\n"
        '{'
        '"intent":"price_query | market_analysis | set_favorite_coin | get_favorite_coin | help | unknown",'
        '"coin":"any coin symbol or null",'
        '"confidence":0.0,'
        '"reason":"..."'
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
    if json_text is None:
        return _build_unknown("invalid_json")

    try:
        payload = json.loads(json_text)
    except json.JSONDecodeError:
        return _build_unknown("invalid_json")

    if not isinstance(payload, dict):
        return _build_unknown("invalid_json")

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
        return _build_response("unsupported_coin", coin, confidence, "coin_not_supported")

    candidate_coins = {
        str(item.get("coin") or "").strip().upper()
        for item in (candidates or [])
        if str(item.get("coin") or "").strip()
    }
    if candidate_coins and coin not in candidate_coins:
        return _build_response("clarification_needed", None, confidence, "candidate_mismatch")

    if not candidate_coins and message:
        message_coin_tokens = {
            token.upper()
            for token in re.findall(r"\b[A-Za-z]{2,4}\b", str(message))
        }
        if message_coin_tokens and coin not in message_coin_tokens:
            return _build_response("clarification_needed", None, confidence, "candidate_mismatch")

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
        print("[LLMClassifier] invalid JSON")
        return _build_unknown("missing_client")

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=_build_prompt(message, candidates=candidates),
        )
        raw_output = str(getattr(response, "text", "") or "").strip()
    except Exception:
        print("[LLMClassifier] invalid JSON")
        return _build_unknown("llm_error")

    result = parse_llm_classifier_output(raw_output, message=message, candidates=candidates)
    reason = str(result.get("reason") or "").strip().lower()
    intent = str(result.get("intent") or "").strip().lower()

    if reason == "invalid_json":
        print("[LLMClassifier] invalid JSON")
        return result

    print("[LLMClassifier] JSON parsed")

    if intent == "unsupported_coin" or reason == "coin_not_supported":
        print("[LLMJudge] unsupported coin detected")
        return result

    if reason == "unsupported_intent":
        print("[LLMClassifier] rejected unsupported intent")
        return result

    if reason == "missing_confidence":
        print("[LLMClassifier] rejected low confidence")
        return result

    if intent == "clarification_needed":
        print("[LLMJudge] rejected fuzzy candidate")
        return result

    if reason == "candidate_mismatch":
        print("[LLMJudge] rejected fuzzy candidate")
        return result

    if intent == "unknown" and reason == "low_confidence":
        print("[LLMJudge] rejected fuzzy candidate")
        return result

    if intent in ALLOWED_INTENTS:
        if candidates:
            print("[LLMJudge] selected coin")
        print("[LLMClassifier] accepted")
        return result

    print("[LLMClassifier] invalid JSON")
    return _build_unknown("invalid_json")
