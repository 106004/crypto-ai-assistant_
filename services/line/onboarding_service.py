"""LINE onboarding service."""

from __future__ import annotations

from user_manager import get_user, mark_user_onboarded, save_user, update_favorite_coin

from services.line.message_service import (
    format_daily_guide_message,
    format_missing_favorite_coin_message,
    format_mycoin_message,
    format_set_coin_success_message,
    format_welcome_message,
)


def get_welcome_message():
    return format_welcome_message()


def get_daily_guide_message():
    return format_daily_guide_message()


def get_missing_favorite_coin_message():
    return format_missing_favorite_coin_message()


def get_onboarding_reply(line_user_id, event_type=None):
    if not line_user_id:
        return None

    user = get_user(line_user_id)
    needs_welcome = event_type == "follow" or user is None or not bool(user.get("onboarded", False))

    if not needs_welcome:
        return None

    if user is None:
        save_user(line_user_id)

    mark_user_onboarded(line_user_id)
    print("[Onboarding] welcome sent")
    return get_welcome_message()


def handle_new_user(line_user_id):
    if not line_user_id:
        return get_welcome_message()

    reply_text = get_onboarding_reply(line_user_id)
    if reply_text is None:
        reply_text = get_welcome_message()
    return reply_text


def handle_set_coin(line_user_id, symbol):
    if not line_user_id:
        return format_set_coin_success_message(symbol)

    update_favorite_coin(line_user_id, symbol)
    print("[Onboarding] favorite coin updated")
    return format_set_coin_success_message(symbol)


def handle_mycoin(line_user_id):
    if not line_user_id:
        return get_missing_favorite_coin_message()

    user = get_user(line_user_id)
    favorite_coin = ""
    if isinstance(user, dict):
        favorite_coin = user.get("favorite_coin", "")

    print("[Onboarding] mycoin fetched")
    if not favorite_coin:
        return get_missing_favorite_coin_message()

    return format_mycoin_message(favorite_coin)
