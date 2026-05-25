import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from services.line.price_service import handle_price_query


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
        self.assertIn("24H 漲跌：+1.50%", result)
        self.assertIn("資料來源：Supabase", result)
        print("[Test] fresh price query passed")

    def test_stale_market_data_returns_coinglass_fallback(self):
        now_utc = datetime.now(timezone.utc)
        market_data = {
            "symbol": "BTC",
            "name": "Bitcoin",
            "price_usd": 100,
            "change_24h": 1.5,
            "source": "Supabase",
            "updated_at": (now_utc - timedelta(minutes=6)).isoformat(),
        }

        with patch(
            "services.line.price_service.get_market_data_by_symbol",
            return_value=market_data,
        ), patch(
            "services.line.message_service.get_coinglass_fallback_message",
            return_value="COINGLASS_FALLBACK",
        ):
            result = handle_price_query("btc")

        self.assertEqual(result, "COINGLASS_FALLBACK")
        print("[Test] stale fallback passed")

    def test_missing_market_data_returns_coinglass_fallback(self):
        with patch(
            "services.line.price_service.get_market_data_by_symbol",
            return_value=None,
        ), patch(
            "services.line.message_service.get_coinglass_fallback_message",
            return_value="COINGLASS_FALLBACK",
        ):
            result = handle_price_query("btc")

        self.assertEqual(result, "COINGLASS_FALLBACK")
        print("[Test] missing market data passed")


if __name__ == "__main__":
    unittest.main()
