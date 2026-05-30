import unittest
from unittest.mock import patch

from api_server import ResolveCoinRequest, resolve_coin_api
from services.agent.coin_resolver_flow import resolve_coin_flow


class CoinResolverFlowTest(unittest.TestCase):
    def test_exact_match_does_not_use_gemini(self):
        result = resolve_coin_flow("BTC", debug=True)

        self.assertEqual(result["coin"], "BTC")
        self.assertEqual(result["status"], "supported")
        self.assertEqual(result["method"], "exact_match")
        self.assertFalse(result["llm_used"])
        self.assertTrue(any(step["step"] == "exact_match" and step["matched"] for step in result["debug_trace"]))
        self.assertFalse(any(step["step"] == "gemini_candidate_judge" and step["executed"] for step in result["debug_trace"]))

    def test_bitcoin_chinese_alias_still_short_circuits(self):
        result = resolve_coin_flow("我想查比特幣", debug=True)

        self.assertEqual(result["coin"], "BTC")
        self.assertEqual(result["status"], "supported")
        self.assertEqual(result["method"], "exact_match")
        self.assertFalse(result["llm_used"])
        self.assertTrue(any(step["step"] == "exact_match" and step["matched"] for step in result["debug_trace"]))

    def test_ethereum_chinese_alias_still_short_circuits(self):
        result = resolve_coin_flow("我想查以太幣", debug=True)

        self.assertEqual(result["coin"], "ETH")
        self.assertEqual(result["status"], "supported")
        self.assertEqual(result["method"], "exact_match")
        self.assertFalse(result["llm_used"])
        self.assertTrue(any(step["step"] == "exact_match" and step["matched"] for step in result["debug_trace"]))

    def test_link_uses_ticker_candidate_and_gemini_cannot_override(self):
        with patch(
            "services.agent.coin_resolver_flow.classify_with_llm",
            return_value={
                "intent": "price_query",
                "coin": "LINK",
                "confidence": 0.91,
                "reason": "selected from candidates",
            },
        ) as classify_mock:
            result = resolve_coin_flow("我想查 LINK", debug=True)

        classify_mock.assert_called_once()
        self.assertTrue(result["llm_used"])
        self.assertEqual(result["coin"], "LINK")
        self.assertEqual(result["status"], "unsupported")
        self.assertEqual(result["method"], "gemini_candidate_judge")
        self.assertTrue(
            any(
                step["step"] == "ticker_extraction"
                and step["executed"]
                and step["matched"]
                and step["candidates"] == [{"coin": "LINK", "source": "ticker_extraction"}]
                for step in result["debug_trace"]
            )
        )
        self.assertTrue(
            any(
                step["step"] == "gemini_candidate_judge"
                and step["executed"]
                and step["matched"]
                and step["accepted_coin"] == "LINK"
                for step in result["debug_trace"]
            )
        )

        _, kwargs = classify_mock.call_args
        self.assertEqual(kwargs["candidates"], [{"coin": "LINK", "source": "ticker_extraction"}])

    def test_ltc_uses_ticker_candidate_and_gemini_cannot_override(self):
        with patch(
            "services.agent.coin_resolver_flow.classify_with_llm",
            return_value={
                "intent": "price_query",
                "coin": "LTC",
                "confidence": 0.91,
                "reason": "selected from candidates",
            },
        ) as classify_mock:
            result = resolve_coin_flow("我想查 LTC", debug=True)

        classify_mock.assert_called_once()
        self.assertTrue(result["llm_used"])
        self.assertEqual(result["coin"], "LTC")
        self.assertEqual(result["status"], "unsupported")
        self.assertEqual(result["method"], "gemini_candidate_judge")
        self.assertTrue(
            any(
                step["step"] == "ticker_extraction"
                and step["executed"]
                and step["matched"]
                and step["candidates"] == [{"coin": "LTC", "source": "ticker_extraction"}]
                for step in result["debug_trace"]
            )
        )

        _, kwargs = classify_mock.call_args
        self.assertEqual(kwargs["candidates"], [{"coin": "LTC", "source": "ticker_extraction"}])

    def test_btcc_generates_fuzzy_candidates_and_keeps_trace(self):
        with patch(
            "services.agent.coin_resolver_flow._match_fuzzy_candidates",
            return_value={
                "coin": None,
                "confidence": 0.0,
                "method": "fuzzy_candidates",
                "candidates": [{"coin": "BTC", "score": 0.943}],
            },
        ), patch(
            "services.agent.coin_resolver_flow.classify_with_llm",
            return_value={
                "intent": "price_query",
                "coin": "BTC",
                "confidence": 0.91,
                "reason": "selected from candidates",
            },
        ):
            result = resolve_coin_flow("我想查 BTCc", debug=True)

        self.assertEqual(result["coin"], "BTC")
        self.assertIn(result["status"], {"supported", "ambiguous"})
        self.assertTrue(any(step["step"] == "fuzzy_candidates" and step["executed"] and step["matched"] for step in result["debug_trace"]))
        self.assertTrue(any(step["step"] == "gemini_candidate_judge" and step["executed"] for step in result["debug_trace"]))
        self.assertTrue(
            any(
                step["step"] == "fuzzy_candidates"
                and step["candidates"] == [{"coin": "BTC", "score": 0.943, "source": "fuzzy"}]
                for step in result["debug_trace"]
            )
        )

    def test_chinese_typo_never_returns_raw_text_as_coin(self):
        with patch(
            "services.agent.coin_resolver_flow._match_fuzzy_candidates",
            return_value={
                "coin": None,
                "confidence": 0.0,
                "method": "fuzzy_candidates",
                "candidates": [{"coin": "BTC", "score": 0.91}],
            },
        ), patch(
            "services.agent.coin_resolver_flow.classify_with_llm",
            return_value={
                "intent": "price_query",
                "coin": "比持幣",
                "confidence": 0.87,
                "reason": "raw text",
            },
        ):
            result = resolve_coin_flow("我想查比持幣", debug=True)

        self.assertNotEqual(result["coin"], "比持幣")
        self.assertIsNone(result["coin"])
        self.assertEqual(result["status"], "ambiguous")
        self.assertTrue(any(step["step"] == "gemini_candidate_judge" and step["executed"] for step in result["debug_trace"]))
        self.assertTrue(
            any(
                step["step"] == "fuzzy_candidates"
                and step["candidates"] == [{"coin": "BTC", "score": 0.91, "source": "fuzzy"}]
                for step in result["debug_trace"]
            )
        )
        self.assertTrue(
            any(
                step["step"] == "gemini_candidate_judge"
                and step.get("rejected_reason") == "non_symbol_raw_text"
                and step.get("normalized_coin") is None
                for step in result["debug_trace"]
            )
        )
        self.assertTrue(
            any(
                step["step"] == "gemini_candidate_judge"
                and step.get("final_coin_source") == "rejected"
                for step in result["debug_trace"]
            )
        )

    def test_trump_message_can_return_unsupported_but_not_btc(self):
        result = resolve_coin_flow("我想查川普幣", debug=True)

        self.assertEqual(result["coin"], "TRUMP")
        self.assertEqual(result["status"], "unsupported")
        self.assertNotEqual(result["coin"], "BTC")
        self.assertTrue(any(step["step"] == "alias_match" and step["matched"] for step in result["debug_trace"]))
        self.assertFalse(any(step["step"] == "gemini_candidate_judge" and step["executed"] for step in result["debug_trace"]))

    def test_nonexistent_coin_message_does_not_become_entire_sentence(self):
        with patch(
            "services.agent.coin_resolver_flow.classify_with_llm",
            return_value={
                "intent": "price_query",
                "coin": "我想查一個完全不存在的幣",
                "confidence": 0.91,
                "reason": "raw text",
            },
        ):
            result = resolve_coin_flow("我想查一個完全不存在的幣", debug=True)

        self.assertIsNone(result["coin"])
        self.assertEqual(result["status"], "not_found")
        self.assertNotEqual(result["coin"], "我想查一個完全不存在的幣")
        self.assertTrue(
            any(
                step["step"] == "gemini_candidate_judge"
                and step.get("rejected_reason") == "non_symbol_raw_text"
                for step in result["debug_trace"]
            )
        )

    def test_weather_message_still_runs_gemini_without_candidates(self):
        with patch(
            "services.agent.coin_resolver_flow.classify_with_llm",
            return_value={
                "intent": "unknown",
                "coin": None,
                "confidence": 0.0,
                "reason": "no coin found",
            },
        ) as classify_mock:
            result = resolve_coin_flow("今天天氣很好", debug=True)

        classify_mock.assert_called_once()
        self.assertEqual(result["coin"], None)
        self.assertEqual(result["status"], "not_found")
        self.assertEqual(result["method"], "gemini_candidate_judge")
        self.assertTrue(result["llm_used"])
        self.assertTrue(any(step["step"] == "gemini_candidate_judge" and step["executed"] for step in result["debug_trace"]))
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

            response = resolve_coin_api(ResolveCoinRequest(text="BTC"))

        helper_mock.assert_called_once_with("BTC", debug=False)
        self.assertEqual(response["coin"], "BTC")


if __name__ == "__main__":
    unittest.main()
