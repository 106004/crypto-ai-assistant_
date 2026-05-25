"""LINE message formatting helpers."""

from __future__ import annotations

from crypto_api import get_coinglass_fallback_message
from services.market.coin_catalog import SUPPORTED_COINS, get_coinglass_url


SUPPORTED_COIN_LIST = " / ".join(SUPPORTED_COINS.keys())


def _usage_guide_header(title):
    return (
        f"{title}\n\n"
        "查價格：btc / eth / sol\n"
        "支援 10 種幣：btc / eth / sol / bnb / xrp / doge / ada / ton / trx / avax\n"
        "AI 分析：analyze btc\n"
        "設定最愛幣：set btc\n"
        "查詢最愛幣：mycoin\n"
        "資料規則：超過 5 分鐘的價格不會回覆舊資料\n"
        "異常時：會提供 CoinGlass 即時行情連結\n"
        "提醒：這不是投資建議"
    )


def format_welcome_message():
    return _usage_guide_header("歡迎使用 Crypto AI Assistant")


def format_daily_guide_message():
    return _usage_guide_header("Crypto AI Assistant 每日提醒")


def format_supported_coin_message():
    return (
        "目前支援的幣種：\n"
        f"{SUPPORTED_COIN_LIST}\n\n"
        "查價格：btc / eth / sol\n"
        "AI 分析：analyze btc\n"
        "設定最愛幣：set btc\n"
        "查詢最愛幣：mycoin\n"
        "提醒：這不是投資建議"
    )


def format_unknown_command_message():
    return format_supported_coin_message()


def format_missing_favorite_coin_message():
    return (
        "你目前還沒有設定最愛幣。\n\n"
        "你可以使用：set btc / set eth / set sol\n"
        f"支援幣種：{SUPPORTED_COIN_LIST}\n"
        "也可以輸入 mycoin 查看目前設定。\n"
        "提醒：這不是投資建議"
    )


def format_set_coin_success_message(symbol):
    display_symbol = str(symbol).strip().upper() or "UNKNOWN"
    return f"✅ 已設定你最愛的幣種為 {display_symbol}"


def format_mycoin_message(symbol):
    display_symbol = str(symbol).strip().upper() or "UNKNOWN"
    return f"你目前設定的最愛幣種是 {display_symbol}"


def format_coin_glass_link_message(symbol, headline, body):
    display_symbol = str(symbol).strip().upper() or "UNKNOWN"
    coinglass_url = get_coinglass_url(display_symbol)
    if coinglass_url is None:
        return get_coinglass_fallback_message()

    return f"{headline}\n\n{body}\n\nCoinGlass 即時行情：\n{coinglass_url}"


def format_analysis_stale_message(symbol):
    return format_coin_glass_link_message(
        symbol,
        "⚠️ 資訊超過 5 分鐘，AI 無法分析。",
        (
            "因為價格資料具有即時性，\n"
            "系統不會使用過期資料產生分析，避免誤導。\n\n"
            "請稍後再試，或查看 CoinGlass 即時行情。"
        ),
    )


def format_price_message(coin_data):
    print("[MessageService] format price message")

    change_24h = float(coin_data["change_24h"])
    change_text = f"{change_24h:+.2f}%"
    price_text = f"{float(coin_data['price_usd']):,.2f}"
    updated_at = coin_data.get("updated_at", "?")

    return (
        f"{coin_data['name']} ({coin_data['symbol']})\n"
        f"價格：{price_text} USD\n"
        f"24H：{change_text}\n"
        f"updated_at：{updated_at}\n"
        "資料來源：Supabase"
    )


def format_analysis_message(symbol, analysis_text):
    print("[MessageService] format analysis message")
    return f"{str(symbol).strip().upper()} AI 分析\n\n{analysis_text}"


def format_stale_data_message(symbol, coinglass_url=None):
    print("[MessageService] format stale message")
    display_symbol = str(symbol).strip().upper() or "UNKNOWN"
    headline = f"⚠️ {display_symbol} 價格資料超過 5 分鐘"
    body = "系統不會推播過期價格，避免誤導。\n你可以查看 CoinGlass 即時行情："

    if coinglass_url:
        return f"{headline}\n\n{body}\n{coinglass_url}"

    return format_coin_glass_link_message(display_symbol, headline, body)
