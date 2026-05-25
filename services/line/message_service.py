"""LINE message formatting helpers."""

from __future__ import annotations

from crypto_api import get_coinglass_fallback_message


def format_price_message(coin_data):
    print("[MessageService] format price message")

    change_24h = float(coin_data["change_24h"])
    change_text = f"{change_24h:+.2f}%"
    price_text = f"{float(coin_data['price_usd']):,.2f}"
    source = "Supabase"
    updated_at = coin_data.get("updated_at", "?")

    return (
        f"{coin_data['name']} ({coin_data['symbol']})\n"
        f"價格：{price_text} USD\n"
        f"24H 漲跌：{change_text}\n"
        f"updated_at：{updated_at}\n"
        f"資料來源：{source}"
    )


def format_analysis_message(symbol, analysis_text):
    print("[MessageService] format analysis message")
    return f"{str(symbol).strip().upper()} AI 市場分析\n\n{analysis_text}"


def format_stale_data_message(symbol, coinglass_url):
    print("[MessageService] format stale message")
    return get_coinglass_fallback_message()
