import unittest

from services.agent.coin_aliases import normalize_coin_alias
from services.agent.decision_engine import decide_user_intent


class CoinAliasNormalizationTest(unittest.TestCase):
    def test_normalizes_chinese_alias(self):
        self.assertEqual(normalize_coin_alias("以太幣今天價格多少"), "ETH 今天價格多少")

    def test_normalizes_english_alias(self):
        self.assertEqual(normalize_coin_alias("dogecoin price"), "DOGE price")

    def test_normalizes_mixed_case_alias(self):
        self.assertEqual(normalize_coin_alias("BiTcOiN is strong"), "BTC is strong")

    def test_normalizes_nickname_alias(self):
        self.assertEqual(normalize_coin_alias("姨太現在還能漲嗎"), "ETH 現在還能漲嗎")

    def test_normalizes_multi_word_alias(self):
        self.assertEqual(normalize_coin_alias("The Open Network 上漲嗎"), "TON 上漲嗎")

    def test_normalizes_mixed_sentence(self):
        self.assertEqual(normalize_coin_alias("大餅今天危險嗎"), "BTC 今天危險嗎")

    def test_keeps_unknown_coin_unchanged(self):
        self.assertEqual(normalize_coin_alias("abc 今天價格多少"), "abc 今天價格多少")

    def test_decision_engine_uses_normalized_text(self):
        self.assertEqual(
            decide_user_intent("大餅今天價格多少"),
            {"intent": "price_query", "coin": "BTC", "confidence": 0.9},
        )


if __name__ == "__main__":
    unittest.main()
