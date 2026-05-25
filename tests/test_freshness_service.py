import unittest
from datetime import datetime, timedelta, timezone

from services.market.freshness_service import is_market_data_fresh


class FreshnessServiceTest(unittest.TestCase):
    def test_fresh_market_data_returns_true(self):
        now_utc = datetime.now(timezone.utc)
        market_data = {
            "symbol": "BTC",
            "updated_at": (now_utc - timedelta(seconds=30)).isoformat(),
        }

        result = is_market_data_fresh(market_data)
        self.assertTrue(result)
        print("[Test] fresh test passed")

    def test_stale_market_data_returns_false(self):
        now_utc = datetime.now(timezone.utc)
        market_data = {
            "symbol": "BTC",
            "updated_at": (now_utc - timedelta(minutes=6)).isoformat(),
        }

        result = is_market_data_fresh(market_data)
        self.assertFalse(result)
        print("[Test] stale test passed")

    def test_missing_updated_at_returns_false(self):
        market_data = {
            "symbol": "BTC",
        }

        result = is_market_data_fresh(market_data)

        self.assertFalse(result)
        print("[Test] missing updated_at test passed")


if __name__ == "__main__":
    unittest.main()
