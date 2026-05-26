import unittest
from unittest.mock import patch

from services.agent.state_manager import get_user_state, reset_user_state
from services.agent.workflow_engine import run_agent_workflow


class AgentWorkflowStateTest(unittest.TestCase):
    def setUp(self):
        reset_user_state("user-1")
        reset_user_state("user-2")

    def test_price_query_updates_state(self):
        with patch(
            "services.agent.workflow_engine.decision_engine.decide_user_intent",
            return_value={"intent": "price_query", "coin": "BTC", "confidence": 0.9},
        ), patch(
            "services.agent.workflow_engine.tool_registry.get_tool_for_intent",
            return_value=lambda coin: {"kind": "price_query", "coin": coin},
        ):
            result = run_agent_workflow("user-1", "btc")

        self.assertEqual(result["intent"], "price_query")
        self.assertEqual(result["coin"], "BTC")
        self.assertEqual(result["confidence"], 0.9)
        self.assertEqual(result["result"], {"kind": "price_query", "coin": "BTC"})
        self.assertEqual(result["state"]["last_intent"], "price_query")
        self.assertEqual(result["state"]["last_coin"], "BTC")
        self.assertEqual(result["state"]["conversation_count"], 1)
        self.assertEqual(get_user_state("user-1")["conversation_count"], 1)

    def test_analysis_updates_state(self):
        with patch(
            "services.agent.workflow_engine.decision_engine.decide_user_intent",
            return_value={"intent": "market_analysis", "coin": "ETH", "confidence": 0.9},
        ), patch(
            "services.agent.workflow_engine.tool_registry.get_tool_for_intent",
            return_value=lambda coin: {"kind": "market_analysis", "coin": coin},
        ):
            result = run_agent_workflow("user-1", "analyze eth")

        self.assertEqual(result["intent"], "market_analysis")
        self.assertEqual(result["coin"], "ETH")
        self.assertEqual(result["state"]["last_intent"], "market_analysis")
        self.assertEqual(result["state"]["last_coin"], "ETH")
        self.assertEqual(result["state"]["conversation_count"], 1)

    def test_unknown_does_not_overwrite_last_coin(self):
        with patch(
            "services.agent.workflow_engine.decision_engine.decide_user_intent",
            return_value={"intent": "price_query", "coin": "BTC", "confidence": 0.9},
        ), patch(
            "services.agent.workflow_engine.tool_registry.get_tool_for_intent",
            return_value=lambda coin: {"kind": "price_query", "coin": coin},
        ):
            run_agent_workflow("user-1", "btc")

        with patch(
            "services.agent.workflow_engine.decision_engine.decide_user_intent",
            return_value={"intent": "unknown", "coin": "", "confidence": 0.1},
        ), patch(
            "services.agent.workflow_engine.tool_registry.get_tool_for_intent",
            return_value=None,
        ):
            result = run_agent_workflow("user-1", "unknown message")

        self.assertEqual(result["intent"], "unknown")
        self.assertEqual(result["result"], "unknown_intent")
        self.assertEqual(result["state"]["last_intent"], "unknown")
        self.assertEqual(result["state"]["last_coin"], "BTC")
        self.assertEqual(result["state"]["conversation_count"], 2)

    def test_context_follow_up_uses_previous_analysis_intent(self):
        def tool_lookup(intent):
            if intent in {"price_query", "market_analysis"}:
                return lambda coin: {"kind": intent, "coin": coin}
            return None

        with patch(
            "services.agent.workflow_engine.tool_registry.get_tool_for_intent",
            side_effect=tool_lookup,
        ):
            first_result = run_agent_workflow("user-1", "analyze btc")
            second_result = run_agent_workflow("user-1", "那 eth 呢")

        self.assertEqual(first_result["intent"], "market_analysis")
        self.assertEqual(first_result["coin"], "BTC")
        self.assertEqual(second_result["intent"], "market_analysis")
        self.assertEqual(second_result["coin"], "ETH")
        self.assertEqual(second_result["confidence"], 0.8)
        self.assertEqual(second_result["result"], {"kind": "market_analysis", "coin": "ETH"})
        self.assertEqual(second_result["state"]["last_intent"], "market_analysis")
        self.assertEqual(second_result["state"]["last_coin"], "ETH")
        self.assertEqual(second_result["state"]["conversation_count"], 2)

    def test_context_follow_up_uses_previous_price_intent(self):
        def tool_lookup(intent):
            if intent in {"price_query", "market_analysis"}:
                return lambda coin: {"kind": intent, "coin": coin}
            return None

        with patch(
            "services.agent.workflow_engine.tool_registry.get_tool_for_intent",
            side_effect=tool_lookup,
        ):
            first_result = run_agent_workflow("user-2", "btc")
            second_result = run_agent_workflow("user-2", "那 sol 呢")

        self.assertEqual(first_result["intent"], "price_query")
        self.assertEqual(first_result["coin"], "BTC")
        self.assertEqual(second_result["intent"], "price_query")
        self.assertEqual(second_result["coin"], "SOL")
        self.assertEqual(second_result["confidence"], 0.8)
        self.assertEqual(second_result["result"], {"kind": "price_query", "coin": "SOL"})
        self.assertEqual(second_result["state"]["last_intent"], "price_query")
        self.assertEqual(second_result["state"]["last_coin"], "SOL")
        self.assertEqual(second_result["state"]["conversation_count"], 2)

    def test_market_analysis_can_be_blocked_by_policy(self):
        with patch(
            "services.agent.workflow_engine.state_manager.get_user_state",
            return_value={
                "last_coin": "BTC",
                "last_intent": "market_analysis",
                "conversation_count": 1,
                "market_data_fresh": False,
            },
        ), patch(
            "services.agent.workflow_engine.tool_registry.get_tool_for_intent",
            return_value=lambda coin: {"kind": "market_analysis", "coin": coin},
        ), patch(
            "services.agent.workflow_engine.agent_policy.should_execute_intent",
            return_value={
                "allowed": False,
                "reason": "stale_market_data",
                "fallback_action": "coinglass_fallback",
            },
        ), patch(
            "services.agent.workflow_engine.decision_engine.decide_user_intent",
            return_value={"intent": "market_analysis", "coin": "ETH", "confidence": 0.8},
        ):
            result = run_agent_workflow("user-1", "那 eth 呢")

        self.assertTrue(result["blocked"])
        self.assertEqual(result["reason"], "stale_market_data")
        self.assertEqual(result["fallback_action"], "coinglass_fallback")
        self.assertEqual(result["state"]["last_intent"], "market_analysis")
        self.assertEqual(result["state"]["last_coin"], "ETH")
        self.assertEqual(result["state"]["conversation_count"], 2)


if __name__ == "__main__":
    unittest.main()
