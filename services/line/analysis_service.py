"""LINE analysis query flow."""

from __future__ import annotations

from data.repositories.market_data_repository import get_market_data_by_symbol  # compatibility alias
from services.ai.market_analysis_service import analyze_market_data
from services.line.message_service import (
    format_analysis_message,
    format_analysis_stale_message,
)
from services.line.price_service import get_fresh_market_data


STALE_ANALYSIS_MESSAGE = format_analysis_stale_message("BTC")


def handle_analysis_query(
    symbol,
    get_market_data_by_symbol_fn=None,
    analyze_market_data_fn=None,
    now_utc=None,
):
    display_symbol = str(symbol).strip().upper()
    print(f"[AnalysisService] start analyze {display_symbol}")

    get_market_data_by_symbol_fn = get_market_data_by_symbol_fn or get_market_data_by_symbol

    market_data = get_fresh_market_data(
        display_symbol,
        now_utc=now_utc,
        get_market_data_by_symbol_fn=get_market_data_by_symbol_fn,
    )
    if not isinstance(market_data, dict):
        print("[AnalysisService] market data stale, skip AI analysis")
        print("[AnalysisService] provide CoinGlass link")
        return format_analysis_stale_message(display_symbol)

    print("[AnalysisService] market_data found")
    print("[AnalysisService] freshness: True")
    print("[AnalysisService] start Gemini analysis")

    analyze_market_data_fn = analyze_market_data_fn or analyze_market_data
    analysis_text = analyze_market_data_fn(market_data)
    print("[AnalysisService] analysis complete")
    return format_analysis_message(display_symbol, analysis_text)
