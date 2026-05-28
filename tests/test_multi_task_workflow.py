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
            return_value="BTC 市場分析：偏多",
        ) as analysis_mock, patch(
            "services.agent.workflow_engine.handle_price_query",
            return_value="BTC 現價：$108,000",
        ) as price_mock:
            result = run_agent_workflow("multi-task-user", "請分析 BTC 並告訴我價格")

        analysis_mock.assert_called_once_with("BTC")
        price_mock.assert_called_once_with("BTC")
        self.assertEqual(result["intent"], "multi_task")
        self.assertEqual(len(result["results"]), 2)
        self.assertIn("BTC 市場分析：偏多", result["result"])
        self.assertIn("BTC 現價：$108,000", result["result"])
        self.assertLess(
            result["result"].index("BTC 市場分析：偏多"),
            result["result"].index("BTC 現價：$108,000"),
        )
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
            return_value="BTC 市場分析：仍偏多",
        ) as analysis_mock, patch(
            "services.agent.workflow_engine.handle_price_query",
            return_value="BTC 現價：$109,000",
        ) as price_mock:
            result = run_agent_workflow("multi-task-user", "BTC 現在多少並分析一下")

        price_mock.assert_called_once_with("BTC")
        analysis_mock.assert_called_once_with("BTC")
        self.assertEqual(result["intent"], "multi_task")
        self.assertLess(
            result["result"].index("BTC 現價：$109,000"),
            result["result"].index("BTC 市場分析：仍偏多"),
        )

    def test_unsupported_coin_then_price_executes_sequentially(self):
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
            return_value="TRUMP 不支援",
        ) as unsupported_mock, patch(
            "services.agent.workflow_engine.handle_price_query",
            return_value="TRUMP 現價 fallback",
        ) as price_mock:
            result = run_agent_workflow("multi-task-user", "分析川普幣並告訴我價格")

        unsupported_mock.assert_called_once_with("TRUMP")
        price_mock.assert_called_once_with("TRUMP")
        self.assertIn("TRUMP 不支援", result["result"])
        self.assertIn("TRUMP 現價 fallback", result["result"])

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
            return_value="ETH 現價：$3,000",
        ), patch(
            "services.agent.workflow_engine.handle_analysis_query",
            side_effect=RuntimeError("analysis boom"),
        ), patch("builtins.print") as print_log:
            result = run_agent_workflow("multi-task-user", "ETH 價格 + analyze ETH")

        self.assertIn("ETH 現價：$3,000", result["result"])
        self.assertIn("分析失敗", result["result"])
        self.assertTrue(
            any("[WorkflowEngine] task failed" in str(call.args[0]) for call in print_log.call_args_list)
        )
        self.assertEqual(result["state"]["last_intent"], "market_analysis")
        self.assertEqual(result["state"]["last_coin"], "ETH")


if __name__ == "__main__":
    unittest.main()
