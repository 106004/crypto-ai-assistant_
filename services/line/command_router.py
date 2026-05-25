"""Central LINE command router."""

from __future__ import annotations

from services.line.line_facade_service import handle_coin_analysis, handle_coin_price
from services.market.coin_catalog import get_coin_info, is_supported_coin


def _get_unknown_command_message():
    from line_bot import _supported_coin_text

    return _supported_coin_text()


def route_user_message(user_message):
    normalized_message = str(user_message or "").strip().lower()
    print(f"[CommandRouter] 收到訊息: {normalized_message}")

    if not normalized_message:
        return None

    parts = normalized_message.split()
    if len(parts) == 1 and is_supported_coin(parts[0]):
        print("[CommandRouter] route → price_service")
        return handle_coin_price(parts[0])

    if len(parts) == 2 and parts[0] == "analyze" and get_coin_info(parts[1]) is not None:
        print("[CommandRouter] route → analysis_service")
        return handle_coin_analysis(parts[1])

    if parts[0] in {"set", "mycoin"}:
        return None

    print("[CommandRouter] route → unknown_command")
    return _get_unknown_command_message()
