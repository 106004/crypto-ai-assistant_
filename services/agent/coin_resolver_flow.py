"""CoinResolver concept flow for the FastAPI wrapper.

This module keeps the higher-level coin resolution sequence separate from the
single-file coin parser so the API can reuse the original project behavior
without turning `coin_resolver.py` into a workflow entrypoint.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from services.agent.coin_aliases import is_supported_coin
from services.agent.coin_resolver import GENERIC_TICKER_STOPWORDS
from services.agent.coin_validator import normalize_llm_coin, normalize_coin_symbol
from services.agent.llm_intent_classifier import classify_with_llm
from services.agent.semantic_resolver import _match_exact_alias, _match_fuzzy_candidates
from services.agent.unsupported_coin_service import detect_unsupported_coin


def _normalize_coin_value(value: object) -> str | None:
    if value in (None, ""):
        return None
    coin = str(value).strip().upper()
    return coin or None


def _normalize_candidates(value: object) -> list[dict[str, Any]]:
    normalized_candidates: list[dict[str, Any]] = []
    if not isinstance(value, list):
        return normalized_candidates

    for item in value:
        if not isinstance(item, dict):
            normalized_candidates.append({"value": item})
            continue

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

    return normalized_candidates


def _tag_candidates(candidates: list[dict[str, Any]], source: str) -> list[dict[str, Any]]:
    tagged_candidates: list[dict[str, Any]] = []
    for candidate in candidates:
        tagged_candidate = dict(candidate)
        tagged_candidate["source"] = source
        tagged_candidates.append(tagged_candidate)
    return tagged_candidates


def _merge_candidate_lists(*candidate_lists: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()

    for candidate_list in candidate_lists:
        for candidate in candidate_list:
            coin = str(candidate.get("coin") or "").strip().upper()
            if not coin or coin in seen:
                continue
            seen.add(coin)
            merged.append(dict(candidate))

    return merged


def _is_candidate_match(coin: str | None, candidates: list[dict[str, Any]]) -> bool:
    if not coin:
        return False

    normalized_coin = coin.strip().upper()
    for candidate in candidates:
        candidate_coin = str(candidate.get("coin") or "").strip().upper()
        if candidate_coin == normalized_coin:
            return True
    return False


def _debug_step(step: str, executed: bool, matched: bool, **extra: object) -> dict[str, object]:
    entry: dict[str, object] = {
        "step": step,
        "executed": executed,
        "matched": matched,
    }
    entry.update(extra)
    return entry


def _extract_ticker_candidates(message: str) -> list[dict[str, Any]]:
    """Return standalone ticker candidates and skip mixed-case typos like BTCc."""

    raw = str(message or "").strip()
    if not raw or re.search(r"\d", raw):
        return []

    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in re.findall(r"(?<![A-Za-z])[A-Za-z]{3,5}(?![A-Za-z])", raw):
        ticker = candidate.strip()
        if not ticker:
            continue
        if ticker.lower() in GENERIC_TICKER_STOPWORDS:
            continue
        if not (ticker.islower() or ticker.isupper()):
            continue

        coin = ticker.upper()
        if coin in seen:
            continue
        seen.add(coin)
        candidates.append({"coin": coin, "source": "ticker_extraction"})

    return candidates


def _build_response(
    *,
    coin: str | None,
    status: Literal["supported", "unsupported", "ambiguous", "not_found", "error"],
    method: str,
    candidates: list[dict[str, Any]],
    confidence: float,
    llm_used: bool,
    debug_trace: list[dict[str, Any]],
) -> dict[str, object]:
    return {
        "coin": coin,
        "status": status,
        "method": method,
        "candidates": candidates,
        "confidence": confidence,
        "llm_used": llm_used,
        "debug_trace": debug_trace,
    }


def _finalize_from_coin(
    *,
    coin: str | None,
    method: str,
    confidence: float,
    llm_used: bool,
    candidates: list[dict[str, Any]],
    debug_trace: list[dict[str, Any]],
) -> dict[str, object]:
    if coin is None:
        status: Literal["supported", "unsupported", "ambiguous", "not_found", "error"]
        status = "ambiguous" if candidates else "not_found"
    elif not is_supported_coin(coin):
        status = "unsupported"
    else:
        status = "supported"

    debug_trace.append(
        {
            "step": "final_decision",
            "executed": True,
            "matched": coin is not None,
            "source": method,
            "coin": coin,
            "status": status,
        }
    )
    return _build_response(
        coin=coin,
        status=status,
        method=method,
        candidates=candidates if status == "ambiguous" else [],
        confidence=confidence,
        llm_used=llm_used,
        debug_trace=debug_trace,
    )


def _finalize_from_gemini_candidates(
    *,
    llm_result: dict[str, object],
    candidates: list[dict[str, Any]],
    debug_trace: list[dict[str, Any]],
) -> dict[str, object]:
    coin_debug = normalize_llm_coin(llm_result.get("coin"))
    coin = normalize_coin_symbol(llm_result.get("coin"))
    confidence = float(llm_result.get("confidence") or 0.0)
    reason = str(llm_result.get("reason") or "").strip().lower()
    intent = str(llm_result.get("intent") or "").strip().lower()
    llm_raw_coin = llm_result.get("llm_raw_coin") or coin_debug.get("llm_raw_coin")
    normalized_coin = coin_debug.get("normalized_coin")
    rejected_reason = llm_result.get("rejected_reason") or coin_debug.get("rejected_reason")
    if coin is not None:
        final_coin_source = "gemini_symbol"
    elif llm_raw_coin:
        final_coin_source = "rejected_non_symbol"
    else:
        final_coin_source = "none"

    llm_selected_candidate = _is_candidate_match(coin, candidates)
    accepted_coin = coin
    debug_trace.append(
        {
            "step": "gemini_candidate_judge",
            "executed": True,
            "matched": accepted_coin is not None,
            "coin": coin,
            "llm_raw_coin": llm_raw_coin,
            "normalized_coin": normalized_coin,
            "rejected_reason": rejected_reason,
            "final_coin_source": final_coin_source,
            "reason": reason,
            "intent": intent,
            "selected_candidate": llm_selected_candidate,
            "accepted_coin": accepted_coin,
            "candidates": candidates,
        }
    )

    if accepted_coin is None:
        status: Literal["supported", "unsupported", "ambiguous", "not_found", "error"] = "ambiguous" if candidates else "not_found"
        debug_trace.append(
            {
                "step": "final_decision",
                "executed": True,
                "matched": False,
                "source": "gemini_candidate_judge",
                "coin": None,
                "status": status,
                "final_coin_source": final_coin_source,
            }
        )
        return _build_response(
            coin=None,
            status=status,
            method="gemini_candidate_judge",
            candidates=candidates if status == "ambiguous" else [],
            confidence=confidence,
            llm_used=True,
            debug_trace=debug_trace,
        )

    status = "supported" if is_supported_coin(accepted_coin) else "unsupported"
    debug_trace.append(
        {
            "step": "final_decision",
            "executed": True,
            "matched": True,
            "source": "gemini_candidate_judge",
            "coin": accepted_coin,
            "status": status,
            "final_coin_source": final_coin_source,
        }
    )
    return _build_response(
        coin=accepted_coin,
        status=status,
        method="gemini_candidate_judge",
        candidates=[],
        confidence=confidence,
        llm_used=True,
        debug_trace=debug_trace,
    )


def resolve_coin_flow(text: str, debug: bool = False) -> dict[str, object]:
    """Resolve a coin using the full concept flow used by the FastAPI wrapper."""

    raw_text = str(text or "").strip()
    debug_trace: list[dict[str, Any]] = []

    if not raw_text:
        debug_trace.extend(
            [
                _debug_step("exact_match", False, False),
                _debug_step("alias_match", False, False),
                _debug_step("ticker_extraction", False, False, candidates=[]),
                _debug_step("fuzzy_candidates", False, False, candidates=[]),
                _debug_step("gemini_candidate_judge", False, False, selected_coin=None, reason="no_candidates", candidates=[]),
                _debug_step("final_decision", True, False, source="none", coin=None, status="not_found"),
            ]
        )
        return _build_response(
            coin=None,
            status="not_found",
            method="none",
            candidates=[],
            confidence=0.0,
            llm_used=False,
            debug_trace=debug_trace,
        )

    exact_match = _match_exact_alias(raw_text)
    if exact_match is not None:
        coin = _normalize_coin_value(exact_match.get("coin"))
        confidence = float(exact_match.get("confidence") or 0.0)
        debug_trace.extend(
            [
                _debug_step("exact_match", True, True, coin=coin, source="semantic_resolver"),
                _debug_step("alias_match", False, False),
                _debug_step("ticker_extraction", False, False, candidates=[]),
                _debug_step("fuzzy_candidates", False, False, candidates=[]),
                _debug_step("gemini_candidate_judge", False, False, selected_coin=None, reason="exact_match_short_circuit", candidates=[]),
            ]
        )
        return _finalize_from_coin(
            coin=coin,
            method="exact_match",
            confidence=confidence,
            llm_used=False,
            candidates=[],
            debug_trace=debug_trace,
        )

    debug_trace.append(_debug_step("exact_match", True, False, source="semantic_resolver"))

    unsupported_alias = detect_unsupported_coin(raw_text)
    unsupported_coin = _normalize_coin_value(unsupported_alias.get("coin"))
    if unsupported_coin is not None:
        confidence = float(unsupported_alias.get("confidence") or 0.0)
        debug_trace.extend(
            [
                _debug_step("alias_match", True, True, coin=unsupported_coin, source="unsupported_coin_service"),
                _debug_step("ticker_extraction", False, False, candidates=[]),
                _debug_step("fuzzy_candidates", False, False, candidates=[]),
                _debug_step("gemini_candidate_judge", False, False, selected_coin=None, reason="alias_match_short_circuit", candidates=[]),
            ]
        )
        return _finalize_from_coin(
            coin=unsupported_coin,
            method="alias_match",
            confidence=confidence,
            llm_used=False,
            candidates=[],
            debug_trace=debug_trace,
        )

    debug_trace.append(_debug_step("alias_match", True, False, source="unsupported_coin_service"))

    ticker_candidates = _extract_ticker_candidates(raw_text)
    debug_trace.append(
        _debug_step(
            "ticker_extraction",
            True,
            bool(ticker_candidates),
            candidates=ticker_candidates,
            source="strict_ticker",
        )
    )

    fuzzy_result = _match_fuzzy_candidates(raw_text)
    fuzzy_candidates = _normalize_candidates(fuzzy_result.get("candidates") if isinstance(fuzzy_result, dict) else [])
    fuzzy_candidates = _tag_candidates(fuzzy_candidates, "fuzzy")
    debug_trace.append(
        _debug_step(
            "fuzzy_candidates",
            True,
            bool(fuzzy_candidates),
            candidates=fuzzy_candidates,
            source="semantic_resolver",
        )
    )

    gemini_candidates = _merge_candidate_lists(ticker_candidates, fuzzy_candidates)
    llm_result = classify_with_llm(raw_text, candidates=gemini_candidates or None, return_debug=True)
    return _finalize_from_gemini_candidates(
        llm_result=llm_result,
        candidates=gemini_candidates,
        debug_trace=debug_trace,
    )
