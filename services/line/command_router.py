"""Central LINE command router."""

from __future__ import annotations

from services.agent.workflow_engine import run_agent_workflow
from services.line import onboarding_service
from services.line.line_facade_service import handle_coin_analysis, handle_coin_price
from services.line.message_service import (
    format_clarification_message,
    format_supported_coin_message,
    format_unknown_command_message,
)
from services.market.coin_catalog import get_coin_info, is_supported_coin


HELP_COMMANDS = {"help", "/help", "說明", "使用說明", "幫助"}
AGENT_PRICE_COMMANDS = {"btc", "eth", "sol", "bnb", "xrp", "doge", "ada", "ton", "trx", "avax"}
AGENT_ONBOARDING_COMMANDS = AGENT_PRICE_COMMANDS


def _route_agent_reply(user_id, normalized_message, branch_label):
    print(branch_label)
    try:
        agent_result = run_agent_workflow(user_id, normalized_message)
        intent = str(agent_result.get("intent") or "").strip().lower()
        if intent == "clarification_needed":
            print("[Clarification] returned to LINE")
            candidates = list(agent_result.get("candidates") or [])
            reason = str(agent_result.get("reason") or "low_confidence")
            message = str(agent_result.get("message") or "").strip()
            if not message:
                message = format_clarification_message(candidates, reason=reason)
            return message

        if intent == "unsupported_coin":
            message = str(agent_result.get("message") or "").strip()
            if message:
                return message

        if intent == "unknown":
            return format_unknown_command_message()

        result_message = agent_result.get("result")
        if result_message is not None:
            return result_message
        raise ValueError("agent workflow returned no result")
    except Exception as error:
        print("[Agent] fallback to legacy flow")
        print(f"[Agent] fallback error: {error}")
        return None


def _route_semantic_agent_fallback(user_id, normalized_message):
    print("[CommandRouter] fallback to Semantic Agent")
    agent_reply = _route_agent_reply(
        user_id,
        normalized_message,
        "[CommandRouter] fallback to Semantic Agent",
    )
    if agent_reply is not None:
        return agent_reply
    return format_unknown_command_message()


def _handoff_to_decision_engine(user_id, normalized_message):
    print("[CommandRouter] handoff to decision_engine")
    return _route_semantic_agent_fallback(user_id, normalized_message)


def route_user_message(user_id, user_message, event_type=None):
    normalized_message = str(user_message or "").strip().lower()
    print(f"[CommandRouter] incoming message: {normalized_message}")

    onboarding_reply = onboarding_service.get_onboarding_reply(user_id, event_type=event_type)
    if onboarding_reply is not None:
        print("[CommandRouter] route -> onboarding")
        return onboarding_reply

    if not normalized_message:
        return None

    parts = normalized_message.split()

    if len(parts) == 1 and parts[0] in AGENT_PRICE_COMMANDS:
        print("[CommandRouter] legacy fast path")
        agent_reply = _route_agent_reply(
            user_id,
            normalized_message,
            "[Agent] price_query routed to Agent workflow",
        )
        if agent_reply is not None:
            print("[Agent] price workflow success")
            return agent_reply
        print("[Agent] fallback to legacy price flow")
        print("[Agent] fallback error: agent workflow returned no result")
        return handle_coin_price(parts[0])

    if len(parts) == 2 and parts[0] == "analyze":
        coin_info = get_coin_info(parts[1])
        if coin_info is None:
            return _handoff_to_decision_engine(user_id, normalized_message)

        print("[CommandRouter] legacy fast path")
        agent_reply = _route_agent_reply(
            user_id,
            normalized_message,
            "[Agent] market_analysis routed to Agent workflow",
        )
        if agent_reply is not None:
            print("[Agent] analysis workflow success")
            return agent_reply
        print("[Agent] fallback to legacy analysis flow")
        print("[Agent] fallback error: agent workflow returned no result")
        return handle_coin_analysis(parts[1])

    if len(parts) == 2 and parts[0] == "set":
        if not is_supported_coin(parts[1]):
            return _handoff_to_decision_engine(user_id, normalized_message)

        print("[CommandRouter] legacy fast path")
        agent_reply = _route_agent_reply(
            user_id,
            normalized_message,
            "[Agent] set_favorite_coin routed to Agent workflow",
        )
        if agent_reply is not None:
            print("[Agent] onboarding workflow success")
            return agent_reply
        print("[Agent] fallback to legacy onboarding flow")
        print("[Agent] fallback error: agent workflow returned no result")
        return onboarding_service.handle_set_coin(user_id, parts[1])

    if len(parts) == 1 and parts[0] == "mycoin":
        print("[CommandRouter] legacy fast path")
        agent_reply = _route_agent_reply(
            user_id,
            normalized_message,
            "[Agent] get_favorite_coin routed to Agent workflow",
        )
        if agent_reply is not None:
            print("[Agent] onboarding workflow success")
            return agent_reply
        print("[Agent] fallback to legacy onboarding flow")
        print("[Agent] fallback error: agent workflow returned no result")
        return onboarding_service.handle_mycoin(user_id)

    if len(parts) == 1 and parts[0] in HELP_COMMANDS:
        print("[CommandRouter] legacy fast path")
        agent_reply = _route_agent_reply(
            user_id,
            normalized_message,
            "[Agent] help intent routed to Agent workflow",
        )
        if agent_reply is not None:
            print("[Agent] help workflow success")
            return agent_reply
        print("[Agent] fallback to legacy help")
        print("[Agent] fallback error: agent workflow returned no result")
        return format_supported_coin_message()

    return _handoff_to_decision_engine(user_id, normalized_message)
