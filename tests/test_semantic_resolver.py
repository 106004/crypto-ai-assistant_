import unittest
from unittest.mock import patch

from services.agent.decision_engine import decide_user_intent
from services.agent.semantic_resolver import resolve_coin_symbol


class SemanticResolverTest(unittest.TestCase):
    def test_exact_alias(self):
        self.assertEqual(
            resolve_coin_symbol("比特幣今天價格"),
            {"coin": "BTC", "confidence": 1.0, "method": "exact_alias"},
        )

    def test_chinese_typo_generates_candidate(self):
        result = resolve_coin_symbol("比特壁")
        self.assertEqual(result["method"], "fuzzy_candidates")
        self.assertIsNone(result["coin"])
        self.assertGreater(len(result["candidates"]), 0)
        self.assertTrue(any(item["coin"] == "BTC" for item in result["candidates"]))

    def test_ascii_typo_generates_btc_candidate(self):
        result = resolve_coin_symbol("btcc")
        self.assertEqual(result["method"], "fuzzy_candidates")
        self.assertIsNone(result["coin"])
        self.assertTrue(any(item["coin"] == "BTC" for item in result["candidates"]))

    def test_english_typo_generates_eth_candidate(self):
        result = resolve_coin_symbol("etherum price")
        self.assertEqual(result["method"], "fuzzy_candidates")
        self.assertIsNone(result["coin"])
        self.assertTrue(any(item["coin"] == "ETH" for item in result["candidates"]))

    def test_ltc_does_not_fuzzy_to_btc(self):
        result = resolve_coin_symbol("LTC")
        self.assertEqual(result["method"], "none")
        self.assertIsNone(result["coin"])
        self.assertNotEqual(result.get("coin"), "BTC")

    def test_etc_does_not_fuzzy_to_eth(self):
        result = resolve_coin_symbol("ETC")
        self.assertEqual(result["method"], "none")
        self.assertIsNone(result["coin"])
        self.assertNotEqual(result.get("coin"), "ETH")

    def test_fet_does_not_fuzzy_to_eth(self):
        result = resolve_coin_symbol("FET")
        self.assertEqual(result["method"], "none")
        self.assertIsNone(result["coin"])
        self.assertNotEqual(result.get("coin"), "ETH")

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

    def test_decision_engine_uses_llm_for_fuzzy_candidates(self):
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
                "confidence": 0.91,
                "reason": "selected from candidates",
            },
        ) as classify_mock:
            result = decide_user_intent("btcc price")

        classify_mock.assert_called_once()
        self.assertEqual(result, {"intent": "price_query", "coin": "BTC", "confidence": 0.91})


if __name__ == "__main__":
    unittest.main()
