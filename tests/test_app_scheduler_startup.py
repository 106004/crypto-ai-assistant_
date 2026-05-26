import importlib
import sys
import unittest
from unittest.mock import patch

from services.agent.agent_metrics import AGENT_METRICS


class AppCronRoutesTest(unittest.TestCase):
    def tearDown(self):
        sys.modules.pop("app", None)

    def test_metrics_endpoint_returns_agent_metrics(self):
        sys.modules.pop("app", None)
        original_metrics = {
            "workflow_success": AGENT_METRICS["workflow_success"],
            "workflow_failure": AGENT_METRICS["workflow_failure"],
            "fallback_count": AGENT_METRICS["fallback_count"],
            "intent_counts": dict(AGENT_METRICS["intent_counts"]),
            "workflow_latency_ms": list(AGENT_METRICS["workflow_latency_ms"]),
        }
        AGENT_METRICS["workflow_success"] = 2
        AGENT_METRICS["workflow_failure"] = 1
        AGENT_METRICS["fallback_count"] = 3
        AGENT_METRICS["intent_counts"] = {"price_query": 4}
        AGENT_METRICS["workflow_latency_ms"] = [10.0, 20.0]

        try:
            app_module = importlib.import_module("app")

            response = app_module.app.test_client().get("/metrics")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.get_json(),
                {
                    "workflow_success": 2,
                    "workflow_failure": 1,
                    "fallback_count": 3,
                    "intent_counts": {"price_query": 4},
                    "workflow_latency_ms": [10.0, 20.0],
                },
            )
        finally:
            AGENT_METRICS["workflow_success"] = original_metrics["workflow_success"]
            AGENT_METRICS["workflow_failure"] = original_metrics["workflow_failure"]
            AGENT_METRICS["fallback_count"] = original_metrics["fallback_count"]
            AGENT_METRICS["intent_counts"] = original_metrics["intent_counts"]
            AGENT_METRICS["workflow_latency_ms"] = original_metrics["workflow_latency_ms"]

    def test_update_market_data_endpoint_runs_collector(self):
        sys.modules.pop("app", None)

        app_module = importlib.import_module("app")

        with patch("routes.cron.run_market_update_job") as run_market_update_job, patch(
            "builtins.print"
        ) as print_log:
            response = app_module.app.test_client().get("/update-market-data")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {"status": "success", "message": "/update-market-data executed"},
        )
        run_market_update_job.assert_called_once_with()
        print_log.assert_any_call("[ExternalCron] /update-market-data called")
        print_log.assert_any_call("[ExternalCron] /update-market-data completed")

    def test_push_favorite_coin_endpoint_runs_job(self):
        sys.modules.pop("app", None)

        app_module = importlib.import_module("app")

        with patch("routes.cron.run_favorite_coin_push_job") as run_job, patch(
            "builtins.print"
        ) as print_log:
            response = app_module.app.test_client().get("/push-favorite-coin")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {"status": "success", "message": "/push-favorite-coin executed"},
        )
        run_job.assert_called_once_with()
        print_log.assert_any_call("[ExternalCron] /push-favorite-coin called")
        print_log.assert_any_call("[ExternalCron] /push-favorite-coin completed")

    def test_daily_guide_endpoint_runs_job(self):
        sys.modules.pop("app", None)

        app_module = importlib.import_module("app")

        with patch("routes.cron.run_daily_guide_job") as run_job, patch(
            "builtins.print"
        ) as print_log:
            response = app_module.app.test_client().get("/daily-guide")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {"status": "success", "message": "/daily-guide executed"},
        )
        run_job.assert_called_once_with()
        print_log.assert_any_call("[ExternalCron] /daily-guide called")
        print_log.assert_any_call("[ExternalCron] /daily-guide completed")

    def test_update_market_data_endpoint_returns_error_when_job_fails(self):
        sys.modules.pop("app", None)

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
        print_log.assert_any_call("[ExternalCron] /update-market-data called")
        print_log.assert_any_call("[ExternalCron][ERROR] /update-market-data failed: db down")


if __name__ == "__main__":
    unittest.main()
