"""LINE analysis query flow."""

from __future__ import annotations

from data.repositories.market_data_repository import get_market_data
from data.repositories.market_data_repository import get_market_data_by_symbol  # compatibility alias
from services.ai.market_analysis_service import analyze_market_data
from services.line.message_service import format_analysis_message
from services.market.freshness_service import is_market_data_fresh


STALE_ANALYSIS_MESSAGE = (
    "⚠️ 市場資料已過期\n\n"
    "目前系統不會使用超過 5 分鐘的舊資料進行分析，"
    "避免誤導。\n\n"
    "請稍後再試。"
)


def handle_analysis_query(symbol):
    display_symbol = str(symbol).strip().upper()
    print(f"[AnalysisService] 開始 analyze {display_symbol}")

    market_data = get_market_data_by_symbol(display_symbol)
    if not isinstance(market_data, dict):
        print("[AnalysisService] freshness: False")
        return STALE_ANALYSIS_MESSAGE

    print("[AnalysisService] market_data found")
    fresh = is_market_data_fresh(market_data)
    print(f"[AnalysisService] freshness: {fresh}")
    if not fresh:
        return STALE_ANALYSIS_MESSAGE

    print("[AnalysisService] 開始 AI analysis")
    analysis_text = analyze_market_data(market_data)
    print("[AnalysisService] analysis complete")
    return format_analysis_message(display_symbol, analysis_text)
