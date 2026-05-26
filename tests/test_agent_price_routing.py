import unittest
from unittest.mock import patch

from services.line.command_router import route_user_message


class AgentPriceRoutingTest(unittest.TestCase):
    def test_price_queries_route_to_agent_workflow(self):
        cases = [
            ("btc", "BTC"),
            ("eth", "ETH"),
            ("sol", "SOL"),
        ]

        for message, coin in cases:
            with self.subTest(message=message), patch(
                "services.line.command_router.run_agent_workflow",
                return_value={
                    "intent": "price_query",
                    "coin": coin,
                    "result": f"AGENT_PRICE_{coin}",
                },
            ) as run_agent_workflow, patch(
                "services.line.command_router.onboarding_service.get_onboarding_reply",
                return_value=None,
            ), patch(
                "services.line.command_router.handle_coin_price"
            ) as handle_coin_price, patch("builtins.print") as print_log:
                result = route_user_message("user-1", message)

            run_agent_workflow.assert_called_once_with("user-1", message)
            handle_coin_price.assert_not_called()
            self.assertEqual(result, f"AGENT_PRICE_{coin}")
            self.assertTrue(
                any(
                    "[Agent] price_query routed to Agent workflow" in str(call.args[0])
                    for call in print_log.call_args_list
                )
            )
            self.assertTrue(
                any(
                    "[Agent] price workflow success" in str(call.args[0])
                    for call in print_log.call_args_list
                )
            )

    def test_price_query_falls_back_to_legacy_price_flow_on_exception(self):
        with patch(
            "services.line.command_router.run_agent_workflow",
            side_effect=RuntimeError("boom"),
        ) as run_agent_workflow, patch(
            "services.line.command_router.onboarding_service.get_onboarding_reply",
            return_value=None,
        ), patch(
            "services.line.command_router.handle_coin_price",
            return_value="LEGACY_PRICE_MESSAGE",
        ) as handle_coin_price, patch("builtins.print") as print_log:
            result = route_user_message("user-1", "btc")

        run_agent_workflow.assert_called_once_with("user-1", "btc")
        handle_coin_price.assert_called_once_with("btc")
        self.assertEqual(result, "LEGACY_PRICE_MESSAGE")
        self.assertTrue(
            any(
                "[Agent] fallback to legacy price flow" in str(call.args[0])
                for call in print_log.call_args_list
            )
        )

    def test_help_routes_to_agent_workflow(self):
        with patch(
            "services.line.command_router.run_agent_workflow",
            return_value={
                "intent": "help",
                "coin": "",
                "result": "AGENT_HELP_MESSAGE",
            },
        ) as run_agent_workflow, patch(
            "services.line.command_router.onboarding_service.get_onboarding_reply",
            return_value=None,
        ), patch(
            "services.line.command_router.format_supported_coin_message"
        ) as format_supported_coin_message:
            result = route_user_message("user-1", "help")

        run_agent_workflow.assert_called_once_with("user-1", "help")
        format_supported_coin_message.assert_not_called()
        self.assertEqual(result, "AGENT_HELP_MESSAGE")


if __name__ == "__main__":
    unittest.main()
