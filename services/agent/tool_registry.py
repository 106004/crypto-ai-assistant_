"""Tool registry scaffold.

Tool registry is the AI Agent's tool list.
This file keeps the mapping between an intent and the service function
that can handle it. It does not connect anything into LINE flow yet.
"""

from __future__ import annotations

from services.line.analysis_service import handle_analysis_query
from services.line.message_service import format_supported_coin_message
from services.line.onboarding_service import handle_mycoin, handle_set_coin
from services.line.price_service import handle_price_query


_INTENT_TO_TOOL = {
    "price_query": handle_price_query,
    "market_analysis": handle_analysis_query,
    "set_favorite_coin": handle_set_coin,
    "get_favorite_coin": handle_mycoin,
    "help": format_supported_coin_message,
}


def get_tool_for_intent(intent: str):
    """Return the service function for a supported intent, or None."""

    normalized_intent = str(intent or "").strip().lower()
    if not normalized_intent:
        return None

    return _INTENT_TO_TOOL.get(normalized_intent)


def list_available_tools():
    """Return the list of intents that currently have a registered tool."""

    return list(_INTENT_TO_TOOL.keys())
