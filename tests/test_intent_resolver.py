import unittest
from unittest.mock import patch

from services.agent.intent_resolver import resolve_intent


class IntentResolverTest(unittest.TestCase):
    def test_keyword_priority_and_defaults(self):
        cases = [
            (
                "BTC價格",
                {
                    "intent": "price_query",
                    "reason": "price_query_keyword",
                    "matched_keywords": ["價格"],
                    "matched_intents": ["price_query"],
                },
            ),
            (
                "BTC多少",
                {
                    "intent": "price_query",
                    "reason": "price_query_keyword",
                    "matched_keywords": ["多少"],
                    "matched_intents": ["price_query"],
                },
            ),
            (
                "analyze BTC",
                {
                    "intent": "market_analysis",
                    "reason": "market_analysis_keyword",
                    "matched_keywords": ["analyze"],
                    "matched_intents": ["market_analysis"],
                },
            ),
            (
                "分析 BTC",
                {
                    "intent": "market_analysis",
                    "reason": "market_analysis_keyword",
                    "matched_keywords": ["分析"],
                    "matched_intents": ["market_analysis"],
                },
            ),
            (
                "幫我看看 BTC",
                {
                    "intent": "market_analysis",
                    "reason": "market_analysis_keyword",
                    "matched_keywords": ["看看"],
                    "matched_intents": ["market_analysis"],
                },
            ),
            (
                "BTC 怎麼樣",
                {
                    "intent": "market_analysis",
                    "reason": "market_analysis_keyword",
                    "matched_keywords": ["怎麼樣"],
                    "matched_intents": ["market_analysis"],
                },
            ),
            (
                "set BTC",
                {
                    "intent": "set_favorite_coin",
                    "reason": "set_favorite_coin_keyword",
                    "matched_keywords": ["set"],
                    "matched_intents": ["set_favorite_coin"],
                },
            ),
            (
                "BTC 是我最愛",
                {
                    "intent": "set_favorite_coin",
                    "reason": "set_favorite_coin_keyword",
                    "matched_keywords": ["最愛"],
                    "matched_intents": ["set_favorite_coin"],
                },
            ),
            (
                "help",
                {
                    "intent": "help",
                    "reason": "help_keyword",
                    "matched_keywords": ["help"],
                    "matched_intents": ["help"],
                },
            ),
            (
                "怎麼用",
                {
                    "intent": "help",
                    "reason": "help_keyword",
                    "matched_keywords": ["怎麼用"],
                    "matched_intents": ["help"],
                },
            ),
            (
                "asd123@@",
                {
                    "intent": "unknown",
                    "reason": "no_keywords",
                    "matched_keywords": [],
                    "matched_intents": [],
                },
            ),
        ]

        for message, expected in cases:
            with self.subTest(message=message):
                result = resolve_intent(message)
                for key, value in expected.items():
                    self.assertEqual(result[key], value)

    def test_multiple_keywords_are_reported(self):
        result = resolve_intent("分析 BTC 價格")
        self.assertEqual(result["intent"], "market_analysis")
        self.assertEqual(result["reason"], "multiple_keywords")
        self.assertEqual(result["matched_intents"], ["market_analysis", "price_query"])
        self.assertEqual(result["matched_keywords"], ["分析", "價格"])

    def test_logs_resolved_intent(self):
        with patch("builtins.print") as print_log:
            result = resolve_intent("分析 BTC")

        self.assertEqual(result["intent"], "market_analysis")
        self.assertTrue(
            any(
                "[IntentResolver] resolved: market_analysis" in str(call.args[0])
                for call in print_log.call_args_list
            )
        )


if __name__ == "__main__":
    unittest.main()
