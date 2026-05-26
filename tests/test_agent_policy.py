import unittest

from services.agent.agent_policy import should_execute_intent


class AgentPolicyTest(unittest.TestCase):
    def test_market_analysis_with_stale_data_is_blocked(self):
        self.assertEqual(
            should_execute_intent("market_analysis", {"market_data_fresh": False}),
            {
                "allowed": False,
                "reason": "stale_market_data",
                "fallback_action": "coinglass_fallback",
            },
        )

    def test_price_query_is_allowed(self):
        self.assertEqual(
            should_execute_intent("price_query", {"market_data_fresh": False}),
            {
                "allowed": True,
                "reason": "allowed",
                "fallback_action": "",
            },
        )


if __name__ == "__main__":
    unittest.main()
