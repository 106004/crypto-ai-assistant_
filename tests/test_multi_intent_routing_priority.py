import unittest
from unittest.mock import patch

from services.line.command_router import route_user_message


class MultiIntentRoutingPriorityTest(unittest.TestCase):
    def _route(self, message: str):
        with patch(
            "services.line.command_router.onboarding_service.get_onboarding_reply",
            return_value=None,
        ):
            return route_user_message("routing-user", message)

    def test_multi_intent_sentence_routes_to_execute_tasks(self):
        with patch(
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
        ) as classify_mock, patch(
            "services.agent.workflow_engine.execute_tasks",
            return_value={
                "intent": "multi_task",
                "tasks": [
                    {"intent": "market_analysis", "coin": "BTC"},
                    {"intent": "price_query", "coin": "BTC"},
                ],
                "results": [],
                "result": "combined",
            },
        ) as execute_mock:
            response = self._route("請分析 BTC 並告訴我價格")

        classify_mock.assert_called_once()
        execute_mock.assert_called_once()
        self.assertEqual(response, "combined")

    def test_natural_language_hands_off_to_decision_engine(self):
        with patch(
            "services.line.command_router.run_agent_workflow",
            return_value={
                "intent": "multi_task",
                "tasks": [
                    {"intent": "market_analysis", "coin": "BTC"},
                    {"intent": "price_query", "coin": "BTC"},
                ],
                "results": [],
                "result": "combined",
            },
        ) as workflow_mock, patch("builtins.print") as print_log:
            response = self._route("請分析 BTC 並告訴我價格")

        workflow_mock.assert_called_once_with("routing-user", "請分析 btc 並告訴我價格")
        self.assertEqual(response, "combined")
        self.assertTrue(
            any(
                "[CommandRouter] handoff to decision_engine" in str(call.args[0])
                for call in print_log.call_args_list
            )
        )

    def test_multi_intent_sentence_with_reverse_order_routes_to_execute_tasks(self):
        with patch(
            "services.agent.decision_engine.classify_with_llm",
            return_value={
                "tasks": [
                    {"intent": "price_query", "coin": "BTC"},
                    {"intent": "market_analysis", "coin": "BTC"},
                ],
                "intent": "price_query",
                "coin": "BTC",
                "confidence": 0.9,
                "reason": "multi_intent_tasks",
            },
        ) as classify_mock, patch(
            "services.agent.workflow_engine.execute_tasks",
            return_value={
                "intent": "multi_task",
                "tasks": [
                    {"intent": "price_query", "coin": "BTC"},
                    {"intent": "market_analysis", "coin": "BTC"},
                ],
                "results": [],
                "result": "combined",
            },
        ) as execute_mock:
            response = self._route("BTC 現在多少並分析一下")

        classify_mock.assert_called_once()
        execute_mock.assert_called_once()
        self.assertEqual(response, "combined")

    def test_single_intent_price_goes_llm_first(self):
        with patch(
            "services.agent.decision_engine.classify_with_llm",
            return_value={
                "tasks": [{"intent": "price_query", "coin": "ETH"}],
                "intent": "price_query",
                "coin": "ETH",
                "confidence": 0.9,
                "reason": "single_task_llm",
            },
        ) as classify_mock, patch(
            "services.agent.workflow_engine.execute_tasks"
        ) as execute_mock:
            execute_mock.return_value = {"result": "combined"}
            response = self._route("今天 ETH 價格多少")

        classify_mock.assert_called_once()
        execute_mock.assert_called_once()
        self.assertEqual(response, "combined")

    def test_single_intent_analyze_keeps_fast_path(self):
        with patch(
            "services.agent.decision_engine.classify_with_llm"
        ) as classify_mock, patch(
            "services.agent.workflow_engine.execute_tasks"
        ) as execute_mock:
            response = self._route("analyze BTC")

        classify_mock.assert_not_called()
        execute_mock.assert_not_called()
        self.assertIsNotNone(response)

    def test_single_coin_keeps_fast_path(self):
        with patch(
            "services.agent.decision_engine.classify_with_llm"
        ) as classify_mock, patch(
            "services.agent.workflow_engine.execute_tasks"
        ) as execute_mock:
            response = self._route("btc")

        classify_mock.assert_not_called()
        execute_mock.assert_not_called()
        self.assertIsNotNone(response)


if __name__ == "__main__":
    unittest.main()
