import unittest

from services.agent.state_manager import get_user_state, reset_user_state, update_user_state


class StateManagerTest(unittest.TestCase):
    def test_update_and_read_back_state(self):
        reset_user_state("user-1")

        update_user_state(
            "user-1",
            {
                "last_coin": "BTC",
                "last_intent": "market_analysis",
            },
        )

        state = get_user_state("user-1")
        self.assertEqual(
            state,
            {
                "last_coin": "BTC",
                "last_intent": "market_analysis",
                "conversation_count": 1,
            },
        )


if __name__ == "__main__":
    unittest.main()
