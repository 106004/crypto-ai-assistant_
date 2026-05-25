"""LINE onboarding service."""

from __future__ import annotations

from data.repositories.user_repository import get_user, save_user, update_user_coin


WELCOME_MESSAGE = """歡迎使用 Crypto AI Assistant

你可以輸入：

btc
查詢 Bitcoin 價格

eth
查詢 Ethereum 價格

set btc
設定你的最愛幣種

mycoin
查看你目前設定的幣種

如果你是第一次使用，先輸入 btc 試試看。"""


def handle_new_user(line_user_id):
    user = get_user(line_user_id)
    if user is None:
        save_user({"line_user_id": line_user_id, "favorite_coin": "btc"})
        print("[Onboarding] new user created")
    return WELCOME_MESSAGE


def handle_set_coin(line_user_id, symbol):
    update_user_coin(line_user_id, symbol)
    print("[Onboarding] favorite coin updated")
    return f"✅ 已設定你最愛的幣種為 {str(symbol).strip().upper()}"


def handle_mycoin(line_user_id):
    user = get_user(line_user_id)
    favorite_coin = ""
    if isinstance(user, dict):
        favorite_coin = user.get("favorite_coin", "")

    print("[Onboarding] mycoin fetched")
    if not favorite_coin:
        return "你目前還沒有設定最愛幣種。\n請輸入：\nset btc"

    return f"你目前設定的最愛幣種是 {str(favorite_coin).strip().upper()}"
