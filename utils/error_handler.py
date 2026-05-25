"""Lightweight backend error handling helpers."""

from __future__ import annotations

from utils.logger import log_error


def format_exception_message(error):
    message = str(error).strip()
    if not message:
        return "發生未知錯誤，請稍後再試。"

    lowered = message.lower()
    if "quota" in lowered:
        return "Gemini 額度暫時不足，請稍後再試。"
    if "supabase" in lowered:
        return "Supabase 資料讀取失敗，請稍後再試。"
    if "coingecko" in lowered:
        return "CoinGecko 資料讀取失敗，請稍後再試。"

    return "系統暫時發生錯誤，請稍後再試。"


def safe_execute(func, fallback=None):
    try:
        return func()
    except Exception as error:
        log_error("ErrorHandler", str(error))
        return fallback
