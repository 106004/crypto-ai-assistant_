import unittest

from services.agent.decision_engine import decide_user_intent
from services.agent.semantic_resolver import resolve_coin_symbol


class SemanticResolverTest(unittest.TestCase):
    def test_exact_alias(self):
        self.assertEqual(
            resolve_coin_symbol("大餅今天價格多少"),
            {"coin": "BTC", "confidence": 1.0, "method": "exact_alias"},
        )

    def test_chinese_typo(self):
        result = resolve_coin_symbol("比特壁今天價格多少")
        self.assertEqual(result["coin"], "BTC")
        self.assertEqual(result["method"], "fuzzy")
        self.assertGreaterEqual(result["confidence"], 0.85)

    def test_english_typo(self):
        result = resolve_coin_symbol("etherum price")
        self.assertEqual(result["coin"], "ETH")
        self.assertEqual(result["method"], "fuzzy")
        self.assertGreaterEqual(result["confidence"], 0.85)

    def test_mixed_case_typo(self):
        result = resolve_coin_symbol("BiTcOiN price")
        self.assertEqual(result["coin"], "BTC")
        self.assertEqual(result["method"], "exact_alias")
        self.assertEqual(result["confidence"], 1.0)

    def test_unrecognized_returns_none(self):
        self.assertEqual(
            resolve_coin_symbol("completely unknown token"),
            {"coin": None, "confidence": 0.0, "method": "none"},
        )

    def test_threshold_blocks_low_confidence(self):
        self.assertEqual(
            resolve_coin_symbol("abcde"),
            {"coin": None, "confidence": 0.0, "method": "none"},
        )

    def test_decision_engine_uses_semantic_resolver(self):
        self.assertEqual(
            decide_user_intent("比特壁今天價格多少"),
            {"intent": "price_query", "coin": "BTC", "confidence": 0.9},
        )


if __name__ == "__main__":
    unittest.main()
