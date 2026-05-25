"""LINE domain facade for coin price and analysis flows."""

from __future__ import annotations

from services.line.analysis_service import handle_analysis_query
from services.line.price_service import handle_price_query


def handle_coin_price(symbol):
    display_symbol = str(symbol).strip().upper()
    print(f"[LineFacade] handle price {display_symbol}")
    return handle_price_query(display_symbol)


def handle_coin_analysis(symbol):
    display_symbol = str(symbol).strip().upper()
    print(f"[LineFacade] handle analysis {display_symbol}")
    return handle_analysis_query(display_symbol)
