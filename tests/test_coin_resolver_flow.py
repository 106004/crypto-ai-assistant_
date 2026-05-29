import unittest
from unittest.mock import patch

from api_server import ResolveCoinRequest, resolve_coin_api
from services.agent.coin_resolver_flow import resolve_coin_flow


class CoinResolverFlowTest(unittest.TestCase):
    def test_exact_match_does_not_use_llm(self):
        result = resolve_coin_flow("我想查比特幣", debug=True)

        self.assertEqual(result["coin"], "BTC")
        self.assertEqual(result["status"], "supported")
        self.assertFalse(result["llm_used"])
        self.assertTrue(any(step["step"] == "exact_match" for step in result["debug_trace"]))
        self.assertFalse(any(step["step"] == "llm_coin_understanding" and step["executed"] for step in result["debug_trace"]))

    def test_fuzzy_candidate_can_be_selected_by_llm(self):
        with patch(
            "services.agent.coin_resolver_flow.classify_with_llm",
            return_value={
                "intent": "price_query",
                "coin": "BTC",
                "confidence": 0.91,
                "reason": "selected from candidates",
            },
        ) as classify_mock:
            result = resolve_coin_flow("我想查 BTCc", debug=True)

        classify_mock.assert_called()
        self.assertTrue(result["llm_used"])
        self.assertEqual(result["coin"], "BTC")
        self.assertEqual(result["status"], "supported")
        self.assertTrue(any(step["step"] == "fuzzy_candidates" and step["executed"] for step in result["debug_trace"]))
        self.assertTrue(any(step["step"] == "llm_coin_understanding" and step["executed"] for step in result["debug_trace"]))
        self.assertTrue(any(step["step"] == "final_decision" and step["source"] for step in result["debug_trace"]))

    def test_ticker_extraction_still_works_without_llm(self):
        result = resolve_coin_flow("我想查 LINK", debug=True)

        self.assertEqual(result["coin"], "LINK")
        self.assertEqual(result["status"], "unsupported")
        self.assertFalse(result["llm_used"])
        self.assertTrue(any(step["step"] == "ticker_extraction" and step["matched"] for step in result["debug_trace"]))

    def test_typo_message_can_fall_back_to_llm_or_not_found(self):
        with patch(
            "services.agent.coin_resolver_flow.classify_with_llm",
            return_value={
                "intent": "unknown",
                "coin": None,
                "confidence": 0.0,
                "reason": "low_confidence",
            },
        ) as classify_mock:
            result = resolve_coin_flow("我想查比持幣", debug=True)

        classify_mock.assert_called()
        self.assertIn(result["status"], {"ambiguous", "not_found", "unsupported", "supported"})
        self.assertTrue(any(step["step"] == "llm_coin_understanding" and step["executed"] for step in result["debug_trace"]))

    def test_weather_message_returns_not_found(self):
        with patch(
            "services.agent.coin_resolver_flow.classify_with_llm",
            return_value={
                "intent": "unknown",
                "coin": None,
                "confidence": 0.0,
                "reason": "low_confidence",
            },
        ) as classify_mock:
            result = resolve_coin_flow("今天天氣很好", debug=True)

        self.assertTrue(classify_mock.called)
        self.assertEqual(result["status"], "not_found")
        self.assertTrue(any(step["step"] == "final_decision" for step in result["debug_trace"]))


class ResolveCoinEndpointFlowTest(unittest.TestCase):
    def test_endpoint_uses_resolve_coin_flow(self):
        with patch("api_server.resolve_coin_flow") as helper_mock:
            helper_mock.return_value = {
                "coin": "BTC",
                "status": "supported",
                "method": "exact_match",
                "candidates": [],
                "confidence": 1.0,
                "llm_used": False,
                "debug_trace": [],
            }

            response = resolve_coin_api(ResolveCoinRequest(text="我想查比特幣"))

        helper_mock.assert_called_once_with("我想查比特幣", debug=False)
        self.assertEqual(response["coin"], "BTC")


if __name__ == "__main__":
    unittest.main()
