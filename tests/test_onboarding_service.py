import unittest

from config.settings import MAX_MARKET_DATA_AGE_SECONDS
from services.line.onboarding_service import get_daily_guide_message, get_welcome_message


MARKET_DATA_AGE_MINUTES = MAX_MARKET_DATA_AGE_SECONDS // 60


class OnboardingServiceTest(unittest.TestCase):
    def test_welcome_message_contains_required_topics(self):
        message = get_welcome_message()

        self.assertIn("可查幣價：btc / eth / sol", message)
        self.assertIn(
            "支援 10 幣種：btc / eth / sol / bnb / xrp / doge / ada / ton / trx / avax",
            message,
        )
        self.assertIn("AI 分析：analyze btc", message)
        self.assertIn("設定幣種：set btc", message)
        self.assertIn("查看幣種：mycoin", message)
        self.assertIn(
            f"資料規則：超過 {MARKET_DATA_AGE_MINUTES} 分鐘的價格不會回覆舊資料",
            message,
        )
        self.assertIn("異常時：會提供 CoinGlass 即時行情連結", message)
        self.assertIn("可隨時輸入 /help 查看說明", message)

    def test_daily_guide_message_contains_required_topics(self):
        message = get_daily_guide_message()

        self.assertIn("可查幣價：btc / eth / sol", message)
        self.assertIn(
            "支援 10 幣種：btc / eth / sol / bnb / xrp / doge / ada / ton / trx / avax",
            message,
        )
        self.assertIn("AI 分析：analyze btc", message)
        self.assertIn("設定幣種：set btc", message)
        self.assertIn("查看幣種：mycoin", message)
        self.assertIn(
            f"資料規則：超過 {MARKET_DATA_AGE_MINUTES} 分鐘的價格不會回覆舊資料",
            message,
        )
        self.assertIn("異常時：會提供 CoinGlass 即時行情連結", message)
        self.assertIn("可隨時輸入 /help 查看說明", message)


if __name__ == "__main__":
    unittest.main()
