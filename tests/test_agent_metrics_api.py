import importlib
import sys
import unittest

from services.agent.agent_metrics import AGENT_METRICS


class AgentMetricsApiTest(unittest.TestCase):
    def tearDown(self):
        sys.modules.pop("app", None)

    def test_get_agent_metrics_endpoint(self):
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
        AGENT_METRICS["intent_counts"] = {"price_query": 4, "help": 1}
        AGENT_METRICS["workflow_latency_ms"] = [10.0, 20.0, 30.0]

        try:
            app_module = importlib.import_module("app")
            response = app_module.app.test_client().get("/agent-metrics")

            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertEqual(payload["workflow_success"], 2)
            self.assertEqual(payload["workflow_failure"], 1)
            self.assertEqual(payload["fallback_count"], 3)
            self.assertEqual(payload["intent_counts"], {"price_query": 4, "help": 1})
            self.assertEqual(payload["workflow_latency_ms"], [10.0, 20.0, 30.0])
            self.assertAlmostEqual(payload["avg_latency_ms"], 20.0, places=3)
        finally:
            AGENT_METRICS["workflow_success"] = original_metrics["workflow_success"]
            AGENT_METRICS["workflow_failure"] = original_metrics["workflow_failure"]
            AGENT_METRICS["fallback_count"] = original_metrics["fallback_count"]
            AGENT_METRICS["intent_counts"] = original_metrics["intent_counts"]
            AGENT_METRICS["workflow_latency_ms"] = original_metrics["workflow_latency_ms"]


if __name__ == "__main__":
    unittest.main()
