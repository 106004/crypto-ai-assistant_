import json
from datetime import datetime, timezone

import requests

from config import LINE_CHANNEL_ACCESS_TOKEN
from crypto_api import (
    MARKET_DATA_MAX_AGE_SECONDS,
    SUPPORTED_COINS,
    get_coinglass_fallback_message,
)
from data.repositories.market_data_repository import get_market_data_by_symbol
from market_analyzer import analyze_market_data
from services.line.onboarding_service import handle_mycoin as onboarding_handle_mycoin
from services.line.onboarding_service import handle_set_coin as onboarding_handle_set_coin
from services.line.command_router import route_user_message
from services.line import analysis_service, price_service
from services.line.message_service import format_analysis_message, format_price_message
from user_manager import get_user, mark_user_onboarded, save_user, update_favorite_coin


# LINE Reply API：只能用在 webhook 收到事件後，用 replyToken 立刻回覆使用者。
LINE_REPLY_API_URL = "https://api.line.me/v2/bot/message/reply"

# LINE Push API：可以主動推播給已經加好友或互動過的使用者。
LINE_PUSH_API_URL = "https://api.line.me/v2/bot/message/push"

WELCOME_MANUAL_TEXT = """歡迎使用 Crypto AI Assistant

你可以輸入以下指令：

btc
查詢 Bitcoin 價格

eth
查詢 Ethereum 價格

set btc
設定你最愛的幣種

mycoin
查看你目前設定的最愛幣種

之後系統會依照你的設定，提供加密貨幣資訊提醒。"""

DAILY_MANUAL_TEXT = """Crypto AI Assistant 每日提醒

你可以輸入：
btc / eth / sol 查詢幣價
set btc 設定最愛幣種
mycoin 查看你的設定

之後你也可以把這個 Bot 當作自己的加密貨幣小助理。"""


def _line_headers():
    """準備呼叫 LINE API 需要的 headers；如果 token 不存在就回傳 None。"""

    # 這裡不要 raise exception，因為開發者可能還沒設定 .env。
    # 缺 token 時只印白話錯誤，讓 Flask webhook 不會整個崩潰。
    if not LINE_CHANNEL_ACCESS_TOKEN:
        print("找不到 LINE_CHANNEL_ACCESS_TOKEN，請先在 .env 設定 LINE Bot 的 Channel access token。")
        return None

    return {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }


def _supported_coin_text():
    """產生支援幣種提示文字。"""

    coin_list = " / ".join(SUPPORTED_COINS.keys())
    return (
        "目前支援的幣種：\n"
        f"{coin_list}\n\n"
        "你可以輸入 btc 查詢價格，或輸入 set btc 設定最愛幣種。"
    )


def _format_coin_message(coin_data):
    """把 crypto_api.py 回傳的資料整理成 LINE 文字訊息。"""

    change_24h = float(coin_data["change_24h"])
    change_text = f"{change_24h:+.2f}%"
    price_text = f"{float(coin_data['price_usd']):,.2f}"
    source = "Supabase"
    updated_at = coin_data.get("updated_at", "未知")

    return (
        f"幣種名稱：{coin_data['name']} ({coin_data['symbol']})\n"
        f"價格：{price_text} USD\n"
        f"24H 漲跌：{change_text}\n"
        f"updated_at：{updated_at}\n"
        f"資料來源：{source}"
    )

def _parse_market_data_updated_at_utc(updated_at):
    if isinstance(updated_at, datetime):
        parsed = updated_at
    else:
        value = str(updated_at).strip()
        if value.endswith("Z"):
            value = f"{value[:-1]}+00:00"
        parsed = datetime.fromisoformat(value)

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def _check_supabase_market_data_freshness(symbol, updated_at, now_utc=None):
    now_utc = now_utc or datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    else:
        now_utc = now_utc.astimezone(timezone.utc)

    print(f"[Freshness] {symbol} updated_at 原始值：{updated_at}")
    updated_time = _parse_market_data_updated_at_utc(updated_at)
    age_seconds = max(0, (now_utc - updated_time).total_seconds())
    age_minutes = age_seconds / 60
    fresh = age_seconds <= MARKET_DATA_MAX_AGE_SECONDS

    print(f"[Freshness] {symbol} parsed updated_at UTC：{updated_time.isoformat()}")
    print(f"[Freshness] 系統現在 UTC：{now_utc.isoformat()}")
    print(f"[Freshness] 資料年齡：{age_minutes:.1f} 分鐘")
    print("[Freshness] freshness limit：5 分鐘")
    print(f"[Freshness] fresh：{fresh}")

    if fresh:
        print(f"[Freshness] {symbol} 資料新鮮，資料年齡：{age_minutes:.1f} 分鐘")
    else:
        print(f"[Freshness] {symbol} 資料已過期，資料年齡：{age_minutes:.1f} 分鐘，超過限制：5 分鐘，放棄使用 Supabase 價格")

    return {
        "fresh": fresh,
        "age_seconds": age_seconds,
        "age_minutes": age_minutes,
        "updated_at_utc": updated_time,
        "now_utc": now_utc,
    }


def _get_fresh_supabase_market_data(symbol, now_utc=None):
    coin_data = get_market_data_by_symbol(symbol)
    if not isinstance(coin_data, dict):
        print(f"[Freshness] {symbol} 在 Supabase 沒有資料，提供 CoinGlass fallback links")
        return None

    try:
        freshness = _check_supabase_market_data_freshness(symbol, coin_data.get("updated_at"), now_utc=now_utc)
    except (TypeError, ValueError) as error:
        print(f"[Freshness] {symbol} updated_at 解析失敗：{error}")
        print(f"[Freshness] {symbol} 資料已過期，資料年齡：未知，超過限制：5 分鐘，放棄使用 Supabase 價格")
        return None

    if not freshness["fresh"]:
        return None

    result = dict(coin_data)
    result["source"] = "Supabase"
    result["_age_minutes"] = freshness["age_minutes"]
    return result


def reply_message(reply_token, text):
    """使用 LINE Reply API 回覆文字訊息。"""

    if not reply_token:
        print("沒有 replyToken，無法使用 LINE Reply API 回覆訊息。")
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
        print(f"呼叫 LINE Reply API 失敗，請檢查 token、webhook 或網路設定：{error}")
        return False

    print("已使用 LINE Reply API 回覆訊息。")
    return True


def push_message(user_id, text):
    """使用 LINE Push API 主動推播文字訊息給指定使用者。"""

    if not user_id:
        print("沒有 user_id，無法使用 LINE Push API 推播。")
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
        print(f"推播給 {user_id} 失敗，請確認使用者是否已加入好友、token 是否正確：{error}")
        return False

    print(f"已推播每日提醒給 {user_id}。")
    return True


def send_welcome_manual(reply_token, user_id=None):
    """第一次使用或第一次加入時，用 Reply API 傳送使用說明書。"""

    success = reply_message(reply_token, WELCOME_MANUAL_TEXT)

    # 題目要求成功後標記 onboarded。
    # 函式主要參數保留 reply_token；user_id 用選填，是為了能真正更新該使用者資料。
    if success and user_id:
        mark_user_onboarded(user_id)

    return success


def _handle_set_coin(user_id, reply_token, user_text):
    """處理 set btc / set eth / set sol 這類設定最愛幣種的指令。"""

    parts = user_text.split()
    if len(parts) != 2 or parts[0] != "set":
        return False

    coin = parts[1].strip().lower()
    if coin not in SUPPORTED_COINS:
        reply_message(reply_token, f"目前不支援 {coin.upper()}。\n\n{_supported_coin_text()}")
        return True

    update_favorite_coin(user_id, coin)
    reply_message(reply_token, f"✅ 已設定你最愛的幣種為 {coin.upper()}")
    return True


def _handle_mycoin(user_id, reply_token):
    """處理 mycoin 指令，顯示使用者目前設定的最愛幣種。"""

    user = get_user(user_id)
    favorite_coin = ""

    if user:
        favorite_coin = user.get("favorite_coin", "")

    if not favorite_coin:
        reply_message(
            reply_token,
            "你目前還沒有設定最愛幣種。\n請輸入：\nset btc",
        )
        return

    reply_message(reply_token, f"你目前設定的最愛幣種是 {favorite_coin.upper()}")


def _handle_coin_price(reply_token, user_text):
    """Handle supported coin price lookup from Supabase market_data only."""

    display_symbol = str(user_text).strip().upper()
    print(f"[PriceFlow] ???{display_symbol}")
    print("[PriceFlow] ?? Supabase")

    coin_data = _get_fresh_supabase_market_data(display_symbol)
    is_fresh = coin_data is not None
    print(f"[PriceFlow] Supabase fresh?{is_fresh}")
    if coin_data is not None:
        print(f"[PriceFlow] ?????{coin_data.get('_age_minutes', 0):.1f} ??")
    else:
        print("[PriceFlow] ???????")
    print("[PriceFlow] ??? JSON fallback")
    print("[PriceFlow] ????? API ??")

    price_service.get_market_data_by_symbol = get_market_data_by_symbol
    reply_text = price_service.handle_price_query(display_symbol)
    reply_message(reply_token, reply_text)


def _handle_analyze_command(reply_token, user_text):
    """Handle analyze btc / analyze eth style market analysis commands."""

    parts = str(user_text).strip().lower().split()
    if len(parts) != 2 or parts[0] != "analyze":
        return False

    coin = parts[1]
    if coin not in SUPPORTED_COINS:
        reply_message(reply_token, _supported_coin_text())
        return True

    display_symbol = coin.upper()
    print(f"[Analyze] ?? analyze ???{display_symbol}")
    print("[Analyze] ???? Supabase market_data")

    analysis_text = analysis_service.handle_analysis_query(display_symbol)
    reply_message(reply_token, analysis_text)
    return True

def handle_webhook(request):
    """處理 LINE webhook request，這是 app.py /callback 會呼叫的入口。"""

    webhook_data = request.get_json(silent=True) or {}

    # 開發階段印出 LINE 傳來的 JSON，方便確認事件格式。
    print("收到 webhook JSON：")
    print(json.dumps(webhook_data, ensure_ascii=False, indent=4))

    events = webhook_data.get("events")
    if not events:
        print("這次 webhook 沒有 events，直接回 OK 給 LINE。")
        return "OK"

    # LINE 有時一次會送多個 event，所以這裡逐筆處理。
    for event in events:
        source = event.get("source", {})
        user_id = source.get("userId")
        reply_token = event.get("replyToken")

        if not user_id:
            print("這筆 event 沒有 userId，可能是群組或特殊事件，先略過。")
            continue

        # save_user 之前先查一次，才能判斷是不是第一次看到這個 user_id。
        existing_user = get_user(user_id)
        is_first_time_user = existing_user is None
        needs_onboarding = is_first_time_user or not existing_user.get("onboarded", False)

        save_user(user_id)
        print(f"已記錄使用者：{user_id}")

        event_type = event.get("type")

        # 第一次加入好友、第一次傳訊息，或舊資料尚未 onboarded，都先送使用說明。
        # Reply API 一個 replyToken 只能用一次，所以送完說明書後就不再同時回覆其他內容。
        if needs_onboarding and reply_token:
            send_welcome_manual(reply_token, user_id)
            continue

        # follow 是使用者加入好友的事件，通常沒有 message text。
        if event_type == "follow":
            send_welcome_manual(reply_token, user_id)
            continue

        message = event.get("message", {})
        user_text = str(message.get("text", "")).strip().lower()

        if not user_text:
            print("這筆 event 不是文字訊息，或文字內容是空的。")
            continue

        routed_reply = route_user_message(user_text)
        if routed_reply is not None:
            reply_message(reply_token, routed_reply)
            continue

        if _handle_set_coin(user_id, reply_token, user_text):
            continue

        if user_text == "mycoin":
            reply_message(reply_token, onboarding_handle_mycoin(user_id))
            continue

        if _handle_analyze_command(reply_token, user_text):
            continue

        if user_text in SUPPORTED_COINS:
            _handle_coin_price(reply_token, user_text)
            continue

        reply_message(reply_token, _supported_coin_text())

    return "OK"

