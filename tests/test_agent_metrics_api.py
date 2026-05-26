import importlib
import sys
import unittest

from services.agent.agent_metrics import AGENT_METRICS, reset_agent_metrics


class AgentMetricsApiTest(unittest.TestCase):
    def tearDown(self):
        sys.modules.pop("app", None)
        reset_agent_metrics()

    def test_get_agent_metrics_endpoint(self):
        sys.modules.pop("app", None)
        reset_agent_metrics()
        AGENT_METRICS["workflow_success"] = 2
        AGENT_METRICS["workflow_failure"] = 1
        AGENT_METRICS["fallback_count"] = 3
        AGENT_METRICS["intent_counts"] = {"price_query": 4, "help": 1}
        AGENT_METRICS["workflow_latency_ms"] = [10.0, 20.0, 30.0]
        AGENT_METRICS["last_workflow"] = {
            "intent": "help",
            "success": True,
            "latency_ms": 30.0,
            "timestamp": "2026-05-26T00:00:00+00:00",
        }

        try:
            app_module = importlib.import_module("app")
            response = app_module.app.test_client().get("/agent-metrics")

            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertIn("summary", payload)
            self.assertIn("intents", payload)
            self.assertIn("latency", payload)
            self.assertIn("last_workflow", payload)
            self.assertEqual(payload["summary"]["workflow_success"], 2)
            self.assertEqual(payload["summary"]["workflow_failure"], 1)
            self.assertEqual(payload["summary"]["fallback_count"], 3)
            self.assertAlmostEqual(payload["summary"]["success_rate"], 2 / 3, places=3)
            self.assertAlmostEqual(payload["summary"]["failure_rate"], 1 / 3, places=3)
            self.assertAlmostEqual(payload["summary"]["fallback_rate"], 1.0, places=3)
            self.assertEqual(payload["intents"]["intent_counts"], {"price_query": 4, "help": 1})
            self.assertEqual(
                payload["intents"]["top_intents"],
                [{"intent": "price_query", "count": 4}, {"intent": "help", "count": 1}],
            )
            self.assertEqual(payload["latency"]["samples"], [10.0, 20.0, 30.0])
            self.assertAlmostEqual(payload["latency"]["avg_latency_ms"], 20.0, places=3)
            self.assertAlmostEqual(payload["latency"]["min_latency_ms"], 10.0, places=3)
            self.assertAlmostEqual(payload["latency"]["max_latency_ms"], 30.0, places=3)
            self.assertAlmostEqual(payload["latency"]["last_latency_ms"], 30.0, places=3)
            self.assertEqual(payload["last_workflow"]["intent"], "help")
            self.assertTrue(payload["last_workflow"]["success"])
            self.assertAlmostEqual(payload["last_workflow"]["latency_ms"], 30.0, places=3)
        finally:
            reset_agent_metrics()


if __name__ == "__main__":
    unittest.main()
