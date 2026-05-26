import unittest
from unittest.mock import patch

from services.line.command_router import route_user_message


class AgentHelpRoutingTest(unittest.TestCase):
    def test_help_uses_agent_workflow(self):
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
        ) as format_supported_coin_message, patch("builtins.print") as print_log:
            result = route_user_message("user-1", "help")

        run_agent_workflow.assert_called_once_with("user-1", "help")
        format_supported_coin_message.assert_not_called()
        self.assertEqual(result, "AGENT_HELP_MESSAGE")
        self.assertTrue(
            any(
                "[Agent] help intent routed to Agent workflow" in str(call.args[0])
                for call in print_log.call_args_list
            )
        )
        self.assertTrue(
            any(
                "[Agent] help workflow success" in str(call.args[0])
                for call in print_log.call_args_list
            )
        )

    def test_help_falls_back_to_legacy_help_flow_on_exception(self):
        with patch(
            "services.line.command_router.run_agent_workflow",
            side_effect=RuntimeError("boom"),
        ) as run_agent_workflow, patch(
            "services.line.command_router.onboarding_service.get_onboarding_reply",
            return_value=None,
        ), patch(
            "services.line.command_router.format_supported_coin_message",
            return_value="LEGACY_HELP_MESSAGE",
        ) as format_supported_coin_message, patch("builtins.print") as print_log:
            result = route_user_message("user-1", "help")

        run_agent_workflow.assert_called_once_with("user-1", "help")
        format_supported_coin_message.assert_called_once()
        self.assertEqual(result, "LEGACY_HELP_MESSAGE")
        self.assertTrue(
            any(
                "[Agent] help intent routed to Agent workflow" in str(call.args[0])
                for call in print_log.call_args_list
            )
        )
        self.assertTrue(
            any(
                "[Agent] fallback to legacy help" in str(call.args[0])
                for call in print_log.call_args_list
            )
        )
        self.assertTrue(
            any(
                "[Agent] fallback error: boom" in str(call.args[0])
                for call in print_log.call_args_list
            )
        )

    def test_chinese_help_commands_route_to_agent(self):
        for message in ("說明", "使用說明"):
            with self.subTest(message=message), patch(
                "services.line.command_router.run_agent_workflow",
                return_value={
                    "intent": "help",
                    "coin": "",
                    "result": "AGENT_HELP_MESSAGE",
                },
            ) as run_agent_workflow, patch(
                "services.line.command_router.onboarding_service.get_onboarding_reply",
                return_value=None,
            ):
                result = route_user_message("user-1", message)

            run_agent_workflow.assert_called_once_with("user-1", message)
            self.assertEqual(result, "AGENT_HELP_MESSAGE")


if __name__ == "__main__":
    unittest.main()
