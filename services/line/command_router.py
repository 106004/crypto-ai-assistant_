"""Central LINE command router."""

from __future__ import annotations

from services.line import onboarding_service
from services.line.line_facade_service import handle_coin_analysis, handle_coin_price
from services.line.message_service import format_unknown_command_message
from services.market.coin_catalog import get_coin_info, is_supported_coin


def route_user_message(user_id, user_message, event_type=None):
    normalized_message = str(user_message or "").strip().lower()
    print(f"[CommandRouter] 收到訊息: {normalized_message}")

    onboarding_reply = onboarding_service.get_onboarding_reply(user_id, event_type=event_type)
    if onboarding_reply is not None:
        print("[CommandRouter] route -> onboarding")
        return onboarding_reply

    if not normalized_message:
        return None

    parts = normalized_message.split()

    if len(parts) == 1 and is_supported_coin(parts[0]):
        print("[CommandRouter] route -> price_service")
        return handle_coin_price(parts[0])

    if len(parts) == 2 and parts[0] == "analyze" and get_coin_info(parts[1]) is not None:
        print("[CommandRouter] route -> analysis_service")
        return handle_coin_analysis(parts[1])

    if len(parts) == 2 and parts[0] == "set":
        print("[CommandRouter] route -> onboarding set coin")
        if not is_supported_coin(parts[1]):
            return format_unknown_command_message()
        return onboarding_service.handle_set_coin(user_id, parts[1])

    if len(parts) == 1 and parts[0] == "mycoin":
        print("[CommandRouter] route -> onboarding mycoin")
        return onboarding_service.handle_mycoin(user_id)

    print("[CommandRouter] route -> unknown_command")
    return format_unknown_command_message()
