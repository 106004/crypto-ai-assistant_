import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from services.ai import market_analysis_service
from services.line.analysis_service import STALE_ANALYSIS_MESSAGE, handle_analysis_query


class AnalysisServiceTest(unittest.TestCase):
    def test_fresh_market_data_returns_analysis_text(self):
        now_utc = datetime.now(timezone.utc)
        market_data = {
            "symbol": "BTC",
            "name": "Bitcoin",
            "price_usd": 100,
            "change_24h": 2.3,
            "source": "Supabase",
            "updated_at": (now_utc - timedelta(seconds=30)).isoformat(),
        }

        with patch(
            "services.line.analysis_service.get_market_data_by_symbol",
            return_value=market_data,
        ), patch(
            "services.line.analysis_service.is_market_data_fresh",
            return_value=True,
        ), patch(
            "services.line.analysis_service.analyze_market_data",
            return_value="ANALYSIS_TEXT",
        ):
            result = handle_analysis_query("btc")

        self.assertIn("BTC AI 市場分析", result)
        self.assertIn("ANALYSIS_TEXT", result)
        print("[Test] fresh analysis passed")

    def test_stale_market_data_returns_stale_message(self):
        now_utc = datetime.now(timezone.utc)
        market_data = {
            "symbol": "BTC",
            "name": "Bitcoin",
            "price_usd": 100,
            "change_24h": 2.3,
            "source": "Supabase",
            "updated_at": (now_utc - timedelta(minutes=6)).isoformat(),
        }

        with patch(
            "services.line.analysis_service.get_market_data_by_symbol",
            return_value=market_data,
        ), patch(
            "services.line.analysis_service.is_market_data_fresh",
            return_value=False,
        ):
            result = handle_analysis_query("btc")

        self.assertEqual(result, STALE_ANALYSIS_MESSAGE)
        print("[Test] stale analysis blocked passed")

    def test_gemini_failure_falls_back_to_rule_based_analysis(self):
        class FakeResponse:
            text = "unused"

        class FakeModels:
            def generate_content(self, model, contents):
                raise RuntimeError("boom")

        class FakeClient:
            def __init__(self):
                self.models = FakeModels()

        coin_data = {
            "symbol": "BTC",
            "name": "Bitcoin",
            "price_usd": 100,
            "change_24h": 2.3,
            "source": "Supabase",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        with patch(
            "market_analyzer.get_gemini_client",
            return_value=FakeClient(),
        ), patch(
            "services.ai.market_analysis_service.rule_based_analysis",
            return_value="RULE_BASED_TEXT",
        ):
            result = market_analysis_service.analyze_market_data(coin_data)

        self.assertIn("RULE_BASED_TEXT", result)
        self.assertTrue(result.startswith(market_analysis_service.AI_FALLBACK_PREFIX))
        print("[Test] Gemini fallback passed")


if __name__ == "__main__":
    unittest.main()
