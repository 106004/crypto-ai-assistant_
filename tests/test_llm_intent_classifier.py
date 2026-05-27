import unittest
from unittest.mock import patch

from services.agent.decision_engine import decide_user_intent
from services.agent.llm_intent_classifier import classify_with_llm, parse_llm_classifier_output


class FakeModels:
    def __init__(self, response_text, capture=None):
        self.response_text = response_text
        self.capture = capture

    def generate_content(self, model, contents):
        if self.capture is not None:
            self.capture["model"] = model
            self.capture["contents"] = contents
        return type("Response", (), {"text": self.response_text})()


class FakeClient:
    def __init__(self, response_text, capture=None):
        self.models = FakeModels(response_text, capture=capture)


class LLMIntentClassifierTest(unittest.TestCase):
    def test_valid_json_accepted(self):
        result = parse_llm_classifier_output(
            '{"intent":"price_query","coin":"ETH","confidence":0.91,"reason":"user asked for price"}'
        )
        self.assertEqual(
            result,
            {
                "intent": "price_query",
                "coin": "ETH",
                "confidence": 0.91,
                "reason": "user asked for price",
            },
        )

    def test_invalid_json_rejected(self):
        self.assertEqual(
            parse_llm_classifier_output("not json"),
            {
                "intent": "unknown",
                "coin": None,
                "confidence": 0.0,
                "reason": "invalid_json",
            },
        )

    def test_unsupported_coin_returns_unsupported_coin(self):
        self.assertEqual(
            parse_llm_classifier_output(
                '{"intent":"price_query","coin":"ABC","confidence":0.99,"reason":"bad coin"}'
            ),
            {
                "intent": "unsupported_coin",
                "coin": "ABC",
                "confidence": 0.99,
                "reason": "coin_not_supported",
            },
        )

    def test_known_unsupported_coin_returns_unsupported_coin(self):
        self.assertEqual(
            parse_llm_classifier_output(
                '{"intent":"market_analysis","coin":"TRUMP","confidence":0.98,"reason":"recognized but unsupported"}'
            ),
            {
                "intent": "unsupported_coin",
                "coin": "TRUMP",
                "confidence": 0.98,
                "reason": "coin_not_supported",
            },
        )

    def test_known_unsupported_coin_floki_returns_unsupported_coin(self):
        self.assertEqual(
            parse_llm_classifier_output(
                '{"intent":"price_query","coin":"FLOKI","confidence":0.97,"reason":"recognized but unsupported"}'
            ),
            {
                "intent": "unsupported_coin",
                "coin": "FLOKI",
                "confidence": 0.97,
                "reason": "coin_not_supported",
            },
        )

    def test_known_unsupported_coin_bonk_returns_unsupported_coin(self):
        self.assertEqual(
            parse_llm_classifier_output(
                '{"intent":"price_query","coin":"BONK","confidence":0.97,"reason":"recognized but unsupported"}'
            ),
            {
                "intent": "unsupported_coin",
                "coin": "BONK",
                "confidence": 0.97,
                "reason": "coin_not_supported",
            },
        )

    def test_low_confidence_unsupported_coin_does_not_become_unsupported_coin(self):
        self.assertEqual(
            parse_llm_classifier_output(
                '{"intent":"market_analysis","coin":"TRUMP","confidence":0.7,"reason":"too uncertain"}'
            ),
            {
                "intent": "clarification_needed",
                "coin": "TRUMP",
                "confidence": 0.7,
                "reason": "low_confidence",
            },
        )

    def test_unsupported_intent_rejected(self):
        self.assertEqual(
            parse_llm_classifier_output(
                '{"intent":"buy_coin","coin":"BTC","confidence":0.99,"reason":"bad intent"}'
            ),
            {
                "intent": "unknown",
                "coin": None,
                "confidence": 0.0,
                "reason": "unsupported_intent",
            },
        )

    def test_low_confidence_rejected(self):
        self.assertEqual(
            parse_llm_classifier_output(
                '{"intent":"market_analysis","coin":"DOGE","confidence":0.7,"reason":"not enough confidence"}'
            ),
            {
                "intent": "clarification_needed",
                "coin": "DOGE",
                "confidence": 0.7,
                "reason": "low_confidence",
            },
        )

    def test_missing_confidence_rejected(self):
        self.assertEqual(
            parse_llm_classifier_output(
                '{"intent":"market_analysis","coin":"DOGE","reason":"missing confidence"}'
            ),
            {
                "intent": "unknown",
                "coin": None,
                "confidence": 0.0,
                "reason": "missing_confidence",
            },
        )

    def test_confidence_as_string_can_be_converted(self):
        self.assertEqual(
            parse_llm_classifier_output(
                '{"intent":"market_analysis","coin":"DOGE","confidence":"0.88","reason":"string confidence"}'
            ),
            {
                "intent": "market_analysis",
                "coin": "DOGE",
                "confidence": 0.88,
                "reason": "string confidence",
            },
        )

    def test_null_coin_allowed_for_help(self):
        self.assertEqual(
            parse_llm_classifier_output(
                '{"intent":"help","coin":null,"confidence":0.99,"reason":"help request"}'
            ),
            {
                "intent": "help",
                "coin": None,
                "confidence": 0.99,
                "reason": "help request",
            },
        )

    def test_null_coin_allowed_for_get_favorite_coin(self):
        self.assertEqual(
            parse_llm_classifier_output(
                '{"intent":"get_favorite_coin","coin":null,"confidence":0.99,"reason":"favorite coin request"}'
            ),
            {
                "intent": "get_favorite_coin",
                "coin": None,
                "confidence": 0.99,
                "reason": "favorite coin request",
            },
        )

    def test_null_coin_allowed_for_unknown(self):
        self.assertEqual(
            parse_llm_classifier_output(
                '{"intent":"unknown","coin":null,"confidence":0.8,"reason":"unsure"}'
            ),
            {
                "intent": "unknown",
                "coin": None,
                "confidence": 0.8,
                "reason": "unsure",
            },
        )

    def test_null_coin_rejected_for_price_query(self):
        self.assertEqual(
            parse_llm_classifier_output(
                '{"intent":"price_query","coin":null,"confidence":0.9,"reason":"missing coin"}'
            ),
            {
                "intent": "unknown",
                "coin": None,
                "confidence": 0.0,
                "reason": "coin_unrecognized",
            },
        )

    def test_classify_with_llm_includes_candidates_in_prompt(self):
        capture = {}
        response_text = (
            '{"intent":"price_query","coin":"BTC","confidence":0.91,'
            '"reason":"selected candidate"}'
        )
        with patch(
            "services.agent.llm_intent_classifier.get_gemini_client",
            return_value=FakeClient(response_text, capture=capture),
        ):
            result = classify_with_llm(
                "btcc price",
                candidates=[{"coin": "BTC", "score": 0.86}],
            )

        self.assertEqual(result["intent"], "price_query")
        self.assertEqual(result["coin"], "BTC")
        self.assertIn("BTC", str(capture["contents"]))
        self.assertIn("btcc price", str(capture["contents"]))

    def test_classify_with_llm_rejects_candidate_mismatch(self):
        response_text = (
            '{"intent":"price_query","coin":"BTC","confidence":0.95,'
            '"reason":"selected wrong coin"}'
        )
        with patch(
            "services.agent.llm_intent_classifier.get_gemini_client",
            return_value=FakeClient(response_text),
        ):
            result = classify_with_llm("LTC price", candidates=[{"coin": "ETH", "score": 0.84}])

        self.assertIn(result["intent"], {"clarification_needed", "unknown"})
        self.assertNotEqual(result.get("coin"), "BTC")

    def test_classify_with_llm_returns_unsupported_coin_for_ltc(self):
        response_text = (
            '{"intent":"price_query","coin":"LTC","confidence":0.96,'
            '"reason":"recognized but unsupported"}'
        )
        with patch(
            "services.agent.llm_intent_classifier.get_gemini_client",
            return_value=FakeClient(response_text),
        ):
            result = classify_with_llm("LTC price")

        self.assertEqual(
            result,
            {
                "intent": "unsupported_coin",
                "coin": "LTC",
                "confidence": 0.96,
                "reason": "coin_not_supported",
            },
        )

    def test_decision_engine_calls_llm_when_ambiguous(self):
        with patch(
            "services.agent.decision_engine.semantic_resolver.resolve_coin_symbol",
            return_value={
                "coin": None,
                "confidence": 0.0,
                "method": "none",
            },
        ), patch(
            "services.agent.decision_engine.classify_with_llm",
            return_value={
                "intent": "market_analysis",
                "coin": "DOGE",
                "confidence": 0.9,
                "reason": "ambiguous request",
            },
        ) as classify_with_llm_mock:
            result = decide_user_intent("some ambiguous request")

        classify_with_llm_mock.assert_called_once()
        self.assertEqual(
            result,
            {"intent": "market_analysis", "coin": "DOGE", "confidence": 0.9},
        )

    def test_decision_engine_fuzzy_candidates_flow(self):
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
