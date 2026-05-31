"""Coin resolver router."""

from __future__ import annotations

import os
from contextlib import ExitStack
from typing import Any, Literal
from unittest.mock import patch

from fastapi import APIRouter

from api.schemas.coin import ResolveCoinRequest, ResolveCoinResponse
from services.agent import decision_engine
from services.agent.coin_aliases import is_supported_coin
from services.agent.coin_resolver_flow import resolve_coin_flow


router = APIRouter()


def _gemini_debug_status() -> dict[str, bool]:
    """Return safe Gemini availability flags without exposing secret values."""

    gemini_key_loaded = bool(os.getenv("GEMINI_API_KEY"))
    try:
        from google import genai  # noqa: F401
    except Exception:
        gemini_client_available = False
    else:
        gemini_client_available = gemini_key_loaded

    return {
        "gemini_key_loaded": gemini_key_loaded,
        "gemini_client_available": gemini_client_available,
    }


def adapt_resolve_coin_result(result: object) -> dict[str, object]:
    """Convert the existing resolver output into the API response shape."""

    payload = result if isinstance(result, dict) else {}

    coin_value = payload.get("coin")
    coin = str(coin_value).strip().upper() if coin_value not in (None, "") else None
    method = str(payload.get("method") or "none")
    reason = str(payload.get("reason") or "").strip().lower()
    confidence = float(payload.get("confidence") or 0.0)

    raw_candidates = payload.get("candidates") or []
    candidates: list[dict[str, Any]] = []
    if isinstance(raw_candidates, list):
        for item in raw_candidates:
            if isinstance(item, dict):
                normalized_item = dict(item)
                candidate_coin = normalized_item.get("coin")
                if candidate_coin not in (None, ""):
                    normalized_item["coin"] = str(candidate_coin).strip().upper()
                score = normalized_item.get("score")
                if score is not None:
                    try:
                        normalized_item["score"] = float(score)
                    except (TypeError, ValueError):
                        normalized_item["score"] = 0.0
                candidates.append(normalized_item)
            else:
                candidates.append({"value": item})

    if method == "fuzzy_candidates" or (coin is None and candidates):
        status: Literal["supported", "unsupported", "ambiguous", "not_found", "error"] = "ambiguous"
        coin = None
    elif coin is None:
        status = "not_found"
    elif not is_supported_coin(coin):
        status = "unsupported"
    else:
        status = "supported"

    if reason == "nickname_normalized" and coin:
        status = "unsupported"
    elif reason in {"empty_message", "no_coin"} and coin is None and not candidates:
        status = "not_found"

    if status != "ambiguous":
        candidates = []

    return {
        "coin": coin,
        "status": status,
        "method": method,
        "candidates": candidates,
        "confidence": confidence,
    }


def _normalize_coin_value(value: object) -> str | None:
    if value in (None, ""):
        return None
    normalized = str(value).strip().upper()
    return normalized or None


def _normalize_candidates(value: object) -> list[dict[str, Any]]:
    normalized_candidates: list[dict[str, Any]] = []
    if not isinstance(value, list):
        return normalized_candidates

    for item in value:
        if isinstance(item, dict):
            normalized_item = dict(item)
            candidate_coin = normalized_item.get("coin")
            if candidate_coin not in (None, ""):
                normalized_item["coin"] = str(candidate_coin).strip().upper()
            score = normalized_item.get("score")
            if score is not None:
                try:
                    normalized_item["score"] = float(score)
                except (TypeError, ValueError):
                    normalized_item["score"] = 0.0
            normalized_candidates.append(normalized_item)
        else:
            normalized_candidates.append({"value": item})

    return normalized_candidates


def _is_candidate_match(coin: str | None, candidates: list[dict[str, Any]]) -> bool:
    if not coin:
        return False
    normalized_coin = coin.strip().upper()
    for candidate in candidates:
        candidate_coin = str(candidate.get("coin") or "").strip().upper()
        if candidate_coin == normalized_coin:
            return True
    return False


def _determine_final_source(decision: object, llm_used: bool, llm_selected_candidate: bool) -> str:
    payload = decision if isinstance(decision, dict) else {}
    intent = str(payload.get("intent") or "unknown").strip().lower()
    tasks = payload.get("tasks")

    if isinstance(tasks, list) and tasks:
        return "decision_engine_llm_tasks"

    if intent == "clarification_needed":
        return "decision_engine_llm_candidates" if llm_used and llm_selected_candidate else "decision_engine_llm_clarification" if llm_used else "decision_engine_clarification"

    if intent == "unsupported_coin":
        return "decision_engine_unsupported_coin"

    if llm_used:
        return "decision_engine_llm"

    return "decision_engine_direct"


def _build_debug_trace(
    intent_result: object,
    coin_result: object,
    decision: object,
    llm_used: bool,
    llm_state: dict[str, Any],
) -> list[dict[str, Any]]:
    trace: list[dict[str, Any]] = []

    if isinstance(intent_result, dict):
        trace.append(
            {
                "step": "intent_resolver",
                "executed": True,
                "matched": str(intent_result.get("intent") or "").strip().lower() != "unknown",
                "intent": intent_result.get("intent"),
                "reason": intent_result.get("reason"),
            }
        )
    else:
        trace.append(
            {
                "step": "intent_resolver",
                "executed": False,
                "matched": False,
                "intent": None,
                "reason": None,
            }
        )

    if isinstance(coin_result, dict):
        coin = _normalize_coin_value(coin_result.get("coin"))
        trace.append(
            {
                "step": "coin_resolver",
                "executed": True,
                "matched": bool(coin),
                "coin": coin,
                "method": coin_result.get("method"),
                "reason": coin_result.get("reason"),
            }
        )
        debug_trace = coin_result.get("debug_trace")
        if isinstance(debug_trace, list):
            trace.extend(dict(step) if isinstance(step, dict) else {"value": step} for step in debug_trace)
    else:
        trace.append(
            {
                "step": "coin_resolver",
                "executed": False,
                "matched": False,
                "coin": None,
                "method": None,
                "reason": None,
            }
        )

    llm_result = llm_state.get("result")
    llm_candidates = _normalize_candidates(llm_state.get("candidates"))
    llm_coin = _normalize_coin_value(llm_result.get("coin")) if isinstance(llm_result, dict) else None
    llm_selected_candidate = _is_candidate_match(llm_coin, llm_candidates)
    llm_error = None
    if isinstance(llm_result, dict):
        reason = str(llm_result.get("reason") or "").strip().lower()
        if reason in {"missing_client", "llm_error", "invalid_json"}:
            llm_error = reason
    trace.append(
        {
            "step": "gemini_classifier",
            "executed": llm_used,
            "matched": llm_selected_candidate,
            "candidates": llm_candidates,
            "selected_candidate": llm_selected_candidate,
            "result_coin": llm_coin,
            "reason": llm_result.get("reason") if isinstance(llm_result, dict) else None,
            "error": llm_error,
        }
    )

    payload = decision if isinstance(decision, dict) else {}
    final_coin = _normalize_coin_value(payload.get("coin")) or llm_coin or _normalize_coin_value(coin_result.get("coin") if isinstance(coin_result, dict) else None)
    final_source = _determine_final_source(decision, llm_used, llm_selected_candidate)
    trace.append(
        {
            "step": "final_decision",
            "executed": True,
            "matched": bool(final_coin),
            "source": final_source,
            "intent": payload.get("intent"),
            "coin": final_coin,
        }
    )

    return trace


def adapt_full_decision_result(
    result: object,
    *,
    llm_used: bool,
    debug_trace: list[dict[str, Any]] | None = None,
    coin_candidates: list[dict[str, Any]] | None = None,
) -> dict[str, object]:
    """Convert the full decision-engine output into the API response shape."""

    payload = result if isinstance(result, dict) else {}
    coin = _normalize_coin_value(payload.get("coin"))
    confidence = float(payload.get("confidence") or 0.0)
    candidates = _normalize_candidates(payload.get("candidates"))
    if not candidates:
        candidates = _normalize_candidates(coin_candidates or [])

    intent = str(payload.get("intent") or "unknown").strip().lower()
    reason = str(payload.get("reason") or "").strip().lower()
    method = _determine_final_source(payload, llm_used, _is_candidate_match(coin, candidates))
    if reason and method == "decision_engine_direct":
        method = f"decision_engine_{reason}"

    if intent == "unsupported_coin":
        status: Literal["supported", "unsupported", "ambiguous", "not_found", "error"] = "unsupported"
    elif intent == "clarification_needed":
        status = "ambiguous"
    elif coin is None and candidates:
        status = "ambiguous"
    elif coin is None:
        status = "not_found"
    elif not is_supported_coin(coin):
        status = "unsupported"
    else:
        status = "supported"

    if status != "ambiguous":
        candidates = []

    return {
        "coin": coin,
        "status": status,
        "method": method,
        "candidates": candidates,
        "confidence": confidence,
        "llm_used": llm_used,
        "debug_trace": debug_trace or [],
    }


def resolve_coin_with_full_decision_flow(text: str, debug: bool = False) -> dict[str, object]:
    """Run the same coin decision path the LINE bot uses."""

    raw_text = str(text or "").strip()
    intent_state: dict[str, object] = {}
    coin_state: dict[str, object] = {}
    llm_state: dict[str, Any] = {"called": False, "candidates": [], "result": None}

    original_resolve_intent = decision_engine.resolve_intent
    original_resolve_coin = decision_engine.resolve_coin
    original_classify_with_llm = decision_engine.classify_with_llm

    def traced_resolve_intent(message: str):
        result = original_resolve_intent(message)
        intent_state["result"] = result
        return result

    def traced_resolve_coin(message: str):
        result = original_resolve_coin(message, debug=True)
        coin_state["result"] = result
        sanitized = dict(result)
        sanitized.pop("debug_trace", None)
        return sanitized

    def traced_classify_with_llm(message: str, candidates: list[dict[str, object]] | None = None):
        llm_state["called"] = True
        llm_state["candidates"] = _normalize_candidates(candidates or [])
        result = original_classify_with_llm(message, candidates=candidates)
        llm_state["result"] = result
        return result

    with ExitStack() as stack:
        stack.enter_context(patch.object(decision_engine, "resolve_intent", traced_resolve_intent))
        stack.enter_context(patch.object(decision_engine, "resolve_coin", traced_resolve_coin))
        stack.enter_context(patch.object(decision_engine, "classify_with_llm", traced_classify_with_llm))
        decision = decision_engine.decide_user_intent(raw_text)

    debug_trace = _build_debug_trace(
        intent_state.get("result"),
        coin_state.get("result"),
        decision,
        bool(llm_state.get("called")),
        llm_state,
    )
    return adapt_full_decision_result(
        decision,
        llm_used=bool(llm_state.get("called")),
        debug_trace=debug_trace,
        coin_candidates=_normalize_candidates(coin_state.get("result", {}).get("candidates") if isinstance(coin_state.get("result"), dict) else []),
    )


@router.post("/resolve-coin", response_model=ResolveCoinResponse, name="resolve_coin")
def resolve_coin_api(request: ResolveCoinRequest) -> dict[str, object]:
    try:
        response = resolve_coin_flow(request.text, debug=False)
        response.update(_gemini_debug_status())
        return response
    except Exception:
        response = {
            "coin": None,
            "status": "error",
            "method": "exception",
            "candidates": [],
            "confidence": 0.0,
            "llm_used": False,
            "debug_trace": [],
        }
        response.update(_gemini_debug_status())
        return response
