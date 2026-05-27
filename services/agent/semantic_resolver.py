"""Semantic coin resolver for the agent layer."""

from __future__ import annotations

import re
from difflib import SequenceMatcher, get_close_matches

from services.agent.coin_aliases import COIN_ALIASES, SUPPORTED_COINS


_ALIAS_ITEMS = [(alias, symbol) for alias, symbol in COIN_ALIASES.items()]
_ALIAS_VALUES = sorted({alias.lower() for alias in COIN_ALIASES})
_ALIAS_BY_LOWER = {alias.lower(): symbol for alias, symbol in COIN_ALIASES.items()}
_SUPPORTED_COINS_SET = set(SUPPORTED_COINS)
_CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]")
_ASCII_ALIAS_VALUES = [alias for alias in _ALIAS_VALUES if re.fullmatch(r"[a-z ]+", alias)]
_CJK_ALIAS_VALUES = [alias for alias in _ALIAS_VALUES if not re.fullmatch(r"[a-z ]+", alias)]


def _build_none_result() -> dict[str, object]:
    return {"coin": None, "confidence": 0.0, "method": "none"}


def _classify_candidate(candidate: str) -> str:
    has_cjk = bool(_CJK_PATTERN.search(candidate))
    has_ascii = bool(re.search(r"[A-Za-z]", candidate))
    if has_cjk and not has_ascii:
        return "cjk"
    if has_ascii and not has_cjk:
        return "ascii"
    if has_cjk and has_ascii:
        return "mixed"
    return "other"


def _tokenize_candidates(message: str) -> list[tuple[str, str]]:
    raw = str(message or "").strip()
    if not raw:
        return []

    candidates = [raw.lower()]
    candidates.extend(
        token.lower()
        for token in re.findall(r"[A-Za-z\u4e00-\u9fff]+", raw)
        if token.strip()
    )

    for chunk in re.findall(r"[\u4e00-\u9fff]+", raw):
        chunk = chunk.strip()
        if len(chunk) >= 2:
            max_window = min(4, len(chunk))
            for size in range(2, max_window + 1):
                for start in range(0, len(chunk) - size + 1):
                    candidates.append(chunk[start : start + size].lower())

    deduped: list[tuple[str, str]] = []
    seen: set[str] = set()
    for candidate in candidates:
        candidate = candidate.strip()
        if candidate and candidate not in seen:
            seen.add(candidate)
            deduped.append((candidate, _classify_candidate(candidate)))
    return deduped


def _match_exact_alias(message: str) -> dict[str, object] | None:
    raw = str(message or "")
    lowered = raw.lower()

    for alias, symbol in sorted(_ALIAS_ITEMS, key=lambda item: len(item[0]), reverse=True):
        alias_lower = alias.lower()
        if re.fullmatch(r"[A-Za-z ]+", alias):
            pattern = rf"(?<![A-Za-z0-9]){re.escape(alias_lower)}(?![A-Za-z0-9])"
            if re.search(pattern, lowered):
                print(
                    f"[SemanticResolver] exact alias matched alias={alias} coin={symbol}"
                )
                return {"coin": symbol, "confidence": 1.0, "method": "exact_alias"}
        else:
            if alias in raw or alias_lower in lowered:
                print(
                    f"[SemanticResolver] exact alias matched alias={alias} coin={symbol}"
                )
                return {"coin": symbol, "confidence": 1.0, "method": "exact_alias"}

    return None


def _score_fuzzy(candidate: str, alias: str) -> float:
    ratio = SequenceMatcher(None, candidate, alias).ratio()
    # Lift close matches into the operational acceptance band while keeping
    # clearly unrelated strings below the threshold.
    confidence = 1.0 - ((1.0 - ratio) * 0.4)
    return round(min(1.0, max(0.0, confidence)), 3)


def _match_fuzzy_candidates(message: str) -> dict[str, object] | None:
    candidates = _tokenize_candidates(message)
    if not candidates:
        return None

    best_scores: dict[str, float] = {}
    best_sources: dict[str, tuple[str, str]] = {}

    for candidate, candidate_kind in candidates:
        if candidate_kind == "ascii":
            if len(candidate) <= 3 and candidate not in _ALIAS_BY_LOWER:
                continue
            alias_pool = _ASCII_ALIAS_VALUES
        elif candidate_kind == "cjk":
            alias_pool = _CJK_ALIAS_VALUES
        elif candidate_kind == "mixed":
            alias_pool = _ALIAS_VALUES
        else:
            continue

        matches = get_close_matches(candidate, alias_pool, n=3, cutoff=0.6)
        if not matches:
            continue
        for alias_lower in matches:
            symbol = _ALIAS_BY_LOWER.get(alias_lower)
            if symbol is None:
                continue
            if abs(len(candidate) - len(alias_lower)) > 1:
                continue
            confidence = _score_fuzzy(candidate, alias_lower)
            if confidence < 0.9:
                continue
            current_best = best_scores.get(symbol, 0.0)
            if confidence > current_best:
                best_scores[symbol] = confidence
                best_sources[symbol] = (candidate, alias_lower)

    if not best_scores:
        return None

    sorted_candidates = sorted(
        best_scores.items(),
        key=lambda item: (item[1], item[0]),
        reverse=True,
    )
    payload = [
        {"coin": symbol, "score": score}
        for symbol, score in sorted_candidates
        if symbol in _SUPPORTED_COINS_SET
    ]
    if not payload:
        return None

    first_symbol, first_score = sorted_candidates[0]
    source_candidate, source_alias = best_sources[first_symbol]
    print(
        "[SemanticResolver] fuzzy candidates generated "
        f"candidate={source_candidate} alias={source_alias} coin={first_symbol} confidence={first_score}"
    )
    return {
        "coin": None,
        "confidence": 0.0,
        "method": "fuzzy_candidates",
        "candidates": payload,
    }


def resolve_coin_symbol(message: str) -> dict[str, object]:
    """Resolve a user message into a supported coin symbol."""

    exact_match = _match_exact_alias(message)
    if exact_match is not None:
        return exact_match

    fuzzy_candidates = _match_fuzzy_candidates(message)
    if fuzzy_candidates is not None:
        return fuzzy_candidates

    print(f"[SemanticResolver] no confident match message={message}")
    return _build_none_result()


def is_confident_coin_resolution(resolution: dict[str, object] | None) -> bool:
    """Return True when the resolver produced a supported exact or fuzzy coin match."""

    if not isinstance(resolution, dict):
        return False

    method = str(resolution.get("method") or "").strip().lower()
    coin = str(resolution.get("coin") or "").strip().upper()
    return method in {"exact_alias", "fuzzy"} and coin in _SUPPORTED_COINS_SET
