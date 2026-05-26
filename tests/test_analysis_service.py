import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from config.settings import MAX_MARKET_DATA_AGE_SECONDS
from services.ai import market_analysis_service
from services.line.analysis_service import handle_analysis_query


MARKET_DATA_AGE_MINUTES = MAX_MARKET_DATA_AGE_SECONDS // 60


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
            "services.line.analysis_service.analyze_market_data",
            return_value="ANALYSIS_TEXT",
        ):
            result = handle_analysis_query("btc")

        self.assertIn("BTC AI 分析", result)
        self.assertIn("ANALYSIS_TEXT", result)

    def test_stale_market_data_returns_stale_message_and_skips_ai(self):
        now_utc = datetime.now(timezone.utc)
        market_data = {
            "symbol": "BTC",
            "name": "Bitcoin",
            "price_usd": 100,
            "change_24h": 2.3,
            "source": "Supabase",
            "updated_at": (now_utc - timedelta(minutes=7)).isoformat(),
        }

        with patch(
            "services.line.analysis_service.get_market_data_by_symbol",
            return_value=market_data,
        ), patch(
            "services.line.analysis_service.analyze_market_data"
        ) as analyze_market_data, patch(
            "builtins.print"
        ) as print_log:
            result = handle_analysis_query("btc")

        analyze_market_data.assert_not_called()
        self.assertIn(
            f"⚠️ 資訊超過 {MARKET_DATA_AGE_MINUTES} 分鐘，AI 無法分析。",
            result,
        )
        self.assertIn("目前資料已過期，為避免誤導，系統不會回傳 AI 分析。", result)
        self.assertIn("CoinGlass", result)
        self.assertIn("https://www.coinglass.com/zh-TW/currencies/BTC", result)
        self.assertTrue(
            any(
                "[AnalysisService] market data stale, skip AI analysis" in str(call.args[0])
                for call in print_log.call_args_list
            )
        )
        self.assertTrue(
            any(
                "[AnalysisService] provide CoinGlass link" in str(call.args[0])
                for call in print_log.call_args_list
            )
        )

    def test_gemini_failure_falls_back_to_rule_based_analysis(self):
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


if __name__ == "__main__":
    unittest.main()
