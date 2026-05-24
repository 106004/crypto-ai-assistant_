import unittest
from unittest.mock import patch

import market_analyzer


class FakeGeminiResponse:
    text = "BTC 維持偏強，但需留意高檔波動。\n\n這不是投資建議。"


class FakeModels:
    def __init__(self):
        self.call_args = None

    def generate_content(self, **kwargs):
        self.call_args = kwargs
        return FakeGeminiResponse()


class FakeGeminiClient:
    def __init__(self):
        self.models = FakeModels()


class MarketAnalyzerTest(unittest.TestCase):
    def test_analyze_market_data_uses_gemini_prompt_and_returns_line_text(self):
        client = FakeGeminiClient()
        coin_data = {
            "symbol": "BTC",
            "name": "Bitcoin",
            "price_usd": 100,
            "change_24h": 2.3,
            "updated_at": "2026-05-24T00:00:00+00:00",
        }

        with patch.object(market_analyzer, "get_gemini_client", return_value=client), patch(
            "builtins.print"
        ) as print_log:
            result = market_analyzer.analyze_market_data(coin_data)

        self.assertEqual(
            result,
            "BTC AI 市場分析\n\nBTC 維持偏強，但需留意高檔波動。\n\n這不是投資建議。",
        )
        self.assertEqual(client.models.call_args["model"], "gemini-2.0-flash")
        prompt = client.models.call_args["contents"]
        self.assertIn("symbol：BTC", prompt)
        self.assertIn("價格：100", prompt)
        self.assertIn("24H 漲跌：2.3", prompt)
        self.assertIn("updated_at：2026-05-24T00:00:00+00:00", prompt)
        self.assertIn("不要超過 120 字", prompt)
        print_log.assert_any_call("[Gemini] 開始生成市場分析")
        print_log.assert_any_call("[Gemini] Prompt 已建立")
        print_log.assert_any_call("[Gemini] API 呼叫成功")
        print_log.assert_any_call("[Gemini] 分析生成完成")

    def test_analyze_market_data_returns_error_message_when_gemini_fails(self):
        coin_data = {
            "symbol": "BTC",
            "name": "Bitcoin",
            "price_usd": 100,
            "change_24h": 2.3,
            "updated_at": "2026-05-24T00:00:00+00:00",
        }

        with patch.object(market_analyzer, "get_gemini_client", side_effect=RuntimeError("boom")), patch(
            "builtins.print"
        ) as print_log:
            result = market_analyzer.analyze_market_data(coin_data)

        self.assertEqual(result, "⚠️ AI 市場分析服務暫時異常\n請稍後再試。")
        print_log.assert_any_call("[Gemini] API 呼叫失敗：boom")

    def test_analyze_market_data_returns_insufficient_data_without_change_24h(self):
        result = market_analyzer.analyze_market_data({"symbol": "BTC"})

        self.assertEqual(result, "目前資料不足，無法產生分析。")


if __name__ == "__main__":
    unittest.main()
