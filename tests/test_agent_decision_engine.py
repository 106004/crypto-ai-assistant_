import unittest

from services.agent.decision_engine import decide_user_intent


class DecisionEngineTest(unittest.TestCase):
    def test_price_query(self):
        self.assertEqual(
            decide_user_intent("btc"),
            {"intent": "price_query", "coin": "BTC", "confidence": 0.9},
        )

    def test_market_analysis(self):
        self.assertEqual(
            decide_user_intent("analyze eth"),
            {"intent": "market_analysis", "coin": "ETH", "confidence": 0.9},
        )

    def test_help(self):
        self.assertEqual(
            decide_user_intent("/help"),
            {"intent": "help", "coin": "", "confidence": 0.9},
        )

    def test_unknown(self):
        self.assertEqual(
            decide_user_intent("something random"),
            {"intent": "unknown", "coin": "", "confidence": 0.1},
        )

    def test_context_inference_uses_previous_analysis_intent(self):
        self.assertEqual(
            decide_user_intent(
                "那 ETH 呢",
                user_state={"last_intent": "market_analysis", "last_coin": "BTC"},
            ),
            {"intent": "market_analysis", "coin": "ETH", "confidence": 0.8},
        )

    def test_context_inference_without_previous_intent_falls_back_to_unknown(self):
        self.assertEqual(
            decide_user_intent("那 SOL 呢", user_state={}),
            {"intent": "unknown", "coin": "", "confidence": 0.1},
        )


if __name__ == "__main__":
    unittest.main()
