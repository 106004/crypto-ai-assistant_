"""Centralized configuration for crypto_ai_assistant.

Render Environment Variables are the cloud version of `.env`.
This module is the new configuration center.
The legacy `config.py` file is kept for compatibility so we can migrate
gradually without breaking existing imports.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

from services.market.coin_catalog import SUPPORTED_COINS as COIN_CATALOG


load_dotenv()


class Settings:
    """Centralized app settings with backward-compatible attribute names."""

    def __init__(self) -> None:
        self.LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        self.LINE_BOT_BASIC_ID = os.getenv("LINE_BOT_BASIC_ID")

        self.SUPABASE_URL = os.getenv("SUPABASE_URL")
        self.SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

        self.MAX_MARKET_DATA_AGE_SECONDS = 360
        self.GEMINI_MODEL = "gemini-2.5-flash"
        self.SUPPORTED_COINS = dict(COIN_CATALOG)
        self.DEFAULT_FAVORITE_COIN = "btc"

        # Convenience aliases for new code that prefers lowercase attributes.
        self.line_channel_access_token = self.LINE_CHANNEL_ACCESS_TOKEN
        self.line_bot_basic_id = self.LINE_BOT_BASIC_ID
        self.supabase_url = self.SUPABASE_URL
        self.supabase_service_role_key = self.SUPABASE_SERVICE_ROLE_KEY
        self.gemini_api_key = self.GEMINI_API_KEY
        self.max_market_data_age_seconds = self.MAX_MARKET_DATA_AGE_SECONDS
        self.gemini_model = self.GEMINI_MODEL
        self.supported_coins = self.SUPPORTED_COINS
        self.default_favorite_coin = self.DEFAULT_FAVORITE_COIN

        print("[Settings] configuration loaded")
        if not self.GEMINI_API_KEY:
            print("[Settings][WARNING] GEMINI_API_KEY missing")


settings = Settings()


LINE_CHANNEL_ACCESS_TOKEN = settings.LINE_CHANNEL_ACCESS_TOKEN
LINE_BOT_BASIC_ID = settings.LINE_BOT_BASIC_ID
SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY = settings.SUPABASE_SERVICE_ROLE_KEY
GEMINI_API_KEY = settings.GEMINI_API_KEY
MAX_MARKET_DATA_AGE_SECONDS = settings.MAX_MARKET_DATA_AGE_SECONDS
GEMINI_MODEL = settings.GEMINI_MODEL
SUPPORTED_COINS = settings.SUPPORTED_COINS
DEFAULT_FAVORITE_COIN = settings.DEFAULT_FAVORITE_COIN


__all__ = [
    "Settings",
    "settings",
    "LINE_CHANNEL_ACCESS_TOKEN",
    "LINE_BOT_BASIC_ID",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "GEMINI_API_KEY",
    "MAX_MARKET_DATA_AGE_SECONDS",
    "GEMINI_MODEL",
    "SUPPORTED_COINS",
    "DEFAULT_FAVORITE_COIN",
]
