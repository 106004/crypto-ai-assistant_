import unittest
from unittest.mock import patch

from services.line.command_router import route_user_message


class CommandRouterSemanticFallbackTest(unittest.TestCase):
    def test_unknown_message_falls_back_to_semantic_agent(self):
        with patch(
            "services.line.command_router.onboarding_service.get_onboarding_reply",
            return_value=None,
        ), patch(
            "services.line.command_router.run_agent_workflow",
            return_value={
                "intent": "unknown",
                "coin": "",
                "confidence": 0.1,
                "result": "unknown_intent",
            },
        ) as run_agent_workflow, patch(
            "services.line.command_router.format_unknown_command_message",
            return_value="UNKNOWN_MENU",
        ) as format_unknown_command_message, patch("builtins.print") as print_log:
            result = route_user_message("user-1", "萊特幣")

        run_agent_workflow.assert_called_once_with("user-1", "萊特幣")
        format_unknown_command_message.assert_called_once()
        self.assertEqual(result, "UNKNOWN_MENU")
        self.assertFalse(
            any(
                "[CommandRouter] route -> unknown_command" in str(call.args[0])
                for call in print_log.call_args_list
            )
        )

    def test_gibberish_message_also_falls_back_to_semantic_agent(self):
        with patch(
            "services.line.command_router.onboarding_service.get_onboarding_reply",
            return_value=None,
        ), patch(
            "services.line.command_router.run_agent_workflow",
            return_value={
                "intent": "unknown",
                "coin": "",
                "confidence": 0.1,
                "result": "unknown_intent",
            },
        ) as run_agent_workflow, patch(
            "services.line.command_router.format_unknown_command_message",
            return_value="UNKNOWN_MENU",
        ) as format_unknown_command_message, patch("builtins.print") as print_log:
            result = route_user_message("user-1", "ajsdhajksd123@@@")

        run_agent_workflow.assert_called_once_with("user-1", "ajsdhajksd123@@@")
        format_unknown_command_message.assert_called_once()
        self.assertEqual(result, "UNKNOWN_MENU")
        print_log.assert_any_call("[CommandRouter] fallback to Semantic Agent")


if __name__ == "__main__":
    unittest.main()
