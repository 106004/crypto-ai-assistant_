import unittest
from unittest.mock import patch

import scheduler


class FakeBackgroundScheduler:
    def __init__(self, timezone):
        self.timezone = timezone
        self.jobs = []
        self.running = False

    def add_job(self, func, **kwargs):
        self.jobs.append({"func": func, **kwargs})

    def start(self):
        self.running = True


class SchedulerTest(unittest.TestCase):
    def setUp(self):
        scheduler._scheduler = None

    def tearDown(self):
        scheduler._scheduler = None

    def test_start_scheduler_keeps_existing_jobs_and_adds_market_update(self):
        with patch.object(scheduler, "BackgroundScheduler", FakeBackgroundScheduler):
            active_scheduler = scheduler.start_scheduler()

        job_ids = {job["id"] for job in active_scheduler.jobs}
        self.assertIn("daily_manual_9am", job_ids)
        self.assertIn("hourly_favorite_coin_price", job_ids)
        self.assertIn("market_data_update_5min", job_ids)

        market_job = next(job for job in active_scheduler.jobs if job["id"] == "market_data_update_5min")
        self.assertEqual(market_job["trigger"], "interval")
        self.assertEqual(market_job["minutes"], 5)

    def test_update_market_data_job_calls_collector(self):
        with patch.object(scheduler, "collect_market_data") as collect_market_data:
            scheduler.update_market_data_job()

        collect_market_data.assert_called_once_with()

    @unittest.skip("Old scheduler price flow used JSON/API fallbacks; scheduled LINE pushes now use Supabase only.")
    def test_hourly_favorite_coin_price_uses_supabase_before_local_and_api(self):
        supabase_coin = {
            "name": "Bitcoin",
            "symbol": "BTC",
            "price_usd": 100,
            "change_24h": 1.5,
            "updated_at": "now",
            "source": "Supabase",
        }

        with patch.object(
            scheduler,
            "get_all_users",
            return_value=[{"user_id": "U1", "favorite_coin": "btc"}],
        ), patch.object(
            scheduler, "get_coin_from_supabase", return_value=supabase_coin
        ) as get_supabase, patch.object(
            scheduler, "get_coin_from_local_data", return_value=None
        ) as get_local, patch.object(
            scheduler, "get_coin_price", return_value=None
        ) as get_api, patch.object(
            scheduler, "push_message"
        ) as push_message:
            scheduler.send_hourly_favorite_coin_price()

        get_supabase.assert_called_once_with("btc")
        get_local.assert_not_called()
        get_api.assert_not_called()
        push_message.assert_called_once()
        self.assertIn("Supabase", push_message.call_args.args[1])

    def test_hourly_favorite_coin_price_uses_supabase_only(self):
        supabase_coin = {
            "name": "Bitcoin",
            "symbol": "BTC",
            "price_usd": 100,
            "change_24h": 1.5,
            "updated_at": "2026-05-25T12:00:00+00:00",
            "source": "Supabase",
        }

        with patch.object(
            scheduler,
            "get_all_users",
            return_value=[{"user_id": "U1", "favorite_coin": "btc"}],
        ), patch.object(
            scheduler, "get_market_data_by_symbol", return_value=supabase_coin
        ) as get_market_data, patch.object(
            scheduler, "push_message"
        ) as push_message:
            scheduler.send_hourly_favorite_coin_price()

        get_market_data.assert_called_once_with("BTC")
        push_message.assert_called_once()
        self.assertIn("Supabase", push_message.call_args.args[1])

    def test_hourly_favorite_coin_price_pushes_coinglass_when_supabase_missing(self):
        with patch.object(
            scheduler,
            "get_all_users",
            return_value=[{"user_id": "U1", "favorite_coin": "btc"}],
        ), patch.object(
            scheduler, "get_market_data_by_symbol", return_value=None
        ) as get_market_data, patch.object(
            scheduler, "push_message"
        ) as push_message:
            scheduler.send_hourly_favorite_coin_price()

        get_market_data.assert_called_once_with("BTC")
        push_message.assert_called_once()
        self.assertIn("CoinGlass", push_message.call_args.args[1])

    @unittest.skip("Old scheduler price flow used JSON/API fallbacks; scheduled LINE pushes now use Supabase only.")
    def test_hourly_favorite_coin_price_falls_back_to_local_before_api(self):
        local_coin = {
            "name": "Bitcoin",
            "symbol": "BTC",
            "price_usd": 90,
            "change_24h": 0.5,
            "updated_at": "now",
            "source": "本地 market_data.json",
        }

        with patch.object(
            scheduler,
            "get_all_users",
            return_value=[{"user_id": "U1", "favorite_coin": "btc"}],
        ), patch.object(
            scheduler, "get_coin_from_supabase", return_value=None
        ), patch.object(
            scheduler, "get_coin_from_local_data", return_value=local_coin
        ) as get_local, patch.object(
            scheduler, "get_coin_price", return_value=None
        ) as get_api, patch.object(
            scheduler, "push_message"
        ) as push_message:
            scheduler.send_hourly_favorite_coin_price()

        get_local.assert_called_once_with("btc")
        get_api.assert_not_called()
        push_message.assert_called_once()
        self.assertIn("本地 market_data.json", push_message.call_args.args[1])


if __name__ == "__main__":
    unittest.main()
