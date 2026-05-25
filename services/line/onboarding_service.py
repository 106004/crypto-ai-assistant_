"""LINE onboarding service."""

from __future__ import annotations

from data.repositories.user_repository import get_user, save_user
from utils.time_utils import get_utc_now

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


def _utc_now_iso():
    return get_utc_now().isoformat()


def _upsert_user(line_user_id, **updates):
    payload = {
        "line_user_id": line_user_id,
        "last_seen_at": _utc_now_iso(),
    }
    payload.update({key: value for key, value in updates.items() if value is not None})

    favorite_coin = payload.get("favorite_coin")
    if favorite_coin is not None:
        payload["favorite_coin"] = str(favorite_coin).strip().lower()

    onboarded_at = payload.get("onboarded_at")
    if onboarded_at is not None:
        payload["onboarded_at"] = str(onboarded_at)

    save_user(payload)
    return payload


def get_onboarding_reply(line_user_id, event_type=None):
    if not line_user_id:
        return None

    user = get_user(line_user_id)
    needs_welcome = event_type == "follow" or user is None or not bool(user.get("onboarded", False))

    if not needs_welcome:
        return None

    onboarded_at = None
    if isinstance(user, dict):
        onboarded_at = user.get("onboarded_at") or None

    _upsert_user(
        line_user_id,
        onboarded=True,
        onboarded_at=onboarded_at or _utc_now_iso(),
    )
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

    _upsert_user(
        line_user_id,
        favorite_coin=symbol,
        onboarded=True,
    )
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
