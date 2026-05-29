import unittest
from unittest.mock import patch

from services.agent.decision_engine import decide_user_intent
from services.agent.llm_intent_classifier import classify_with_llm


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


class MultiIntentParserTest(unittest.TestCase):
    def _classify(self, message, response_text, capture=None):
        with patch(
            "services.agent.llm_intent_classifier.get_gemini_client",
            return_value=FakeClient(response_text, capture=capture),
        ):
            return classify_with_llm(message)

    def test_analysis_then_price_returns_ordered_tasks(self):
        result = self._classify(
            "請分析 BTC 並告訴我價格",
            '{"tasks":[{"intent":"market_analysis","coin":"BTC"},{"intent":"price_query","coin":"BTC"}]}',
        )

        self.assertEqual(
            result["tasks"],
            [
                {"intent": "market_analysis", "coin": "BTC"},
                {"intent": "price_query", "coin": "BTC"},
            ],
        )

    def test_price_then_analysis_returns_ordered_tasks(self):
        result = self._classify(
            "BTC 現在多少並分析一下",
            '{"tasks":[{"intent":"price_query","coin":"BTC"},{"intent":"market_analysis","coin":"BTC"}]}',
        )

        self.assertEqual(
            result["tasks"],
            [
                {"intent": "price_query", "coin": "BTC"},
                {"intent": "market_analysis", "coin": "BTC"},
            ],
        )

    def test_single_price_returns_single_task(self):
        result = self._classify(
            "今天 ETH 價格多少",
            '{"tasks":[{"intent":"price_query","coin":"ETH"}]}',
        )

        self.assertEqual(result["tasks"], [{"intent": "price_query", "coin": "ETH"}])

    def test_analysis_only_returns_single_task(self):
        result = self._classify(
            "分析一下 XRP",
            '{"tasks":[{"intent":"market_analysis","coin":"XRP"}]}',
        )

        self.assertEqual(result["tasks"], [{"intent": "market_analysis", "coin": "XRP"}])

    def test_unsupported_coin_collapses_to_single_task(self):
        result = self._classify(
            "分析一下川普幣跟告訴我價格",
            '{"tasks":[{"intent":"unsupported_coin","coin":"TRUMP"},{"intent":"price_query","coin":"TRUMP"}]}',
        )

        self.assertEqual(result["tasks"], [{"intent": "unsupported_coin", "coin": "TRUMP"}])

    def test_price_task_with_unsupported_coin_becomes_unsupported_coin(self):
        result = self._classify(
            "ZEC 價格",
            '{"tasks":[{"intent":"price_query","coin":"ZEC"}]}',
        )

        self.assertEqual(result["intent"], "unsupported_coin")
        self.assertEqual(result["coin"], "ZEC")
        self.assertEqual(result["reason"], "coin_not_supported")
        self.assertEqual(result["tasks"], [{"intent": "unsupported_coin", "coin": "ZEC"}])

    def test_mixed_supported_and_unsupported_tasks_are_preserved(self):
        result = self._classify(
            "請分析 BTC 並給我 ZEC 價格",
            '{"tasks":[{"intent":"market_analysis","coin":"BTC"},{"intent":"price_query","coin":"ZEC"}]}',
        )

        self.assertEqual(result["intent"], "market_analysis")
        self.assertEqual(result["coin"], "BTC")
        self.assertEqual(
            result["tasks"],
            [
                {"intent": "market_analysis", "coin": "BTC"},
                {"intent": "unsupported_coin", "coin": "ZEC"},
            ],
        )

    def test_gibberish_returns_unknown_task(self):
        result = self._classify(
            "ajsdhajksd123@@@",
            '{"tasks":[{"intent":"unknown","coin":null}]}',
        )

        self.assertEqual(result["tasks"], [{"intent": "unknown", "coin": None}])

    def test_prompt_requests_multi_intent_tasks(self):
        capture = {}
        self._classify(
            "請分析 BTC 並告訴我價格",
            '{"tasks":[{"intent":"market_analysis","coin":"BTC"},{"intent":"price_query","coin":"BTC"}]}',
            capture=capture,
        )

        prompt = str(capture["contents"])
        self.assertIn("multiple intents", prompt)
        self.assertIn("tasks", prompt)
        self.assertIn("same order as the user's meaning", prompt)
        self.assertIn("analysis", prompt)

    def test_decision_engine_logs_multi_intent_tasks_and_keeps_compatibility(self):
        with patch(
            "services.agent.decision_engine.semantic_resolver.resolve_coin_symbol",
            return_value={"coin": None, "confidence": 0.0, "method": "none"},
        ), patch(
            "services.agent.decision_engine.classify_with_llm",
            return_value={
                "tasks": [
                    {"intent": "market_analysis", "coin": "BTC"},
                    {"intent": "price_query", "coin": "BTC"},
                ],
                "intent": "market_analysis",
                "coin": "BTC",
                "confidence": 0.9,
                "reason": "multi_intent_tasks",
            },
        ), patch("builtins.print") as print_log:
            result = decide_user_intent("請分析 BTC 並告訴我價格")

        self.assertIn("tasks", result)
        self.assertEqual(result["intent"], "market_analysis")
        self.assertEqual(result["coin"], "BTC")
        self.assertEqual(
            result["tasks"],
            [
                {"intent": "market_analysis", "coin": "BTC"},
                {"intent": "price_query", "coin": "BTC"},
            ],
        )
        self.assertTrue(
            any(
                "[DecisionEngine] natural-language detected" in str(call.args[0])
                for call in print_log.call_args_list
            )
        )
        self.assertTrue(
            any(
                "[DecisionEngine] routing to LLM-first path" in str(call.args[0])
                for call in print_log.call_args_list
            )
        )
        self.assertTrue(
            any(
                "[DecisionEngine] multi-intent tasks accepted" in str(call.args[0])
                for call in print_log.call_args_list
            )
        )


if __name__ == "__main__":
    unittest.main()
