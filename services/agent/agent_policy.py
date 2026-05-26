"""Agent policy layer.

This is the Agent's safety and control gate.
It decides whether an intent is allowed to execute before the workflow
actually runs the underlying service tool.
"""

from __future__ import annotations


def should_execute_intent(intent: str, context: dict | None = None):
    """Decide whether the agent should execute a given intent.

    The first version is rule-based only. It is intentionally small so we can
    add more policy checks later for safety, rate limiting, and anti-spam.
    """

    normalized_intent = str(intent or "").strip().lower()
    context = dict(context or {})
    print(f"[AgentPolicy] checking intent: {normalized_intent}")

    if normalized_intent == "market_analysis" and context.get("market_data_fresh") is False:
        print("[AgentPolicy] blocked market_analysis")
        print("[AgentPolicy] fallback: coinglass_fallback")
        return {
            "allowed": False,
            "reason": "stale_market_data",
            "fallback_action": "coinglass_fallback",
        }

    return {
        "allowed": True,
        "reason": "allowed",
        "fallback_action": "",
    }
