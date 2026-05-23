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


if __name__ == "__main__":
    unittest.main()
