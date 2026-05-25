import importlib
import os
import sys
import unittest
from unittest.mock import patch


class AppSchedulerStartupTest(unittest.TestCase):
    def tearDown(self):
        sys.modules.pop("app", None)
        os.environ.pop("FLASK_DEBUG", None)
        os.environ.pop("WERKZEUG_RUN_MAIN", None)

    def test_debug_reloader_parent_does_not_start_scheduler(self):
        os.environ["FLASK_DEBUG"] = "1"
        os.environ.pop("WERKZEUG_RUN_MAIN", None)
        sys.modules.pop("app", None)

        with patch("scheduler.start_scheduler") as start_scheduler:
            importlib.import_module("app")

        start_scheduler.assert_not_called()

    def test_scheduler_starts_once_in_serving_process(self):
        os.environ["FLASK_DEBUG"] = "1"
        os.environ["WERKZEUG_RUN_MAIN"] = "true"
        sys.modules.pop("app", None)

        with patch("scheduler.start_scheduler") as start_scheduler:
            app_module = importlib.import_module("app")
            app_module._start_scheduler_once()

        start_scheduler.assert_called_once_with()

    def test_update_market_data_endpoint_runs_collector(self):
        sys.modules.pop("app", None)

        with patch("scheduler.start_scheduler"):
            app_module = importlib.import_module("app")

        with patch("routes.cron.run_market_update_job") as run_market_update_job, patch(
            "builtins.print"
        ) as print_log:
            response = app_module.app.test_client().get("/update-market-data")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {"status": "success", "message": "market data updated"},
        )
        run_market_update_job.assert_called_once_with()
        print_log.assert_any_call("[Route] /update-market-data called")
        print_log.assert_any_call("[Route] cron route complete")
        print_log.assert_any_call("[ExternalCron] market update success")

    def test_update_market_data_endpoint_does_not_return_collected_market_data(self):
        sys.modules.pop("app", None)

        large_market_data = {
            f"coin_{index}": {
                "name": "Bitcoin",
                "symbol": "BTC",
                "price_usd": 100000,
                "change_24h": 1.23,
                "updated_at": "2026-05-23 12:00:00",
            }
            for index in range(100)
        }

        with patch("scheduler.start_scheduler"):
            app_module = importlib.import_module("app")

        with patch("routes.cron.run_market_update_job", return_value=large_market_data), patch(
            "builtins.print"
        ):
            response = app_module.app.test_client().get("/update-market-data")

        response_body = response.get_data(as_text=True)
        self.assertEqual(
            response.get_json(),
            {"status": "success", "message": "market data updated"},
        )
        self.assertNotIn("coin_99", response_body)
        self.assertLess(len(response_body), 80)

    def test_update_market_data_endpoint_returns_error_when_collector_fails(self):
        sys.modules.pop("app", None)

        with patch("scheduler.start_scheduler"):
            app_module = importlib.import_module("app")

        with patch(
            "routes.cron.run_market_update_job", side_effect=RuntimeError("db down")
        ), patch("builtins.print") as print_log:
            response = app_module.app.test_client().get("/update-market-data")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.get_json(),
            {"status": "error", "message": "db down"},
        )
        print_log.assert_any_call("[ExternalCron][ERROR] market update failed: db down")


if __name__ == "__main__":
    unittest.main()
