import unittest
from unittest.mock import patch

from services.agent.clarification_service import build_clarification_message
from services.agent.decision_engine import decide_user_intent
from services.agent.state_manager import reset_user_state
from services.agent.workflow_engine import run_agent_workflow
from services.line.command_router import route_user_message


class ClarificationWorkflowTest(unittest.TestCase):
    def setUp(self):
        reset_user_state("clarify-user")

    def test_low_confidence_becomes_clarification(self):
        with patch(
            "services.agent.decision_engine.semantic_resolver.resolve_coin_symbol",
            return_value={"coin": None, "confidence": 0.0, "method": "none"},
        ), patch(
            "services.agent.decision_engine.classify_with_llm",
            return_value={
                "intent": "unknown",
                "coin": None,
                "confidence": 0.62,
                "reason": "low_confidence",
            },
        ), patch(
            "services.agent.decision_engine.suggest_clarification_candidates",
            return_value=["DOGE", "SHIB"],
        ):
            result = decide_user_intent("幫我看一下狗狗幣")

        self.assertEqual(
            result,
            {
                "intent": "clarification_needed",
                "candidates": ["DOGE", "SHIB"],
                "reason": "low_confidence",
            },
        )

    def test_no_candidate_returns_unknown(self):
        with patch(
            "services.agent.decision_engine.semantic_resolver.resolve_coin_symbol",
            return_value={"coin": None, "confidence": 0.0, "method": "none"},
        ), patch(
            "services.agent.decision_engine.classify_with_llm",
            return_value={
                "intent": "unknown",
                "coin": None,
                "confidence": 0.62,
                "reason": "low_confidence",
            },
        ), patch(
            "services.agent.decision_engine.suggest_clarification_candidates",
            return_value=[],
        ):
            result = decide_user_intent("我想查一個幣")

        self.assertEqual(result, {"intent": "unknown", "coin": "", "confidence": 0.1})

    def test_clarification_message_format_with_candidates(self):
        message = build_clarification_message(["DOGE", "BTC"], reason="low_confidence")
        self.assertIn("我不太確定你指的是哪個幣種。", message)
        self.assertIn("1. DOGE 狗狗幣", message)
        self.assertIn("2. BTC 比特幣", message)
        self.assertIn("請直接輸入幣種，例如：doge 或 btc。", message)

    def test_clarification_message_format_without_candidates(self):
        message = build_clarification_message([], reason="low_confidence")
        self.assertIn("我還不確定你想查哪個幣。", message)
        self.assertIn("btc / eth / sol / bnb / xrp / doge / ada / ton / trx / avax", message)
        self.assertIn("analyze btc", message)
        self.assertIn("set btc", message)

    def test_workflow_does_not_enter_service_layer_for_clarification(self):
        with patch(
            "services.agent.workflow_engine.decision_engine.decide_user_intent",
            return_value={
                "intent": "clarification_needed",
                "candidates": ["DOGE", "SHIB"],
                "reason": "low_confidence",
            },
        ), patch(
            "services.agent.workflow_engine.tool_registry.get_tool_for_intent"
        ) as get_tool_for_intent, patch(
            "services.agent.workflow_engine.agent_policy.should_execute_intent"
        ) as should_execute_intent, patch(
            "services.agent.workflow_engine.format_clarification_message",
            return_value="clarify-message",
        ):
            result = run_agent_workflow("clarify-user", "幫我看一下狗狗幣")

        get_tool_for_intent.assert_not_called()
        should_execute_intent.assert_not_called()
        self.assertEqual(result["intent"], "clarification_needed")
        self.assertEqual(result["message"], "clarify-message")
        self.assertEqual(result["candidates"], ["DOGE", "SHIB"])

    def test_command_router_returns_clarification_message(self):
        with patch(
            "services.line.command_router.onboarding_service.get_onboarding_reply",
            return_value=None,
        ), patch(
            "services.line.command_router.run_agent_workflow",
            return_value={
                "intent": "clarification_needed",
                "candidates": ["DOGE", "BTC"],
                "reason": "low_confidence",
                "message": "clarify-message",
            },
        ) as run_agent_workflow, patch("builtins.print") as print_log:
            result = route_user_message("clarify-user", "幫我看一下狗狗幣")

        run_agent_workflow.assert_called_once_with("clarify-user", "幫我看一下狗狗幣")
        self.assertEqual(result, "clarify-message")
        self.assertTrue(
            any(
                "[Clarification] returned to LINE" in str(call.args[0])
                for call in print_log.call_args_list
            )
        )


if __name__ == "__main__":
    unittest.main()
