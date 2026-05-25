"""Build prompts for Gemini market analysis."""

from __future__ import annotations


def build_market_analysis_prompt(coin_data):
    coin_data = coin_data or {}
    symbol = str(coin_data.get("symbol") or "").strip().upper() or "UNKNOWN"
    price_usd = coin_data.get("price_usd")
    change_24h = coin_data.get("change_24h")
    updated_at = coin_data.get("updated_at")

    return (
        "請用繁體中文輸出市場分析。\n"
        "內容簡短。\n"
        "不要超過 120 字。\n"
        "不要誇張。\n"
        "不保證投資。\n"
        "最後加：這不是投資建議。\n"
        f"symbol：{symbol}\n"
        f"價格：{price_usd}\n"
        f"24H 漲跌：{change_24h}\n"
        f"price_usd：{price_usd}\n"
        f"change_24h：{change_24h}\n"
        f"updated_at：{updated_at}\n"
        "請根據以上資料給出一段精簡分析。"
    )
