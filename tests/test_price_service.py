import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from config.settings import MAX_MARKET_DATA_AGE_SECONDS
from services.line.price_service import handle_price_query


MARKET_DATA_AGE_MINUTES = MAX_MARKET_DATA_AGE_SECONDS // 60


class PriceServiceTest(unittest.TestCase):
    def test_fresh_market_data_returns_price_message(self):
        now_utc = datetime.now(timezone.utc)
        market_data = {
            "symbol": "BTC",
            "name": "Bitcoin",
            "price_usd": 100,
            "change_24h": 1.5,
            "source": "Supabase",
            "updated_at": (now_utc - timedelta(seconds=30)).isoformat(),
        }

        with patch(
            "services.line.price_service.get_market_data_by_symbol",
            return_value=market_data,
        ):
            result = handle_price_query("btc")

        self.assertIn("Bitcoin (BTC)", result)
        self.assertIn("價格：100.00 USD", result)
        self.assertIn("24H：+1.50%", result)
        self.assertIn("資料來源：Supabase", result)

    def test_stale_market_data_returns_single_coinglass_link(self):
        now_utc = datetime.now(timezone.utc)
        market_data = {
            "symbol": "BTC",
            "name": "Bitcoin",
            "price_usd": 100,
            "change_24h": 1.5,
            "source": "Supabase",
            "updated_at": (now_utc - timedelta(minutes=7)).isoformat(),
        }

        with patch(
            "services.line.price_service.get_market_data_by_symbol",
            return_value=market_data,
        ):
            result = handle_price_query("btc")

        self.assertIn(f"⚠️ BTC 價格資料超過 {MARKET_DATA_AGE_MINUTES} 分鐘", result)
        self.assertIn("https://www.coinglass.com/zh-TW/currencies/BTC", result)
        self.assertNotIn("AVAX", result)

    def test_missing_market_data_returns_single_coinglass_link(self):
        with patch(
            "services.line.price_service.get_market_data_by_symbol",
            return_value=None,
        ):
            result = handle_price_query("btc")

        self.assertIn(f"⚠️ BTC 價格資料超過 {MARKET_DATA_AGE_MINUTES} 分鐘", result)
        self.assertIn("https://www.coinglass.com/zh-TW/currencies/BTC", result)


if __name__ == "__main__":
    unittest.main()
