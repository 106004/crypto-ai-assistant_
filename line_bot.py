"""LINE webhook entrypoint and legacy compatibility wrappers."""

from __future__ import annotations

import json

from data.clients.line_client import push_message, reply_message
from data.repositories.market_data_repository import get_market_data_by_symbol
from services.line import analysis_service, onboarding_service, price_service
from services.line.command_router import route_user_message
from services.line.message_service import format_supported_coin_message
from services.market.coin_catalog import SUPPORTED_COINS


def _supported_coin_text():
    return format_supported_coin_message()


def send_welcome_manual(reply_token, user_id=None):
    if user_id is None:
        return reply_message(reply_token, onboarding_service.get_welcome_message())

    success = reply_message(reply_token, onboarding_service.handle_new_user(user_id))
    return success


def _get_fresh_supabase_market_data(symbol, now_utc=None):
    return price_service.get_fresh_market_data(
        symbol,
        now_utc=now_utc,
        get_market_data_by_symbol_fn=get_market_data_by_symbol,
    )


def _handle_set_coin(user_id, reply_token, user_text):
    parts = str(user_text).split()
    if len(parts) != 2 or parts[0] != "set":
        return False

    coin = parts[1].strip().lower()
    if coin not in SUPPORTED_COINS:
        reply_message(reply_token, _supported_coin_text())
        return True

    reply_message(reply_token, onboarding_service.handle_set_coin(user_id, coin))
    return True


def _handle_mycoin(user_id, reply_token):
    reply_message(reply_token, onboarding_service.handle_mycoin(user_id))
    return True


def _handle_coin_price(reply_token, user_text):
    display_symbol = str(user_text).strip().upper()
    print(f"[PriceFlow] start {display_symbol}")
    reply_text = price_service.handle_price_query(
        display_symbol,
        get_market_data_by_symbol_fn=get_market_data_by_symbol,
    )
    reply_message(reply_token, reply_text)


def _handle_analyze_command(reply_token, user_text):
    parts = str(user_text).strip().lower().split()
    if len(parts) != 2 or parts[0] != "analyze":
        return False

    coin = parts[1]
    display_symbol = coin.upper()
    print(f"[Analyze] start analyze {display_symbol}")
    analysis_text = analysis_service.handle_analysis_query(
        display_symbol,
        get_market_data_by_symbol_fn=analysis_service.get_market_data_by_symbol,
        analyze_market_data_fn=analysis_service.analyze_market_data,
    )
    reply_message(reply_token, analysis_text)
    return True


def handle_webhook(request):
    webhook_data = request.get_json(silent=True) or {}

    print("[Webhook] received")
    print(json.dumps(webhook_data, ensure_ascii=False, indent=4))

    events = webhook_data.get("events")
    if not events:
        print("[Webhook] no events")
        return "OK"

    for event in events:
        source = event.get("source", {})
        user_id = source.get("userId")
        reply_token = event.get("replyToken")
        event_type = event.get("type")

        if not user_id:
            print("[Webhook] skip event without userId")
            continue

        message = event.get("message", {})
        user_text = str(message.get("text", "")).strip().lower()

        routed_reply = route_user_message(user_id, user_text, event_type=event_type)
        if routed_reply is not None and reply_token:
            reply_message(reply_token, routed_reply)
            continue

        if routed_reply is not None:
            print("[Webhook] routed reply dropped because reply_token is missing")
            continue

        if not user_text:
            print("[Webhook] empty text message")
            continue

        print("[Webhook] no reply generated")

    return "OK"
