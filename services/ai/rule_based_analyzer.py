"""Rule-based fallback analysis for market data."""

from __future__ import annotations


AI_FALLBACK_PREFIX = "⚠️ AI 額度暫時不足，以下使用規則分析。"
INSUFFICIENT_DATA_MESSAGE = "目前資料不足，無法產生分析。"


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_change_percent(change_24h):
    sign = "+" if change_24h > 0 else ""
    return f"{sign}{change_24h:.1f}%"


def _format_price(price_usd):
    price = _to_float(price_usd)
    if price is None:
        return "N/A"
    return f"{price:g}"


def rule_based_analysis(coin_data):
    print("[Analyzer] 使用 rule_based_analysis")

    if not isinstance(coin_data, dict):
        return INSUFFICIENT_DATA_MESSAGE

    change_24h = _to_float(coin_data.get("change_24h"))
    if change_24h is None:
        return INSUFFICIENT_DATA_MESSAGE

    if change_24h >= 5:
        market_status = "強勢上漲"
        interpretation = "短線買盤明顯，但也要注意追高風險。"
    elif change_24h >= 2:
        market_status = "偏強"
        interpretation = "價格有上漲動能，但仍需觀察是否延續。"
    elif change_24h > -2:
        market_status = "震盪"
        interpretation = "價格變化不大，市場方向還不夠明確。"
    elif change_24h > -5:
        market_status = "偏弱"
        interpretation = "賣壓開始增加，短線操作要保守。"
    else:
        market_status = "明顯下跌"
        interpretation = "賣壓較強，短線波動風險較高。"

    symbol = str(coin_data.get("symbol") or "").strip().upper() or "UNKNOWN"
    price_text = _format_price(coin_data.get("price_usd"))

    return (
        f"{symbol} 市場簡易分析\n\n"
        f"價格：{price_text} USD\n"
        f"24H 漲跌：{_format_change_percent(change_24h)}\n\n"
        f"市場狀態：{market_status}\n\n"
        f"解讀：\n{interpretation}\n\n"
        "這是依照價格變化做的規則判斷，僅供參考。"
    )
