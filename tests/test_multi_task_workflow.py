import unittest
from unittest.mock import patch

from services.agent.state_manager import reset_user_state
from services.agent.workflow_engine import run_agent_workflow


class MultiTaskWorkflowTest(unittest.TestCase):
    def setUp(self):
        reset_user_state("multi-task-user")

    def test_analysis_then_price_executes_in_order(self):
        with patch(
            "services.agent.workflow_engine.decision_engine.decide_user_intent",
            return_value={
                "tasks": [
                    {"intent": "market_analysis", "coin": "BTC"},
                    {"intent": "price_query", "coin": "BTC"},
                ]
            },
        ), patch(
            "services.agent.workflow_engine.handle_analysis_query",
            return_value="BTC analysis result",
        ) as analysis_mock, patch(
            "services.agent.workflow_engine.handle_price_query",
            return_value="BTC price result",
        ) as price_mock:
            result = run_agent_workflow("multi-task-user", "please analyze BTC and tell me the price")

        analysis_mock.assert_called_once_with("BTC")
        price_mock.assert_called_once_with("BTC")
        self.assertEqual(result["intent"], "multi_task")
        self.assertEqual(len(result["results"]), 2)
        self.assertIn("BTC analysis result", result["result"])
        self.assertIn("BTC price result", result["result"])
        self.assertLess(result["result"].index("BTC analysis result"), result["result"].index("BTC price result"))
        self.assertEqual(result["state"]["last_intent"], "price_query")
        self.assertEqual(result["state"]["last_coin"], "BTC")
        self.assertEqual(result["state"]["conversation_count"], 1)

    def test_price_then_analysis_executes_in_order(self):
        with patch(
            "services.agent.workflow_engine.decision_engine.decide_user_intent",
            return_value={
                "tasks": [
                    {"intent": "price_query", "coin": "BTC"},
                    {"intent": "market_analysis", "coin": "BTC"},
                ]
            },
        ), patch(
            "services.agent.workflow_engine.handle_analysis_query",
            return_value="BTC analysis result",
        ) as analysis_mock, patch(
            "services.agent.workflow_engine.handle_price_query",
            return_value="BTC price result",
        ) as price_mock:
            result = run_agent_workflow("multi-task-user", "BTC price then analyze")

        price_mock.assert_called_once_with("BTC")
        analysis_mock.assert_called_once_with("BTC")
        self.assertEqual(result["intent"], "multi_task")
        self.assertLess(result["result"].index("BTC price result"), result["result"].index("BTC analysis result"))

    def test_unsupported_coin_then_price_short_circuits_price_service(self):
        with patch(
            "services.agent.workflow_engine.decision_engine.decide_user_intent",
            return_value={
                "tasks": [
                    {"intent": "unsupported_coin", "coin": "TRUMP"},
                    {"intent": "price_query", "coin": "TRUMP"},
                ]
            },
        ), patch(
            "services.agent.workflow_engine.build_unsupported_coin_message",
            return_value="unsupported coin message",
        ) as unsupported_mock, patch(
            "services.agent.workflow_engine.handle_price_query",
            return_value="TRUMP price fallback",
        ) as price_mock, patch("builtins.print") as print_log:
            result = run_agent_workflow("multi-task-user", "TRUMP price")

        self.assertGreaterEqual(unsupported_mock.call_count, 2)
        price_mock.assert_not_called()
        self.assertIn("unsupported coin message", result["result"])
        self.assertTrue(
            any(
                "[WorkflowEngine] unsupported coin task short-circuited" in str(call.args[0])
                for call in print_log.call_args_list
            )
        )

    def test_partial_failure_keeps_successful_tasks(self):
        with patch(
            "services.agent.workflow_engine.decision_engine.decide_user_intent",
            return_value={
                "tasks": [
                    {"intent": "price_query", "coin": "ETH"},
                    {"intent": "market_analysis", "coin": "ETH"},
                ]
            },
        ), patch(
            "services.agent.workflow_engine.handle_price_query",
            return_value="ETH price result",
        ), patch(
            "services.agent.workflow_engine.handle_analysis_query",
            side_effect=RuntimeError("analysis boom"),
        ), patch("builtins.print") as print_log:
            result = run_agent_workflow("multi-task-user", "ETH price + analyze ETH")

        self.assertIn("ETH price result", result["result"])
        self.assertIn("失敗", result["result"])
        self.assertTrue(
            any("[WorkflowEngine] task failed" in str(call.args[0]) for call in print_log.call_args_list)
        )
        self.assertEqual(result["state"]["last_intent"], "market_analysis")
        self.assertEqual(result["state"]["last_coin"], "ETH")


if __name__ == "__main__":
    unittest.main()
