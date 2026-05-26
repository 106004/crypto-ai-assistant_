import unittest
from unittest.mock import patch

from services.line.command_router import route_user_message


class AgentOnboardingRoutingTest(unittest.TestCase):
    def test_set_commands_route_to_agent_workflow(self):
        cases = [
            ("set btc", "BTC"),
            ("set eth", "ETH"),
            ("set sol", "SOL"),
            ("set bnb", "BNB"),
            ("set xrp", "XRP"),
            ("set doge", "DOGE"),
            ("set ada", "ADA"),
            ("set ton", "TON"),
            ("set trx", "TRX"),
            ("set avax", "AVAX"),
        ]

        for message, coin in cases:
            with self.subTest(message=message), patch(
                "services.line.command_router.run_agent_workflow",
                return_value={
                    "intent": "set_favorite_coin",
                    "coin": coin,
                    "result": f"AGENT_SET_{coin}",
                    "state": {"last_coin": coin, "last_intent": "set_favorite_coin"},
                },
            ) as run_agent_workflow, patch(
                "services.line.command_router.onboarding_service.get_onboarding_reply",
                return_value=None,
            ), patch(
                "services.line.command_router.onboarding_service.handle_set_coin"
            ) as handle_set_coin, patch("builtins.print") as print_log:
                result = route_user_message("user-1", message)

            run_agent_workflow.assert_called_once_with("user-1", message)
            handle_set_coin.assert_not_called()
            self.assertEqual(result, f"AGENT_SET_{coin}")
            self.assertTrue(
                any(
                    "[Agent] set_favorite_coin routed to Agent workflow" in str(call.args[0])
                    for call in print_log.call_args_list
                )
            )
            self.assertTrue(
                any(
                    "[Agent] onboarding workflow success" in str(call.args[0])
                    for call in print_log.call_args_list
                )
            )

    def test_mycoin_routes_to_agent_workflow(self):
        with patch(
            "services.line.command_router.run_agent_workflow",
            return_value={
                "intent": "get_favorite_coin",
                "coin": "",
                "result": "AGENT_MYCOIN_MESSAGE",
                "state": {"last_coin": "BTC", "last_intent": "get_favorite_coin"},
            },
        ) as run_agent_workflow, patch(
            "services.line.command_router.onboarding_service.get_onboarding_reply",
            return_value=None,
        ), patch(
            "services.line.command_router.onboarding_service.handle_mycoin"
        ) as handle_mycoin, patch("builtins.print") as print_log:
            result = route_user_message("user-1", "mycoin")

        run_agent_workflow.assert_called_once_with("user-1", "mycoin")
        handle_mycoin.assert_not_called()
        self.assertEqual(result, "AGENT_MYCOIN_MESSAGE")
        self.assertTrue(
            any(
                "[Agent] get_favorite_coin routed to Agent workflow" in str(call.args[0])
                for call in print_log.call_args_list
            )
        )
        self.assertTrue(
            any(
                "[Agent] onboarding workflow success" in str(call.args[0])
                for call in print_log.call_args_list
            )
        )

    def test_onboarding_falls_back_to_legacy_on_exception(self):
        cases = [
            ("set btc", "btc", "LEGACY_SET_MESSAGE"),
            ("mycoin", None, "LEGACY_MYCOIN_MESSAGE"),
        ]

        for message, coin, expected in cases:
            with self.subTest(message=message), patch(
                "services.line.command_router.run_agent_workflow",
                side_effect=RuntimeError("boom"),
            ) as run_agent_workflow, patch(
                "services.line.command_router.onboarding_service.get_onboarding_reply",
                return_value=None,
            ), patch(
                "services.line.command_router.onboarding_service.handle_set_coin",
                return_value="LEGACY_SET_MESSAGE",
            ) as handle_set_coin, patch(
                "services.line.command_router.onboarding_service.handle_mycoin",
                return_value="LEGACY_MYCOIN_MESSAGE",
            ) as handle_mycoin, patch("builtins.print") as print_log:
                result = route_user_message("user-1", message)

            run_agent_workflow.assert_called_once_with("user-1", message)
            self.assertEqual(result, expected)
            if coin is not None:
                handle_set_coin.assert_called_once_with("user-1", coin)
                handle_mycoin.assert_not_called()
            else:
                handle_mycoin.assert_called_once_with("user-1")
                handle_set_coin.assert_not_called()
            self.assertTrue(
                any(
                    "[Agent] fallback to legacy onboarding flow" in str(call.args[0])
                    for call in print_log.call_args_list
                )
            )


if __name__ == "__main__":
    unittest.main()
