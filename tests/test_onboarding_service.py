import unittest

from services.line.onboarding_service import get_daily_guide_message, get_welcome_message


class OnboardingServiceTest(unittest.TestCase):
    def test_welcome_message_contains_required_topics(self):
        message = get_welcome_message()

        self.assertIn("查價格：btc / eth / sol", message)
        self.assertIn("支援 10 種幣：btc / eth / sol / bnb / xrp / doge / ada / ton / trx / avax", message)
        self.assertIn("AI 分析：analyze btc", message)
        self.assertIn("設定最愛幣：set btc", message)
        self.assertIn("查詢最愛幣：mycoin", message)
        self.assertIn("資料規則：超過 5 分鐘的價格不會回覆舊資料", message)
        self.assertIn("異常時：會提供 CoinGlass 即時行情連結", message)
        self.assertIn("提醒：這不是投資建議", message)

    def test_daily_guide_message_contains_required_topics(self):
        message = get_daily_guide_message()

        self.assertIn("查價格：btc / eth / sol", message)
        self.assertIn("支援 10 種幣：btc / eth / sol / bnb / xrp / doge / ada / ton / trx / avax", message)
        self.assertIn("AI 分析：analyze btc", message)
        self.assertIn("設定最愛幣：set btc", message)
        self.assertIn("查詢最愛幣：mycoin", message)
        self.assertIn("資料規則：超過 5 分鐘的價格不會回覆舊資料", message)
        self.assertIn("異常時：會提供 CoinGlass 即時行情連結", message)
        self.assertIn("提醒：這不是投資建議", message)


if __name__ == "__main__":
    unittest.main()
