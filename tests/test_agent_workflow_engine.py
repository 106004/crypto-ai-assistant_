import unittest
from unittest.mock import patch

from services.agent.state_manager import reset_user_state
from services.agent.workflow_engine import run_agent_workflow


class WorkflowEngineTest(unittest.TestCase):
    def setUp(self):
        reset_user_state("test-user")

    def test_price_query_workflow(self):
        with patch(
            "services.agent.workflow_engine.decision_engine.decide_user_intent",
            return_value={"intent": "price_query", "coin": "BTC", "confidence": 0.9},
        ), patch(
            "services.agent.workflow_engine.tool_registry.get_tool_for_intent",
            return_value=lambda coin: {"kind": "price_query", "coin": coin},
        ):
            result = run_agent_workflow("test-user", "btc")

        self.assertEqual(
            result,
            {
                "intent": "price_query",
                "coin": "BTC",
                "confidence": 0.9,
                "result": {"kind": "price_query", "coin": "BTC"},
                "state": {
                    "last_coin": "BTC",
                    "last_intent": "price_query",
                    "conversation_count": 1,
                },
            },
        )

    def test_analysis_workflow(self):
        with patch(
            "services.agent.workflow_engine.decision_engine.decide_user_intent",
            return_value={"intent": "market_analysis", "coin": "ETH", "confidence": 0.9},
        ), patch(
            "services.agent.workflow_engine.tool_registry.get_tool_for_intent",
            return_value=lambda coin: {"kind": "market_analysis", "coin": coin},
        ):
            result = run_agent_workflow("test-user", "analyze eth")

        self.assertEqual(
            result,
            {
                "intent": "market_analysis",
                "coin": "ETH",
                "confidence": 0.9,
                "result": {"kind": "market_analysis", "coin": "ETH"},
                "state": {
                    "last_coin": "ETH",
                    "last_intent": "market_analysis",
                    "conversation_count": 1,
                },
            },
        )

    def test_unknown_intent_returns_safe_fallback(self):
        with patch(
            "services.agent.workflow_engine.decision_engine.decide_user_intent",
            return_value={"intent": "unknown", "coin": "", "confidence": 0.1},
        ), patch(
            "services.agent.workflow_engine.tool_registry.get_tool_for_intent",
            return_value=None,
        ):
            result = run_agent_workflow("test-user", "???")

        self.assertEqual(
            result,
            {
                "intent": "unknown",
                "coin": "",
                "confidence": 0.1,
                "result": "unknown_intent",
                "state": {
                    "last_coin": None,
                    "last_intent": "unknown",
                    "conversation_count": 1,
                },
            },
        )


if __name__ == "__main__":
    unittest.main()
