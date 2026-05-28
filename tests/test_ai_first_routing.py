import unittest
from unittest.mock import patch

from services.line.command_router import route_user_message


class AIFirstRoutingTest(unittest.TestCase):
    def _route(self, message: str):
        with patch(
            "services.line.command_router.onboarding_service.get_onboarding_reply",
            return_value=None,
        ):
            return route_user_message("ai-first-user", message)

    def test_btc_keeps_fast_path(self):
        with patch("services.agent.decision_engine.classify_with_llm") as classify_mock, patch(
            "services.agent.workflow_engine.execute_tasks"
        ) as execute_mock:
            response = self._route("btc")

        classify_mock.assert_not_called()
        execute_mock.assert_not_called()
        self.assertIsNotNone(response)

    def test_analyze_btc_keeps_fast_path(self):
        with patch("services.agent.decision_engine.classify_with_llm") as classify_mock, patch(
            "services.agent.workflow_engine.execute_tasks"
        ) as execute_mock:
            response = self._route("analyze btc")

        classify_mock.assert_not_called()
        execute_mock.assert_not_called()
        self.assertIsNotNone(response)

    def test_natural_language_routes_to_llm_first(self):
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

    def test_simple_question_routes_to_llm_first(self):
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
            response = self._route("今天 ETH 怎麼樣")

        classify_mock.assert_called_once()
        execute_mock.assert_called_once()
        self.assertEqual(response, "combined")

    def test_requesting_favorite_coin_routes_to_llm_first(self):
        with patch(
            "services.agent.decision_engine.classify_with_llm",
            return_value={
                "tasks": [{"intent": "get_favorite_coin", "coin": "XRP"}],
                "intent": "get_favorite_coin",
                "coin": "XRP",
                "confidence": 0.9,
                "reason": "single_task_llm",
            },
        ) as classify_mock, patch(
            "services.agent.workflow_engine.execute_tasks"
        ) as execute_mock:
            execute_mock.return_value = {"result": "combined"}
            response = self._route("LTC 是我最愛貨幣")

        classify_mock.assert_called_once()
        execute_mock.assert_called_once()
        self.assertEqual(response, "combined")


if __name__ == "__main__":
    unittest.main()
