import unittest

from services.agent.tool_registry import get_tool_for_intent, list_available_tools
from services.line.analysis_service import handle_analysis_query
from services.line.message_service import format_supported_coin_message
from services.line.onboarding_service import handle_mycoin, handle_set_coin
from services.line.price_service import handle_price_query


class ToolRegistryTest(unittest.TestCase):
    def test_available_tools_list(self):
        self.assertEqual(
            list_available_tools(),
            [
                "price_query",
                "market_analysis",
                "set_favorite_coin",
                "get_favorite_coin",
                "help",
            ],
        )

    def test_price_query_tool(self):
        self.assertIs(get_tool_for_intent("price_query"), handle_price_query)

    def test_market_analysis_tool(self):
        self.assertIs(get_tool_for_intent("market_analysis"), handle_analysis_query)

    def test_set_favorite_coin_tool(self):
        self.assertIs(get_tool_for_intent("set_favorite_coin"), handle_set_coin)

    def test_get_favorite_coin_tool(self):
        self.assertIs(get_tool_for_intent("get_favorite_coin"), handle_mycoin)

    def test_help_tool(self):
        self.assertIs(get_tool_for_intent("help"), format_supported_coin_message)

    def test_unknown_tool(self):
        self.assertIsNone(get_tool_for_intent("unknown"))


if __name__ == "__main__":
    unittest.main()
