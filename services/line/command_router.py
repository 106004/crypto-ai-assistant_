"""Central LINE command router."""

from __future__ import annotations

from services.agent.workflow_engine import run_agent_workflow
from services.line import onboarding_service
from services.line.line_facade_service import handle_coin_analysis, handle_coin_price
from services.line.message_service import format_supported_coin_message, format_unknown_command_message
from services.market.coin_catalog import get_coin_info, is_supported_coin


HELP_COMMANDS = {"help", "/help", "說明", "使用說明", "隤芣?", "雿輻隤芣?"}
AGENT_PRICE_COMMANDS = {"btc", "eth", "sol", "bnb", "xrp", "doge", "ada", "ton", "trx", "avax"}
AGENT_ONBOARDING_COMMANDS = AGENT_PRICE_COMMANDS


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
        print("[Agent] price_query routed to Agent workflow")
        try:
            agent_result = run_agent_workflow(user_id, normalized_message)
            print("[Agent] price workflow success")
            price_message = agent_result.get("result")
            if price_message is not None:
                return price_message
            raise ValueError("price workflow returned no result")
        except Exception as error:
            print("[Agent] fallback to legacy price flow")
            print(f"[Agent] fallback error: {error}")
            return handle_coin_price(parts[0])

    if len(parts) == 2 and parts[0] == "analyze" and get_coin_info(parts[1]) is not None:
        if parts[1] in AGENT_PRICE_COMMANDS:
            print("[Agent] market_analysis routed to Agent workflow")
            try:
                agent_result = run_agent_workflow(user_id, normalized_message)
                print("[Agent] analysis workflow success")
                analysis_message = agent_result.get("result")
                if analysis_message is not None:
                    return analysis_message
                raise ValueError("analysis workflow returned no result")
            except Exception as error:
                print("[Agent] fallback to legacy analysis flow")
                print(f"[Agent] fallback error: {error}")
                return handle_coin_analysis(parts[1])

        print("[CommandRouter] route -> analysis_service")
        return handle_coin_analysis(parts[1])

    if len(parts) == 2 and parts[0] == "set":
        if not is_supported_coin(parts[1]):
            print("[CommandRouter] route -> unknown_command")
            return format_unknown_command_message()

        if parts[1] in AGENT_ONBOARDING_COMMANDS:
            print("[Agent] set_favorite_coin routed to Agent workflow")
            try:
                agent_result = run_agent_workflow(user_id, normalized_message)
                print("[Agent] onboarding workflow success")
                onboarding_message = agent_result.get("result")
                if onboarding_message is not None:
                    return onboarding_message
                raise ValueError("onboarding workflow returned no result")
            except Exception as error:
                print("[Agent] fallback to legacy onboarding flow")
                print(f"[Agent] fallback error: {error}")
                return onboarding_service.handle_set_coin(user_id, parts[1])

        print("[CommandRouter] route -> onboarding set coin")
        return onboarding_service.handle_set_coin(user_id, parts[1])

    if len(parts) == 1 and parts[0] == "mycoin":
        print("[Agent] get_favorite_coin routed to Agent workflow")
        try:
            agent_result = run_agent_workflow(user_id, normalized_message)
            print("[Agent] onboarding workflow success")
            onboarding_message = agent_result.get("result")
            if onboarding_message is not None:
                return onboarding_message
            raise ValueError("onboarding workflow returned no result")
        except Exception as error:
            print("[Agent] fallback to legacy onboarding flow")
            print(f"[Agent] fallback error: {error}")
            return onboarding_service.handle_mycoin(user_id)

    if len(parts) == 1 and parts[0] in HELP_COMMANDS:
        print("[Agent] help intent routed to Agent workflow")
        try:
            agent_result = run_agent_workflow(user_id, normalized_message)
            print("[Agent] help workflow success")
            help_message = agent_result.get("result")
            if help_message is not None:
                return help_message
            raise ValueError("help workflow returned no result")
        except Exception as error:
            print("[Agent] fallback to legacy help")
            print(f"[Agent] fallback error: {error}")
            return format_supported_coin_message()

    print("[CommandRouter] route -> unknown_command")
    return format_unknown_command_message()
