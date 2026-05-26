import unittest
from unittest.mock import patch

from config.settings import MAX_MARKET_DATA_AGE_SECONDS
from services.jobs.scheduler_service import run_daily_guide_job, run_favorite_coin_job


MARKET_DATA_AGE_MINUTES = MAX_MARKET_DATA_AGE_SECONDS // 60


class SchedulerServiceTest(unittest.TestCase):
    def test_run_favorite_coin_job_logs_and_pushes_fresh_price(self):
        market_data = {
            "name": "Bitcoin",
            "symbol": "BTC",
            "price_usd": 100,
            "change_24h": 1.5,
            "updated_at": "2026-05-25T12:00:00+00:00",
        }

        with patch(
            "services.jobs.scheduler_service.get_all_users",
            return_value=[{"user_id": "U1", "favorite_coin": "btc"}],
        ), patch(
            "services.jobs.scheduler_service.get_market_data_by_symbol",
            return_value=market_data,
        ), patch(
            "services.jobs.scheduler_service.is_market_data_fresh",
            return_value=True,
        ), patch(
            "services.jobs.scheduler_service.push_message"
        ) as push_message, patch("builtins.print") as print_log:
            run_favorite_coin_job()

        push_message.assert_called_once()
        self.assertTrue(
            any("[FavoriteCoinJob] started" in str(call.args[0]) for call in print_log.call_args_list)
        )
        self.assertTrue(
            any("[FavoriteCoinJob] user count: 1" in str(call.args[0]) for call in print_log.call_args_list)
        )
        self.assertTrue(
            any("[FavoriteCoinJob] pushing BTC to user U1" in str(call.args[0]) for call in print_log.call_args_list)
        )
        self.assertTrue(
            any("[FavoriteCoinJob] push completed" in str(call.args[0]) for call in print_log.call_args_list)
        )
        self.assertTrue(
            any("[FavoriteCoinJob] completed" in str(call.args[0]) for call in print_log.call_args_list)
        )
        self.assertIn("資料來源：Supabase", push_message.call_args.args[1])

    def test_run_favorite_coin_job_pushes_fallback_when_data_missing(self):
        with patch(
            "services.jobs.scheduler_service.get_all_users",
            return_value=[{"user_id": "U1", "favorite_coin": "btc"}],
        ), patch(
            "services.jobs.scheduler_service.get_market_data_by_symbol",
            return_value=None,
        ), patch(
            "services.jobs.scheduler_service.push_message"
        ) as push_message, patch("builtins.print") as print_log:
            run_favorite_coin_job()

        push_message.assert_called_once()
        self.assertIn(
            f"⚠️ BTC 價格資料超過 {MARKET_DATA_AGE_MINUTES} 分鐘",
            push_message.call_args.args[1],
        )
        self.assertIn("https://www.coinglass.com/zh-TW/currencies/BTC", push_message.call_args.args[1])
        self.assertNotIn("AVAX", push_message.call_args.args[1])
        self.assertTrue(
            any(
                "[FavoriteCoinJob] BTC stale, pushing CoinGlass link" in str(call.args[0])
                for call in print_log.call_args_list
            )
        )
        self.assertTrue(
            any("[FavoriteCoinJob] push completed" in str(call.args[0]) for call in print_log.call_args_list)
        )

    def test_run_daily_guide_job_logs_and_pushes_guide(self):
        with patch(
            "services.jobs.scheduler_service.get_all_users",
            return_value=[{"user_id": "U1"}],
        ), patch(
            "services.jobs.scheduler_service.push_message"
        ) as push_message, patch("builtins.print") as print_log:
            run_daily_guide_job()

        push_message.assert_called_once()
        self.assertTrue(
            any("[DailyGuideJob] started" in str(call.args[0]) for call in print_log.call_args_list)
        )
        self.assertTrue(
            any("[DailyGuideJob] user count: 1" in str(call.args[0]) for call in print_log.call_args_list)
        )
        self.assertTrue(
            any("[DailyGuideJob] pushing guide to user U1" in str(call.args[0]) for call in print_log.call_args_list)
        )
        self.assertTrue(
            any("[DailyGuideJob] completed" in str(call.args[0]) for call in print_log.call_args_list)
        )


if __name__ == "__main__":
    unittest.main()
