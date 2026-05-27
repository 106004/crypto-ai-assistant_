import unittest
from unittest.mock import patch

from services.agent.decision_engine import decide_user_intent
from services.agent.state_manager import reset_user_state
from services.agent.unsupported_coin_service import build_unsupported_coin_message
from services.agent.workflow_engine import run_agent_workflow
from services.line.command_router import route_user_message


class UnsupportedCoinWorkflowTest(unittest.TestCase):
    def setUp(self):
        reset_user_state("unsupported-user")

    def test_trump_becomes_unsupported_coin_from_llm(self):
        self.assertEqual(
            decide_user_intent("TRUMP"),
            {
                "intent": "unsupported_coin",
                "coin": "TRUMP",
                "reason": "coin_not_supported",
            },
        )

    def test_chinese_unsupported_coin_becomes_unsupported_coin(self):
        self.assertEqual(
            decide_user_intent("川普幣"),
            {
                "intent": "unsupported_coin",
                "coin": "TRUMP",
                "reason": "coin_not_supported",
            },
        )

    def test_floki_becomes_unsupported_coin(self):
        self.assertEqual(
            decide_user_intent("FLOKI"),
            {
                "intent": "unsupported_coin",
                "coin": "FLOKI",
                "reason": "coin_not_supported",
            },
        )

    def test_bonk_becomes_unsupported_coin(self):
        self.assertEqual(
            decide_user_intent("BONK"),
            {
                "intent": "unsupported_coin",
                "coin": "BONK",
                "reason": "coin_not_supported",
            },
        )

    def test_shib_becomes_unsupported_coin(self):
        with patch(
            "services.agent.decision_engine.classify_with_llm"
        ) as classify_with_llm:
            result = decide_user_intent("shib")

        classify_with_llm.assert_not_called()
        self.assertEqual(
            result,
            {
                "intent": "unsupported_coin",
                "coin": "SHIB",
                "reason": "coin_not_supported",
            },
        )

    def test_pepe_becomes_unsupported_coin(self):
        with patch(
            "services.agent.decision_engine.classify_with_llm"
        ) as classify_with_llm:
            result = decide_user_intent("analyze pepe")

        classify_with_llm.assert_not_called()
        self.assertEqual(
            result,
            {
                "intent": "unsupported_coin",
                "coin": "PEPE",
                "reason": "coin_not_supported",
            },
        )

    def test_unknown_gibberish_stays_unknown(self):
        with patch(
            "services.agent.decision_engine.detect_unsupported_coin",
            return_value={"coin": None, "confidence": 0.0, "method": "none"},
        ), patch(
            "services.agent.decision_engine.classify_with_llm",
            return_value={
                "intent": "unknown",
                "coin": None,
                "confidence": 0.0,
                "reason": "invalid_json",
            },
        ):
            result = decide_user_intent("ajsdhajksd123@@@")

        self.assertEqual(result, {"intent": "unknown", "coin": "", "confidence": 0.1})

    def test_supported_coin_does_not_trigger_unsupported(self):
        result = decide_user_intent("btc")
        self.assertNotEqual(result["intent"], "unsupported_coin")
        self.assertEqual(result["intent"], "price_query")

    def test_supported_coin_router_does_not_go_unknown_command(self):
        with patch(
            "services.line.command_router.onboarding_service.get_onboarding_reply",
            return_value=None,
        ), patch(
            "services.line.command_router.run_agent_workflow",
            return_value={
                "intent": "unsupported_coin",
                "coin": "TRUMP",
                "reason": "coin_not_supported",
                "message": "unsupported-message",
            },
        ) as run_agent_workflow, patch("builtins.print") as print_log:
            result = route_user_message("unsupported-user", "川普幣")

        run_agent_workflow.assert_called_once_with("unsupported-user", "川普幣")
        self.assertEqual(result, "unsupported-message")
        self.assertTrue(
            any(
                "[Agent] unsupported_coin routed to Agent workflow" in str(call.args[0])
                for call in print_log.call_args_list
            )
        )

    def test_llm_unsupported_coin_result_is_preserved(self):
        with patch(
            "services.agent.decision_engine.semantic_resolver.resolve_coin_symbol",
            return_value={"coin": None, "confidence": 0.0, "method": "none"},
        ), patch(
            "services.agent.decision_engine.detect_unsupported_coin",
            return_value={"coin": None, "confidence": 0.0, "method": "none"},
        ), patch(
            "services.agent.decision_engine.classify_with_llm",
            return_value={
                "intent": "unsupported_coin",
                "coin": "PEPE",
                "confidence": 0.96,
                "reason": "coin_not_supported",
            },
        ):
            result = decide_user_intent("analyze pepe")

        self.assertEqual(
            result,
            {
                "intent": "unsupported_coin",
                "coin": "PEPE",
                "confidence": 0.96,
                "reason": "coin_not_supported",
            },
        )

    def test_workflow_does_not_enter_service_layer(self):
        with patch(
            "services.agent.workflow_engine.decision_engine.decide_user_intent",
            return_value={
                "intent": "unsupported_coin",
                "coin": "SHIB",
                "reason": "coin_not_supported",
            },
        ), patch(
            "services.agent.workflow_engine.tool_registry.get_tool_for_intent"
        ) as get_tool_for_intent, patch(
            "services.agent.workflow_engine.agent_policy.should_execute_intent"
        ) as should_execute_intent, patch(
            "services.agent.workflow_engine.build_unsupported_coin_message",
            return_value="unsupported-message",
        ):
            result = run_agent_workflow("unsupported-user", "shib")

        get_tool_for_intent.assert_not_called()
        should_execute_intent.assert_not_called()
        self.assertEqual(result["intent"], "unsupported_coin")
        self.assertEqual(result["coin"], "SHIB")
        self.assertEqual(result["message"], "unsupported-message")
        self.assertEqual(result["reason"], "coin_not_supported")

    def test_response_message_correct(self):
        message = build_unsupported_coin_message("SHIB")
        self.assertIn("目前我還不能查詢或分析 SHIB。", message)
        self.assertIn("目前只支援：", message)
        self.assertIn("BTC / ETH / SOL / BNB / XRP / DOGE / ADA / TON / TRX / AVAX", message)
        self.assertIn("btc", message)
        self.assertIn("analyze eth", message)
        self.assertIn("set sol", message)

    def test_command_router_returns_unsupported_coin_message(self):
        for message in ("trump", "shib", "set shib"):
            with self.subTest(message=message), patch(
                "services.line.command_router.onboarding_service.get_onboarding_reply",
                return_value=None,
            ), patch(
                "services.line.command_router.run_agent_workflow",
                return_value={
                    "intent": "unsupported_coin",
                    "coin": "SHIB",
                    "reason": "coin_not_supported",
                    "message": "unsupported-message",
                },
            ) as run_agent_workflow, patch("builtins.print") as print_log:
                result = route_user_message("unsupported-user", message)

            run_agent_workflow.assert_called_once_with("unsupported-user", message)
            self.assertEqual(result, "unsupported-message")
            self.assertTrue(
                any(
                    "[Agent] unsupported_coin routed to Agent workflow" in str(call.args[0])
                    for call in print_log.call_args_list
                )
            )


if __name__ == "__main__":
    unittest.main()
