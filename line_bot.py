"""LINE webhook entrypoint."""

from __future__ import annotations

import json

from data.clients.line_client import push_message, reply_message
from services.line import onboarding_service
from services.line.command_router import route_user_message


def send_welcome_manual(reply_token, user_id=None):
    if user_id is None:
        return reply_message(reply_token, onboarding_service.get_welcome_message())

    success = reply_message(reply_token, onboarding_service.handle_new_user(user_id))
    return success


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
