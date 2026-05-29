import unittest
from unittest.mock import patch

from services.agent.coin_resolver import resolve_coin


class CoinResolverTest(unittest.TestCase):
    def test_exact_and_generic_coin_signals(self):
        cases = [
            ("BTC價格", "BTC", "exact_alias"),
            ("BTC多少", "BTC", "exact_alias"),
            ("analyze BTC", "BTC", "exact_alias"),
            ("分析 BTC", "BTC", "exact_alias"),
            ("ZEC價格", "ZEC", "ticker_extraction"),
            ("HYPE價格", "HYPE", "ticker_extraction"),
            ("analyze LTC", "LTC", "ticker_extraction"),
            ("asd123@@", None, "no_coin"),
        ]

        for message, expected_coin, expected_reason in cases:
            with self.subTest(message=message):
                result = resolve_coin(message)
                self.assertEqual(result["coin"], expected_coin)
                self.assertEqual(result["reason"], expected_reason)

    def test_logs_generic_ticker_extraction(self):
        with patch("builtins.print") as print_log:
            result = resolve_coin("ZEC價格")

        self.assertEqual(result["coin"], "ZEC")
        self.assertTrue(
            any(
                "[UnknownTickerExtractor] extracted ticker: ZEC" in str(call.args[0])
                for call in print_log.call_args_list
            )
        )


if __name__ == "__main__":
    unittest.main()
