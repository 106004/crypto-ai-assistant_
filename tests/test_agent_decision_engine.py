import unittest
from unittest.mock import patch

from services.agent.decision_engine import decide_user_intent


class DecisionEngineTest(unittest.TestCase):
    def test_price_query_exact_alias(self):
        self.assertEqual(
            decide_user_intent("btc"),
            {"intent": "price_query", "coin": "BTC", "confidence": 0.9},
        )

    def test_market_analysis_exact_alias(self):
        self.assertEqual(
            decide_user_intent("analyze eth"),
            {"intent": "market_analysis", "coin": "ETH", "confidence": 0.9},
        )

    def test_help(self):
        self.assertEqual(
            decide_user_intent("/help"),
            {"intent": "help", "coin": "", "confidence": 0.9},
        )

    def test_unknown(self):
        self.assertEqual(
            decide_user_intent("something random"),
            {"intent": "unknown", "coin": "", "confidence": 0.1},
        )

    def test_context_inference_uses_previous_analysis_intent(self):
        self.assertEqual(
            decide_user_intent(
                "and what about eth?",
                user_state={"last_intent": "market_analysis", "last_coin": "BTC"},
            ),
            {"intent": "market_analysis", "coin": "ETH", "confidence": 0.8},
        )

    def test_context_inference_without_previous_intent_falls_back_to_unknown(self):
        self.assertEqual(
            decide_user_intent("and what about sol?", user_state={}),
            {"intent": "unknown", "coin": "", "confidence": 0.1},
        )

    def test_btc_typo_uses_llm_for_fuzzy_candidate(self):
        with patch(
            "services.agent.decision_engine.semantic_resolver.resolve_coin_symbol",
            return_value={
                "coin": None,
                "confidence": 0.0,
                "method": "fuzzy_candidates",
                "candidates": [{"coin": "BTC", "score": 0.86}],
            },
        ), patch(
            "services.agent.decision_engine.classify_with_llm",
            return_value={
                "intent": "price_query",
                "coin": "BTC",
                "confidence": 0.92,
                "reason": "selected from candidates",
            },
        ) as classify_mock:
            result = decide_user_intent("btcc price")

        classify_mock.assert_called_once()
        self.assertEqual(result, {"intent": "price_query", "coin": "BTC", "confidence": 0.92})

    def test_ltc_does_not_turn_into_btc(self):
        with patch(
            "services.agent.decision_engine.classify_with_llm",
            return_value={
                "intent": "unsupported_coin",
                "coin": "LTC",
                "confidence": 0.96,
                "reason": "coin_not_supported",
            },
        ):
            result = decide_user_intent("今天 LTC 價格")
        self.assertEqual(result["intent"], "unsupported_coin")
        self.assertEqual(result["coin"], "LTC")
        self.assertNotEqual(result["coin"], "BTC")

    def test_chinese_typo_uses_btc(self):
        with patch(
            "services.agent.decision_engine.classify_with_llm",
            return_value={
                "intent": "price_query",
                "coin": "BTC",
                "confidence": 0.93,
                "reason": "selected from candidates",
            },
        ):
            result = decide_user_intent("今天比特價格")
        self.assertEqual(result, {"intent": "price_query", "coin": "BTC", "confidence": 0.93})

    def test_chinese_exact_alias_uses_btc(self):
        result = decide_user_intent("今天比特幣價格")
        self.assertEqual(result, {"intent": "price_query", "coin": "BTC", "confidence": 0.9})

    def test_generic_unknown_ticker_becomes_unsupported_coin(self):
        with patch(
            "services.agent.decision_engine.semantic_resolver.resolve_coin_symbol",
            return_value={"coin": None, "confidence": 0.0, "method": "none"},
        ), patch(
            "services.agent.decision_engine.classify_with_llm",
            return_value={
                "tasks": [{"intent": "price_query", "coin": None}],
                "intent": "price_query",
                "coin": None,
                "confidence": 0.9,
                "reason": "single_task_llm",
            },
        ):
            result = decide_user_intent("hype 價格")

        self.assertEqual(
            result,
            {
                "intent": "unsupported_coin",
                "coin": "HYPE",
                "reason": "coin_not_supported",
            },
        )


if __name__ == "__main__":
    unittest.main()
