import unittest
from unittest.mock import patch

from services.agent.decision_engine import decide_user_intent


class GeneralUnsupportedCoinRuleTest(unittest.TestCase):
    def test_general_unsupported_coin_and_supported_coin_routing(self):
        cases = [
            ("ZEC價格", {"intent": "unsupported_coin", "coin": "ZEC", "reason": "coin_not_supported"}),
            ("HYPE價格", {"intent": "unsupported_coin", "coin": "HYPE", "reason": "coin_not_supported"}),
            ("Analyze XLM", {"intent": "unsupported_coin", "coin": "XLM", "reason": "coin_not_supported"}),
            ("analyze LTC", {"intent": "unsupported_coin", "coin": "LTC", "reason": "coin_not_supported"}),
            ("analyze TRUMP", {"intent": "unsupported_coin", "coin": "TRUMP", "reason": "coin_not_supported"}),
            ("PEPE價格", {"intent": "unsupported_coin", "coin": "PEPE", "reason": "coin_not_supported"}),
            ("BTC價格", {"intent": "price_query", "coin": "BTC", "confidence": 0.9}),
            ("analyze BTC", {"intent": "market_analysis", "coin": "BTC", "confidence": 0.9}),
            ("好想知道愛達幣價格哦", {"intent": "price_query", "coin": "ADA", "confidence": 0.9}),
            ("asd123@@", {"intent": "unknown", "coin": "", "confidence": 0.1}),
        ]

        for message, expected in cases:
            with self.subTest(message=message):
                result = decide_user_intent(message)
                self.assertEqual(result, expected)

    def test_validator_log_is_emitted_for_unsupported_coin(self):
        with patch("builtins.print") as print_log:
            result = decide_user_intent("ZEC價格")

        self.assertEqual(result["intent"], "unsupported_coin")
        self.assertEqual(result["coin"], "ZEC")
        self.assertTrue(
            any(
                "[CoinValidator] unsupported coin: ZEC" in str(call.args[0])
                for call in print_log.call_args_list
            )
        )

    def test_llm_unavailable_falls_back_to_ticker_extraction(self):
        with patch(
            "services.agent.llm_intent_classifier.get_gemini_client",
            return_value=None,
        ), patch("builtins.print") as print_log:
            result = decide_user_intent("ZEC價格")

        self.assertEqual(
            result,
            {
                "intent": "unsupported_coin",
                "coin": "ZEC",
                "reason": "coin_not_supported",
            },
        )
        self.assertTrue(
            any(
                "[LLMClassifier] unavailable or failed" in str(call.args[0])
                for call in print_log.call_args_list
            )
        )
        self.assertTrue(
            any(
                "[UnknownTickerExtractor] extracted ticker: ZEC" in str(call.args[0])
                for call in print_log.call_args_list
            )
        )


if __name__ == "__main__":
    unittest.main()
