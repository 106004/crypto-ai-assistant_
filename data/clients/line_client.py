"""LINE Messaging API client helpers."""

from __future__ import annotations

import requests

from config import LINE_CHANNEL_ACCESS_TOKEN


LINE_REPLY_API_URL = "https://api.line.me/v2/bot/message/reply"
LINE_PUSH_API_URL = "https://api.line.me/v2/bot/message/push"


def _line_headers():
    if not LINE_CHANNEL_ACCESS_TOKEN:
        print("[LINEClient] missing LINE_CHANNEL_ACCESS_TOKEN")
        return None

    return {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }


def reply_message(reply_token, text):
    if not reply_token:
        print("[LINEClient] missing reply_token")
        return False

    headers = _line_headers()
    if headers is None:
        return False

    payload = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}],
    }

    try:
        response = requests.post(LINE_REPLY_API_URL, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
    except requests.RequestException as error:
        print(f"[LINEClient] reply failed: {error}")
        return False

    print("[LINEClient] reply sent")
    return True


def push_message(user_id, text):
    if not user_id:
        print("[LINEClient] missing user_id")
        return False

    headers = _line_headers()
    if headers is None:
        return False

    payload = {
        "to": user_id,
        "messages": [{"type": "text", "text": text}],
    }

    try:
        response = requests.post(LINE_PUSH_API_URL, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
    except requests.RequestException as error:
        print(f"[LINEClient] push failed for {user_id}: {error}")
        return False

    print(f"[LINEClient] push sent to {user_id}")
    return True
