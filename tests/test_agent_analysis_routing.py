import unittest
from unittest.mock import patch

from services.line.command_router import route_user_message


class AgentAnalysisRoutingTest(unittest.TestCase):
    def test_analysis_queries_route_to_agent_workflow(self):
        cases = [
            ("analyze btc", "BTC"),
            ("analyze eth", "ETH"),
            ("analyze sol", "SOL"),
            ("analyze bnb", "BNB"),
            ("analyze xrp", "XRP"),
            ("analyze doge", "DOGE"),
            ("analyze ada", "ADA"),
            ("analyze ton", "TON"),
            ("analyze trx", "TRX"),
            ("analyze avax", "AVAX"),
        ]

        for message, coin in cases:
            with self.subTest(message=message), patch(
                "services.line.command_router.run_agent_workflow",
                return_value={
                    "intent": "market_analysis",
                    "coin": coin,
                    "result": f"AGENT_ANALYSIS_{coin}",
                },
            ) as run_agent_workflow, patch(
                "services.line.command_router.onboarding_service.get_onboarding_reply",
                return_value=None,
            ), patch(
                "services.line.command_router.handle_coin_analysis"
            ) as handle_coin_analysis, patch("builtins.print") as print_log:
                result = route_user_message("user-1", message)

            run_agent_workflow.assert_called_once_with("user-1", message)
            handle_coin_analysis.assert_not_called()
            self.assertEqual(result, f"AGENT_ANALYSIS_{coin}")
            self.assertTrue(
                any(
                    "[Agent] market_analysis routed to Agent workflow" in str(call.args[0])
                    for call in print_log.call_args_list
                )
            )
            self.assertTrue(
                any(
                    "[Agent] analysis workflow success" in str(call.args[0])
                    for call in print_log.call_args_list
                )
            )

    def test_analysis_falls_back_to_legacy_flow_on_exception(self):
        with patch(
            "services.line.command_router.run_agent_workflow",
            side_effect=RuntimeError("boom"),
        ) as run_agent_workflow, patch(
            "services.line.command_router.onboarding_service.get_onboarding_reply",
            return_value=None,
        ), patch(
            "services.line.command_router.handle_coin_analysis",
            return_value="LEGACY_ANALYSIS_MESSAGE",
        ) as handle_coin_analysis, patch("builtins.print") as print_log:
            result = route_user_message("user-1", "analyze btc")

        run_agent_workflow.assert_called_once_with("user-1", "analyze btc")
        handle_coin_analysis.assert_called_once_with("btc")
        self.assertEqual(result, "LEGACY_ANALYSIS_MESSAGE")
        self.assertTrue(
            any(
                "[Agent] fallback to legacy analysis flow" in str(call.args[0])
                for call in print_log.call_args_list
            )
        )

    def test_non_agent_analysis_cases_remain_legacy(self):
        with patch(
            "services.line.command_router.onboarding_service.get_onboarding_reply",
            return_value=None,
        ), patch(
            "services.line.command_router.run_agent_workflow"
        ) as run_agent_workflow, patch(
            "services.line.command_router.handle_coin_analysis",
            return_value="LEGACY_ANALYSIS_MESSAGE",
        ) as handle_coin_analysis:
            result = route_user_message("user-1", "analyze usdt")

        self.assertIn("目前支援的幣種", result)
        handle_coin_analysis.assert_not_called()
        run_agent_workflow.assert_not_called()


if __name__ == "__main__":
    unittest.main()
